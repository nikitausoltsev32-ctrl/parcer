from __future__ import annotations

import json
import logging
import re
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage, ChatSession
from app.models.user import User
from app.services.chat.tools import HANDLERS, TOOLS_SCHEMA
from app.services.llm import get_llm_client
from app.services.llm.base import LLMMessage

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты — Лида, ИИ-агент по продажам для бизнеса пользователя в России.
Помогаешь пользователю: искать компании-клиентов, писать персональные письма,
вести CRM, отвечать на входящие. Работаешь через вызов функций (tools).

Говоришь по-русски, кратко, без канцелярита.
Когда пользователь явно просит действие (найти компании, сохранить список, обогатить) — вызывай нужный tool. Не переспрашивай лишнего.
Когда задача неясна — задай один точный вопрос. При обычном разговоре отвечай текстом без вызова tools.
Не выдумывай факты о клиентах пользователя.
Не упоминай, что ты AI или языковая модель.
"""


_SEARCH_TRIGGERS = ("найди", "найти", "подбери", "ищу", "нужны", "find", "search")


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

    if not query:
        return None
    return {"query": query, "city": city, "limit": 20}


def _system_with_profile(user: User) -> str:
    bp = user.business_profile or {}
    profile = "\n".join([
        f"Бизнес пользователя: {bp.get('business', 'не указан')}",
        f"Оффер: {bp.get('offer', 'не указан')}",
        f"Город: {bp.get('city', 'не указан')}",
        f"Тон по умолчанию: {bp.get('tone_default', 'friendly')}",
    ])
    return SYSTEM_PROMPT + "\n" + profile


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

    messages: list[LLMMessage] = [LLMMessage(role="system", content=_system_with_profile(user))]
    for msg in history[-20:]:
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

    fallback_args = _forced_search_args(user_text)
    if fallback_args:
        tool_call = {
            "id": f"forced-{uuid.uuid4()}",
            "name": "search_companies",
            "arguments": fallback_args,
        }
        yield sse("tool_calls", {"tool_calls": [tool_call]})

        handler_args = dict(fallback_args)
        handler_args["__db"] = db
        handler_args["__user"] = user
        tool_result = await HANDLERS["search_companies"](handler_args)
        yield sse("tool_result", {"name": "search_companies", "result": tool_result})

        assistant_msg = ChatMessage(
            id=uuid.uuid4(),
            session_id=session.id,
            role="assistant",
            content=None,
            tool_calls=[tool_call],
            tool_results=[{"id": tool_call["id"], "name": "search_companies", "result": tool_result}],
        )
        db.add(assistant_msg)
        session.last_message_at = datetime.now(UTC)
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
                tool_result = await handler(args) if handler else {"error": "unknown_tool"}
                # Убираем служебные ключи перед отправкой клиенту
                args.pop("__db", None)
                args.pop("__user", None)
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
