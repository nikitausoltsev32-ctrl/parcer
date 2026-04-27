from __future__ import annotations

import json
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage, ChatSession
from app.models.user import User
from app.services.chat.tools import HANDLERS, TOOLS_SCHEMA
from app.services.llm import get_llm_client
from app.services.llm.base import LLMMessage

SYSTEM_PROMPT = """Ты — AI-менеджер по продажам для малого бизнеса в России.
Помогаешь пользователю: искать компании-клиентов, писать персональные письма,
вести CRM, отвечать на входящие. Работаешь через вызов функций (tools).

Говоришь по-русски, кратко, без канцелярита.
Когда хватает данных — сразу вызывай tool. Не переспрашивай лишнего.
Когда не хватает — задай один точный вопрос.
Не выдумывай факты о клиентах пользователя.
Не упоминай, что ты AI или языковая модель.
"""


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
) -> AsyncGenerator[str, None]:
    """Yield SSE-совместимые строки: data: <json>\n\n"""

    def sse(event: str, payload: dict) -> str:
        return f"data: {json.dumps({'event': event, **payload}, ensure_ascii=False)}\n\n"

    client = get_llm_client("chat")

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

    # Tool-calling loop (до 5 итераций)
    for _ in range(5):
        result = await client.chat(
            messages=messages,
            tools=TOOLS_SCHEMA,
            temperature=0.4,
            max_tokens=1500,
        )

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
