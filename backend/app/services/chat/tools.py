from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact, ContactList
from app.models.user import User
from app.services.search import search_companies as _search

ToolHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]

TOOLS_SCHEMA: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_companies",
            "description": (
                "Найти компании по запросу пользователя в публичных источниках. "
                "Используй когда пользователь явно просит найти клиентов или компании."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Тип компаний или запрос, например: 'дизайн-студии'",
                    },
                    "city": {"type": "string", "description": "Город поиска"},
                    "limit": {"type": "integer", "default": 20, "description": "Количество результатов, максимум 50"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_companies",
            "description": (
                "Сохранить найденные компании как контакты пользователя. "
                "Вызывай после search_companies когда пользователь подтвердил список."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "companies": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "email": {"type": "string"},
                                "website": {"type": "string"},
                                "city": {"type": "string"},
                                "industry": {"type": "string"},
                            },
                        },
                    },
                    "list_name": {"type": "string", "description": "Название списка контактов"},
                },
                "required": ["companies", "list_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "enrich_contacts",
            "description": (
                "Запустить обогащение контактов: Firecrawl + LLM анализ сайтов. "
                "Используй когда пользователь явно просит узнать больше о компаниях в списке."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "list_id": {
                        "type": "string",
                        "description": "ID списка контактов для обогащения",
                    },
                    "contact_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Конкретные ID контактов (альтернатива list_id)",
                    },
                },
            },
        },
    },
]


async def _not_implemented(args: dict[str, Any]) -> dict[str, Any]:
    return {"error": "not_implemented"}


async def _handle_search_companies(args: dict[str, Any]) -> dict[str, Any]:
    args.pop("__db")
    args.pop("__user", None)
    results = await _search(
        query=args.get("query", ""),
        city=args.get("city"),
        limit=args.get("limit", 20),
    )
    return {"companies": results, "total": len(results)}


async def _handle_save_companies(args: dict[str, Any]) -> dict[str, Any]:
    db: AsyncSession = args.pop("__db")
    user: User = args.pop("__user")

    companies = args.get("companies", [])
    list_name = args.get("list_name", f"Поиск {datetime.now(UTC).strftime('%d.%m.%Y')}")

    contact_list = ContactList(
        id=uuid.uuid4(),
        user_id=user.id,
        name=list_name,
        source="search",
        total_count=len(companies),
    )
    db.add(contact_list)
    await db.flush()

    saved = 0
    for c in companies:
        contact = Contact(
            id=uuid.uuid4(),
            user_id=user.id,
            list_id=contact_list.id,
            contact_name=c.get("name"),
            email=c.get("email"),
            enrichment={"website_summary": c.get("website_summary"), "website": c.get("website")},
            raw=c,
        )
        db.add(contact)
        saved += 1

    await db.commit()
    return {"list_id": str(contact_list.id), "list_name": list_name, "saved": saved}


async def _handle_enrich_contacts(args: dict[str, Any]) -> dict[str, Any]:
    from app.core.config import settings
    from app.workers.main import enrich_contact_task

    db: AsyncSession = args.pop("__db")
    args.pop("__user", None)

    if settings.llm_enrich_provider == "disabled":
        return {"error": "enrichment_disabled", "message": "Обогащение отключено (LLM_ENRICH_PROVIDER=disabled)"}

    list_id: str | None = args.get("list_id")
    contact_ids: list[str] | None = args.get("contact_ids")

    ids: list[str] = []
    if contact_ids:
        ids = contact_ids
    elif list_id:
        rows = await db.execute(
            select(Contact.id).where(Contact.list_id == uuid.UUID(list_id))
        )
        ids = [str(r) for r in rows.scalars().all()]
    else:
        return {"error": "missing_params", "message": "Укажи list_id или contact_ids"}

    for cid in ids:
        await enrich_contact_task.defer_async(contact_id=cid)

    return {"enqueued": len(ids), "message": f"Запущено обогащение для {len(ids)} контактов"}


HANDLERS: dict[str, ToolHandler] = {
    "search_companies": _handle_search_companies,
    "save_companies": _handle_save_companies,
    "enrich_contacts": _handle_enrich_contacts,
    "create_campaign": _not_implemented,
    "generate_letters": _not_implemented,
    "send_campaign": _not_implemented,
    "check_inbox": _not_implemented,
    "update_contact": _not_implemented,
    "set_reminder": _not_implemented,
}
