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
    {
        "type": "function",
        "function": {
            "name": "create_campaign",
            "description": (
                "Создать кампанию рассылки и поставить в очередь генерацию писем. "
                "Используй когда пользователь хочет запустить рассылку по списку контактов. "
                "Перед вызовом убедись что у пользователя есть список контактов (list_id), "
                "шаблон (template_id) и почтовый ящик (smtp_account_id)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Название кампании"},
                    "list_id": {"type": "string", "description": "ID списка контактов"},
                    "template_id": {"type": "string", "description": "ID шаблона письма"},
                    "smtp_account_id": {"type": "string", "description": "ID почтового ящика для отправки"},
                    "send_rate_per_hour": {"type": "integer", "default": 30, "description": "Писем в час"},
                },
                "required": ["name", "list_id", "template_id", "smtp_account_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_campaign",
            "description": (
                "Отправить сгенерированные письма кампании. "
                "Используй только после того как кампания в статусе 'generated'. "
                "Спроси подтверждение у пользователя перед вызовом."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "string", "description": "ID кампании для отправки"},
                },
                "required": ["campaign_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_resources",
            "description": (
                "Получить списки доступных ресурсов пользователя: списки контактов, шаблоны, почтовые ящики. "
                "Вызывай когда нужно узнать какие list_id / template_id / smtp_account_id доступны."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "resource": {
                        "type": "string",
                        "enum": ["contact_lists", "templates", "smtp_accounts", "campaigns"],
                        "description": "Тип ресурса",
                    },
                },
                "required": ["resource"],
            },
        },
    },
]


async def _not_implemented(args: dict[str, Any]) -> dict[str, Any]:
    return {"error": "not_implemented"}


async def _handle_create_campaign(args: dict[str, Any]) -> dict[str, Any]:
    from app.models.campaign import Campaign
    from app.models.smtp_account import SmtpAccount
    from app.models.template import Template
    from app.workers.main import generate_letters

    db: AsyncSession = args.pop("__db")
    user: User = args.pop("__user")

    try:
        list_id = uuid.UUID(args["list_id"])
        template_id = uuid.UUID(args["template_id"])
        smtp_account_id = uuid.UUID(args["smtp_account_id"])
    except (ValueError, KeyError) as e:
        field = str(e).strip("'\"")
        return {"error": "invalid_uuid", "field": field, "message": "Сначала вызови list_resources, чтобы получить настоящие UUID."}

    if not (await db.execute(select(ContactList.id).where(ContactList.id == list_id, ContactList.user_id == user.id))).scalar_one_or_none():
        return {"error": "not_found", "message": "Список контактов не найден. Вызови list_resources(resource='contact_lists')."}
    if not (await db.execute(select(SmtpAccount.id).where(SmtpAccount.id == smtp_account_id, SmtpAccount.user_id == user.id))).scalar_one_or_none():
        return {"error": "not_found", "message": "Почтовый ящик не найден. Вызови list_resources(resource='smtp_accounts')."}
    if not (await db.execute(select(Template.id).where(Template.id == template_id, (Template.user_id == user.id) | (Template.user_id.is_(None))))).scalar_one_or_none():
        return {"error": "not_found", "message": "Шаблон не найден. Вызови list_resources(resource='templates')."}

    campaign = Campaign(
        id=uuid.uuid4(),
        user_id=user.id,
        name=args.get("name", ""),
        list_id=list_id,
        template_id=template_id,
        smtp_account_id=smtp_account_id,
        send_rate_per_hour=args.get("send_rate_per_hour", 30),
        status="generating",
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)

    await generate_letters.defer_async(campaign_id=str(campaign.id))

    return {
        "campaign_id": str(campaign.id),
        "name": campaign.name,
        "status": "generating",
        "message": f"Кампания «{campaign.name}» создана, генерация писем запущена.",
    }


async def _handle_send_campaign(args: dict[str, Any]) -> dict[str, Any]:
    from datetime import timedelta

    from app.models.campaign import Campaign, CampaignMessage
    from app.workers.main import send_email

    db: AsyncSession = args.pop("__db")
    user: User = args.pop("__user")

    try:
        campaign_id = uuid.UUID(args["campaign_id"])
    except (ValueError, KeyError):
        return {"error": "invalid_uuid", "field": "campaign_id", "message": "Сначала вызови list_resources(resource='campaigns')."}

    row = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == user.id)
    )
    campaign = row.scalar_one_or_none()
    if not campaign:
        return {"error": "not_found", "message": "Кампания не найдена."}
    if campaign.status != "generated":
        return {
            "error": "wrong_status",
            "message": f"Кампания в статусе «{campaign.status}», отправка возможна только из статуса «generated».",
        }

    rows = await db.execute(
        select(CampaignMessage).where(
            CampaignMessage.campaign_id == campaign_id,
            CampaignMessage.status == "pending",
        )
    )
    messages = rows.scalars().all()
    rate = max(campaign.send_rate_per_hour, 1)
    for i, msg in enumerate(messages):
        await send_email.defer_async(
            message_id=str(msg.id),
            schedule_in={"seconds": int(3600 / rate) * i},
        )

    campaign.status = "sending"
    await db.commit()

    return {
        "campaign_id": str(campaign_id),
        "enqueued": len(messages),
        "message": f"Отправка запущена: {len(messages)} писем поставлено в очередь.",
    }


async def _handle_list_resources(args: dict[str, Any]) -> dict[str, Any]:
    from app.models.campaign import Campaign
    from app.models.smtp_account import SmtpAccount
    from app.models.template import Template

    db: AsyncSession = args.pop("__db")
    user: User = args.pop("__user")
    resource = args.get("resource", "contact_lists")

    if resource == "contact_lists":
        rows = await db.execute(
            select(ContactList).where(ContactList.user_id == user.id)
        )
        items = [{"id": str(r.id), "name": r.name, "total": r.total_count} for r in rows.scalars().all()]

    elif resource == "templates":
        rows = await db.execute(
            select(Template).where((Template.user_id == user.id) | (Template.user_id.is_(None)))
        )
        items = [{"id": str(r.id), "name": r.name, "tone": r.tone} for r in rows.scalars().all()]

    elif resource == "smtp_accounts":
        rows = await db.execute(
            select(SmtpAccount).where(SmtpAccount.user_id == user.id)
        )
        items = [{"id": str(r.id), "email": r.from_email, "name": r.from_name, "active": r.is_active} for r in rows.scalars().all()]

    elif resource == "campaigns":
        rows = await db.execute(
            select(Campaign).where(Campaign.user_id == user.id).order_by(Campaign.created_at.desc()).limit(10)
        )
        items = [{"id": str(r.id), "name": r.name, "status": r.status, "stats": r.stats} for r in rows.scalars().all()]

    else:
        return {"error": "unknown_resource"}

    return {"resource": resource, "items": items, "count": len(items)}


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
        try:
            parsed_list_id = uuid.UUID(list_id)
        except ValueError:
            return {"error": "invalid_uuid", "field": "list_id", "message": "Сначала вызови list_resources(resource='contact_lists')."}
        rows = await db.execute(
            select(Contact.id).where(Contact.list_id == parsed_list_id)
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
    "create_campaign": _handle_create_campaign,
    "send_campaign": _handle_send_campaign,
    "list_resources": _handle_list_resources,
    "check_inbox": _not_implemented,
    "update_contact": _not_implemented,
    "set_reminder": _not_implemented,
}
