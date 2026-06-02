from __future__ import annotations

import json
import logging
import re
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import CampaignMessage
from app.models.chat import ChatMessage, ChatSession
from app.models.contact import Contact
from app.models.inbox_message import InboxMessage
from app.models.lead import Lead
from app.models.user import User
from app.services.chat.tools import HANDLERS, TOOLS_SCHEMA
from app.services.llm import get_llm_client
from app.services.llm.base import LLMMessage

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты — Лида, ИИ-ассистент по продажам для бизнеса пользователя в России.
Помогаешь искать клиентов, писать персональные письма, вести CRM, отвечать на входящие.
Говоришь по-русски, кратко, без канцелярита. Не упоминай, что ты AI.

## Когда вызывать tools
- Пользователь просит найти компании/клиентов → search_companies
- Пользователь подтверждает сохранение списка → save_companies
- Пользователь хочет запустить рассылку → сначала list_resources чтобы уточнить list_id/template_id/smtp_account_id,
  потом create_campaign
- Пользователь спрашивает про конкретную компанию → get_company_info
- Нужны доступные списки/шаблоны/ящики → list_resources
Не переспрашивай лишнего. Если задача неясна — задай один точный вопрос.

## Флоу поиска (строго соблюдай порядок)

**Шаг 1 — поиск:** вызови search_companies с query и city из запроса пользователя.

**Шаг 2 — вывод результатов:** покажи каждую компанию отдельной строкой в формате:
`N. **[Название](сайт)** — краткое описание чем занимается · 📧 email · 📍 город`

Правила формата:
- Если есть website — делай название кликабельной ссылкой [Название](https://...)
- Если есть email — показывай после · 📧
- Если есть website_summary или description — 1 фраза своими словами что делает компания
- Если нет ни summary ни description — пиши рубрику/отрасль из поля industry
- Если нет ни того ни другого — пиши только название и город
- Каждая компания с новой строки, не склеивай в абзац
- Не повторяй одинаковые фразы для всех компаний

**Шаг 3 — предложи действие:** после списка ВСЕГДА добавляй одну строку:
`Сохранить список для рассылки? Или уточнить поиск?`

## После сохранения списка
Сообщи сколько контактов сохранено и предложи:
`Готово! Запустить рассылку по этому списку?`

## Входящие и CRM
- «Есть ли ответы?» / «Кто написал?» → check_inbox, покажи список с классификацией
- После check_inbox если есть interested/question → предложи suggest_reply для каждого
- «Ответь ему», «что написать» → suggest_reply, покажи варианты пронумерованным списком
- «Отметь как заинтересованного», «поставь статус» → update_contact
- «Напомни», «перезвоню» → set_reminder, подтверди дату и действие

## Не выдумывай факты о клиентах пользователя.
"""


_SEARCH_TRIGGERS = ("найди", "найти", "подбери", "ищу", "нужны", "find", "search")
_IMPORT_URL_RE = re.compile(r"import://[0-9a-fA-F-]{36}")


def _forced_search_args(user_text: str) -> dict | None:
    text = " ".join(user_text.strip().split())
    if not text or not any(trigger in text.lower() for trigger in _SEARCH_TRIGGERS):
        return None

    query = re.sub(
        r"^(найди|найти|подбери|ищу|нужны|нужен|find|search)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip(" .,!?:;")
    if not query:
        return None

    city = None
    city_match = re.search(r"\s+в\s+([A-Za-zА-Яа-яЁё -]+)$", query, flags=re.IGNORECASE)
    if city_match:
        city = city_match.group(1).strip(" .,!?:;")
        query = query[:city_match.start()].strip(" .,!?:;")

    limit = 20
    limit_match = re.match(r"^(\d{1,2})\s+", query)
    if limit_match:
        limit = max(1, min(int(limit_match.group(1)), 50))
        query = query[limit_match.end():].strip(" .,!?:;")

    if not query:
        return None
    return {"query": query, "city": city, "limit": limit}


def _forced_import_args(user_text: str) -> dict | None:
    match = _IMPORT_URL_RE.search(user_text)
    if not match:
        return None
    text = user_text.lower()
    confirmed = "confirmed=true" in text or "confirm import" in text or "подтверж" in text
    return {"file_url": match.group(0), "confirmed": confirmed}


def _system_with_profile(user: User) -> str:
    bp = user.business_profile or {}
    icp = bp.get("icp") if isinstance(bp.get("icp"), dict) else {}
    icp_profile_lines = [
        f"Website: {bp.get('website') or bp.get('website_url') or 'not set'}",
        f"ICP summary: {icp.get('seller_summary', 'not set')}",
        f"ICP buyer segments: {_join_profile_list(icp.get('buyer_segments'))}",
        f"ICP exclusions: {_join_profile_list(icp.get('excluded_industries'))}",
    ]
    profile = "\n".join([
        f"Бизнес пользователя: {bp.get('business', 'не указан')}",
        f"Оффер: {bp.get('offer', 'не указан')}",
        f"Город: {bp.get('city', 'не указан')}",
        *icp_profile_lines,
        f"Тон по умолчанию: {bp.get('tone_default', 'friendly')}",
    ])
    return SYSTEM_PROMPT + "\n" + profile


def _join_profile_list(value: object) -> str:
    if not isinstance(value, list):
        return "not set"
    cleaned = [" ".join(str(item).split()) for item in value if " ".join(str(item).split())]
    return ", ".join(cleaned[:8]) or "not set"


async def _crm_context_summary(db: AsyncSession, user: User) -> str:
    try:
        contacts = await db.scalar(select(func.count(Contact.id)).where(Contact.user_id == user.id))
        leads = await db.scalar(select(func.count(Lead.id)).where(Lead.user_id == user.id))
        sent = await db.scalar(
            select(func.count(CampaignMessage.id))
            .join(Contact, Contact.id == CampaignMessage.contact_id)
            .where(Contact.user_id == user.id, CampaignMessage.sent_at.is_not(None))
        )
        replies = await db.scalar(select(func.count(InboxMessage.id)).where(InboxMessage.user_id == user.id))
    except Exception:
        return "CRM memory: unavailable for this turn."

    return (
        "CRM memory: "
        f"leads_found={int(leads or 0)}, "
        f"contacts={int(contacts or 0)}, "
        f"messages_sent={int(sent or 0)}, "
        f"inbox_replies={int(replies or 0)}. "
        "Use CRM tools before claiming details about a specific company."
    )


async def stream_agent(
    db: AsyncSession,
    session: ChatSession,
    user: User,
    user_text: str,
    history: list[ChatMessage],
    *,
    model: str | None = None,
) -> AsyncGenerator[str, None]:
    """Yield SSE-совместимые строки: data: <json>\n\n"""

    def sse(event: str, payload: dict) -> str:
        return f"data: {json.dumps({'event': event, **payload}, ensure_ascii=False)}\n\n"

    crm_context = await _crm_context_summary(db, user)
    messages: list[LLMMessage] = [LLMMessage(role="system", content=f"{_system_with_profile(user)}\n{crm_context}")]
    for msg in history[-20:]:
        if msg.role == "assistant" and msg.tool_calls:
            rebuilt_calls = []
            for tc in msg.tool_calls:
                args = tc["arguments"]
                if not isinstance(args, str):
                    args = json.dumps(args, ensure_ascii=False)
                rebuilt_calls.append({
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["name"], "arguments": args},
                })
            messages.append(LLMMessage(
                role="assistant",
                content=msg.content,
                tool_calls=rebuilt_calls,
            ))
            for tr in (msg.tool_results or []):
                messages.append(LLMMessage(
                    role="tool",
                    content=json.dumps(tr.get("result", {}), ensure_ascii=False),
                    tool_call_id=tr.get("id"),
                    name=tr.get("name"),
                ))
        else:
            messages.append(LLMMessage(role=msg.role, content=msg.content))
    messages.append(LLMMessage(role="user", content=user_text))

    # Сохраняем сообщение пользователя
    user_msg = ChatMessage(
        id=uuid.uuid4(),
        session_id=session.id,
        role="user",
        content=user_text,
    )
    db.add(user_msg)
    await db.commit()

    import_args = _forced_import_args(user_text)
    if import_args:
        tool_call_id = f"forced-{uuid.uuid4()}"
        tool_call = {
            "id": tool_call_id,
            "name": "import_contacts",
            "arguments": import_args,
        }
        yield sse("tool_calls", {"tool_calls": [tool_call]})

        handler_args = dict(import_args)
        handler_args["__db"] = db
        handler_args["__user"] = user
        tool_result = await HANDLERS["import_contacts"](handler_args)
        yield sse("tool_result", {"name": "import_contacts", "result": tool_result})

        assistant_msg = ChatMessage(
            id=uuid.uuid4(),
            session_id=session.id,
            role="assistant",
            content=None,
            tool_calls=[tool_call],
            tool_results=[{"id": tool_call_id, "name": "import_contacts", "result": tool_result}],
        )
        db.add(assistant_msg)
        session.last_message_at = datetime.now(UTC)
        await db.commit()
        yield sse("done", {})
        return

    fallback_args = _forced_search_args(user_text)
    if fallback_args:
        tool_call_id = f"forced-{uuid.uuid4()}"
        tool_call = {
            "id": tool_call_id,
            "name": "search_companies",
            "arguments": fallback_args,
        }
        yield sse("tool_calls", {"tool_calls": [tool_call]})

        handler_args = dict(fallback_args)
        handler_args["__db"] = db
        handler_args["__user"] = user
        handler_args["__ai_model"] = model
        tool_result = await HANDLERS["search_companies"](handler_args)
        yield sse("tool_result", {"name": "search_companies", "result": tool_result})

        assistant_msg = ChatMessage(
            id=uuid.uuid4(),
            session_id=session.id,
            role="assistant",
            content=None,
            tool_calls=[tool_call],
            tool_results=[{"id": tool_call_id, "name": "search_companies", "result": tool_result}],
        )
        db.add(assistant_msg)
        await db.commit()
        yield sse("done", {})
        return

    try:
        client = get_llm_client("chat", model_override=model)
    except Exception:
        logger.exception("chat: failed to initialize llm client")
        yield sse("error", {"message": "Не удалось подключить модель. Проверьте настройки LLM и попробуйте снова."})
        yield sse("done", {})
        return

    # Tool-calling loop (до 5 итераций)
    for _ in range(5):
        try:
            result = await client.chat(
                messages=messages,
                tools=TOOLS_SCHEMA,
                temperature=0.4,
                max_tokens=1500,
            )
        except Exception:
            logger.exception("chat: llm call failed")
            yield sse(
                "error",
                {"message": "Не удалось получить ответ модели. Провайдер временно недоступен или перегружен."},
            )
            yield sse("done", {})
            return

        if result.tool_calls:
            yield sse("tool_calls", {"tool_calls": result.tool_calls})

            tool_results = []
            for tc in result.tool_calls:
                handler = HANDLERS.get(tc["name"])
                args = json.loads(tc["arguments"]) if isinstance(tc["arguments"], str) else tc["arguments"]
                # Передаём db и user в handlers через аргументы
                args["__db"] = db
                args["__user"] = user
                args["__ai_model"] = model
                tool_result = await handler(args) if handler else {"error": "unknown_tool"}
                # Убираем служебные ключи перед отправкой клиенту
                args.pop("__db", None)
                args.pop("__user", None)
                args.pop("__ai_model", None)
                tool_results.append({"id": tc["id"], "name": tc["name"], "result": tool_result})
                yield sse("tool_result", {"name": tc["name"], "result": tool_result})

            # Добавляем tool-сообщения в историю для следующей итерации
            messages.append(LLMMessage(
                role="assistant",
                content=result.content,
                tool_calls=[
                    {"id": tc["id"], "type": "function", "function": {"name": tc["name"], "arguments": tc["arguments"]}}
                    for tc in result.tool_calls
                ],
            ))
            for tr in tool_results:
                messages.append(LLMMessage(
                    role="tool",
                    content=json.dumps(tr["result"], ensure_ascii=False),
                    tool_call_id=tr["id"],
                    name=tr["name"],
                ))

            # Сохраняем tool round в БД
            assistant_msg = ChatMessage(
                id=uuid.uuid4(),
                session_id=session.id,
                role="assistant",
                content=result.content,
                tool_calls=result.tool_calls,
                tool_results=tool_results,
            )
            db.add(assistant_msg)
            await db.commit()
            continue

        # Финальный текстовый ответ
        if result.content:
            yield sse("text", {"content": result.content})
            final_msg = ChatMessage(
                id=uuid.uuid4(),
                session_id=session.id,
                role="assistant",
                content=result.content,
            )
            db.add(final_msg)
            session.last_message_at = datetime.now(UTC)
            await db.commit()

        yield sse("done", {})
        return

    yield sse("error", {"message": "Превышено количество итераций"})
    yield sse("done", {})
