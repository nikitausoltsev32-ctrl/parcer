from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact, ContactList
from app.models.user import User
from app.services.leads.async_search import LeadSearchQuotaExceededError, start_lead_search_job

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
            "name": "import_contacts",
            "description": (
                "Import contacts from an uploaded CSV, TSV or XLSX file. "
                "Call first with confirmed=false to show a preview. "
                "Call again with confirmed=true only after user approval."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "file_url": {
                        "type": "string",
                        "description": "Temporary import file URL returned by /contacts/import preview, for example import://<uuid>.",
                    },
                    "confirmed": {
                        "type": "boolean",
                        "default": False,
                        "description": "false returns preview only; true creates ContactList and Contact rows.",
                    },
                    "list_name": {
                        "type": "string",
                        "description": "Optional contact list name to use when confirmed=true.",
                    },
                },
                "required": ["file_url", "confirmed"],
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
                                "email": {"type": ["string", "null"]},
                                "website": {"type": ["string", "null"]},
                                "city": {"type": ["string", "null"]},
                                "industry": {"type": ["string", "null"]},
                                "phone": {"type": ["string", "null"]},
                                "website_summary": {"type": ["string", "null"]},
                            },
                            "required": ["name"],
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
            "name": "get_company_info",
            "description": (
                "Получить подробную информацию о компании из базы: чем занимается, услуги, клиенты, город. "
                "Используй когда пользователь спрашивает конкретно о компании или контакте."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_id": {
                        "type": "string",
                        "description": "UUID контакта",
                    },
                    "company_name": {
                        "type": "string",
                        "description": "Название компании (если contact_id неизвестен)",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_inbox",
            "description": (
                "Проверить входящие письма: новые ответы от клиентов с AI-классификацией. "
                "Вызывай когда пользователь спрашивает «есть ли ответы», «кто написал», «что в почте»."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "classification": {
                        "type": "string",
                        "enum": ["interested", "rejected", "autoreply", "question", "unsubscribe", "other"],
                        "description": "Фильтр по классификации (опционально)",
                    },
                    "limit": {"type": "integer", "default": 10, "description": "Количество сообщений"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_reply",
            "description": (
                "Предложить 2–3 варианта ответа на входящее письмо от клиента. "
                "Вызывай когда пользователь хочет ответить на конкретное письмо."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "inbox_message_id": {
                        "type": "string",
                        "description": "ID входящего сообщения из check_inbox",
                    },
                },
                "required": ["inbox_message_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_contact",
            "description": (
                "Обновить данные контакта: статус, следующий шаг, заметку. "
                "Используй когда пользователь говорит «отметь как заинтересованного», «запиши что...», «поставь статус»."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_id": {"type": "string", "description": "UUID контакта"},
                    "status": {
                        "type": "string",
                        "enum": ["new", "contacted", "replied", "qualified", "won", "lost", "cold"],
                        "description": "Новый статус",
                    },
                    "next_step": {"type": "string", "description": "Следующее действие (текст)"},
                    "note": {"type": "string", "description": "Заметка, которую нужно добавить"},
                },
                "required": ["contact_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_reminder",
            "description": (
                "Поставить напоминание по контакту на конкретную дату и время. "
                "Используй когда пользователь говорит «напомни», «поставь напоминание», «перезвоню во вторник»."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_id": {"type": "string", "description": "UUID контакта"},
                    "remind_at": {
                        "type": "string",
                        "description": "Дата и время в формате ISO 8601, например 2026-05-10T10:00:00",
                    },
                    "action": {"type": "string", "description": "Что нужно сделать, например «позвонить» или «отправить follow-up»"},
                },
                "required": ["contact_id", "remind_at", "action"],
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


async def _handle_check_inbox(args: dict[str, Any]) -> dict[str, Any]:
    from app.models.inbox_message import InboxMessage

    db: AsyncSession = args.pop("__db")
    user: User = args.pop("__user")

    classification = args.get("classification")
    limit = min(args.get("limit", 10), 30)

    q = select(InboxMessage).where(InboxMessage.user_id == user.id)
    if classification:
        q = q.where(InboxMessage.classification == classification)
    q = q.order_by(InboxMessage.created_at.desc()).limit(limit)

    rows = await db.execute(q)
    messages = rows.scalars().all()

    items = []
    for m in messages:
        items.append({
            "id": str(m.id),
            "from_email": m.from_email,
            "subject": m.subject,
            "body_preview": (m.body_text or "")[:300],
            "classification": m.classification,
            "received_at": m.received_at.isoformat() if m.received_at else None,
            "contact_id": str(m.contact_id) if m.contact_id else None,
            "campaign_id": str(m.campaign_id) if m.campaign_id else None,
        })

    classification_counts: dict[str, int] = {}
    for m in messages:
        c = m.classification or "other"
        classification_counts[c] = classification_counts.get(c, 0) + 1

    return {"messages": items, "total": len(items), "by_classification": classification_counts}


async def _handle_import_contacts(args: dict[str, Any]) -> dict[str, Any]:
    from app.services.crm.contact_import import (
        ContactImportError,
        confirm_contact_import_job,
        load_import_file,
        preview_contact_import,
    )

    db: AsyncSession = args.pop("__db")
    user: User = args.pop("__user")

    file_url = args.get("file_url")
    if not file_url:
        return {"error": "missing_file_url", "message": "Upload a CSV/XLSX file first."}

    try:
        if args.get("confirmed") is True:
            return await confirm_contact_import_job(
                db,
                user,
                file_url=file_url,
                list_name=args.get("list_name"),
            )
        job = await load_import_file(db, user.id, file_url)
        return await preview_contact_import(db, user, filename=job.filename, content=job.payload, persist_file=False)
    except ContactImportError as exc:
        return {"error": "import_failed", "detail": exc.detail, "status_code": exc.status_code}


async def _handle_suggest_reply(args: dict[str, Any]) -> dict[str, Any]:
    from app.models.inbox_message import InboxMessage
    from app.services.llm import get_llm_client
    from app.services.llm.base import LLMMessage

    db: AsyncSession = args.pop("__db")
    user: User = args.pop("__user")

    try:
        inbox_id = uuid.UUID(args["inbox_message_id"])
    except (ValueError, KeyError):
        return {"error": "invalid_uuid", "message": "Укажи inbox_message_id из check_inbox"}

    row = await db.execute(
        select(InboxMessage).where(InboxMessage.id == inbox_id, InboxMessage.user_id == user.id)
    )
    msg = row.scalar_one_or_none()
    if not msg:
        return {"error": "not_found", "message": "Сообщение не найдено"}

    bp = user.business_profile or {}
    system = (
        "Ты — помощник по B2B-продажам. Предложи 2–3 варианта ответа на входящее письмо от клиента. "
        "Варианты должны быть короткими (2–4 предложения), на русском, без канцелярита. "
        "Отвечай JSON: {\"replies\": [\"вариант 1\", \"вариант 2\", \"вариант 3\"]}"
    )
    user_prompt = (
        f"Отправитель: {msg.from_email}\n"
        f"Тема: {msg.subject}\n"
        f"Письмо:\n{(msg.body_text or '')[:800]}\n\n"
        f"Бизнес: {bp.get('business', '')}\nОффер: {bp.get('offer', '')}"
    )

    try:
        client = get_llm_client("chat")
        result = await client.chat(
            messages=[
                LLMMessage(role="system", content=system),
                LLMMessage(role="user", content=user_prompt),
            ],
            temperature=0.7,
            max_tokens=600,
        )
        import json as _json
        data = _json.loads(result.content or "{}")
        replies = data.get("replies", [])
    except Exception:
        replies = []

    return {
        "inbox_message_id": str(inbox_id),
        "from_email": msg.from_email,
        "subject": msg.subject,
        "replies": replies,
    }


async def _handle_update_contact(args: dict[str, Any]) -> dict[str, Any]:
    from app.models.activity import Activity

    db: AsyncSession = args.pop("__db")
    user: User = args.pop("__user")

    try:
        contact_id = uuid.UUID(args["contact_id"])
    except (ValueError, KeyError):
        return {"error": "invalid_uuid", "message": "Укажи корректный contact_id"}

    row = await db.execute(
        select(Contact).where(Contact.id == contact_id, Contact.user_id == user.id)
    )
    contact = row.scalar_one_or_none()
    if not contact:
        return {"error": "not_found", "message": "Контакт не найден"}

    changes = []
    if "status" in args and args["status"] != contact.status:
        old_status = contact.status
        contact.status = args["status"]
        changes.append(f"статус: {old_status} → {args['status']}")

    if "next_step" in args:
        contact.next_step = args["next_step"]
        changes.append(f"следующий шаг: {args['next_step']}")

    if "note" in args and args["note"]:
        db.add(Activity(
            id=uuid.uuid4(),
            user_id=user.id,
            contact_id=contact.id,
            type="note",
            body=args["note"],
        ))
        changes.append("добавлена заметка")

    await db.commit()
    return {
        "contact_id": str(contact_id),
        "name": contact.contact_name,
        "changes": changes,
        "status": contact.status,
    }


async def _handle_set_reminder(args: dict[str, Any]) -> dict[str, Any]:
    from datetime import datetime

    from app.models.reminder import Reminder

    db: AsyncSession = args.pop("__db")
    user: User = args.pop("__user")

    try:
        contact_id = uuid.UUID(args["contact_id"])
    except (ValueError, KeyError):
        return {"error": "invalid_uuid", "message": "Укажи корректный contact_id"}

    try:
        remind_at = datetime.fromisoformat(args["remind_at"])
    except (ValueError, KeyError):
        return {"error": "invalid_date", "message": "Формат даты: 2026-05-10T10:00:00"}

    row = await db.execute(
        select(Contact).where(Contact.id == contact_id, Contact.user_id == user.id)
    )
    contact = row.scalar_one_or_none()
    if not contact:
        return {"error": "not_found", "message": "Контакт не найден"}

    reminder = Reminder(
        id=uuid.uuid4(),
        user_id=user.id,
        contact_id=contact_id,
        remind_at=remind_at,
        action=args.get("action", ""),
        status="pending",
    )
    db.add(reminder)
    await db.commit()

    return {
        "reminder_id": str(reminder.id),
        "contact_name": contact.contact_name,
        "remind_at": remind_at.isoformat(),
        "action": reminder.action,
    }


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
    db: AsyncSession = args.pop("__db")
    user: User = args.pop("__user")
    ai_model = args.pop("__ai_model", None)
    query = " ".join(str(args.get("query", "")).split())
    city_value = args.get("city")
    city = " ".join(str(city_value).split()) if city_value else None
    limit = max(1, min(int(args.get("limit", 5) or 5), 5))
    list_name = f"{query} {city or ''}".strip() or None
    try:
        log_id = await start_lead_search_job(
            db,
            user=user,
            query=query,
            city=city,
            limit=limit,
            list_name=list_name,
            fast_mode=True,
            ai_model=ai_model,
        )
    except LeadSearchQuotaExceededError:
        return {
            "error": "lead_quota_exhausted",
            "message": "Лимит лидов исчерпан. Увеличь квоту или смени тариф.",
            "query": query,
            "city": city,
        }
    return {"status": "pending", "log_id": str(log_id), "query": query, "city": city, "limit": limit}


async def _handle_save_companies(args: dict[str, Any]) -> dict[str, Any]:
    import logging as _logging

    from app.core.config import settings
    from app.workers.main import enrich_contact_task

    _log = _logging.getLogger(__name__)
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

    saved: list[tuple[str, str | None]] = []
    for c in companies:
        website = c.get("website")
        contact = Contact(
            id=uuid.uuid4(),
            user_id=user.id,
            list_id=contact_list.id,
            contact_name=c.get("name"),
            email=c.get("email"),
            phone=c.get("phone"),
            enrichment={"website_summary": c.get("website_summary"), "website": website},
            raw=c,
        )
        db.add(contact)
        saved.append((str(contact.id), website))

    await db.commit()

    # Обогащение только для контактов с сайтом — иначе worker сразу вернёт no_website
    enrich_queued = 0
    if settings.llm_enrich_provider != "disabled":
        for cid, website in saved:
            if not website:
                continue
            try:
                await enrich_contact_task.defer_async(contact_id=cid)
                enrich_queued += 1
            except Exception as exc:
                _log.warning("save_companies: defer enrich failed (%s) — skipping", exc)
                break

    return {
        "list_id": str(contact_list.id),
        "list_name": list_name,
        "saved": len(saved),
        "enrich_queued": enrich_queued,
    }


async def _handle_get_company_info(args: dict[str, Any]) -> dict[str, Any]:
    from app.models.company import Company

    db: AsyncSession = args.pop("__db")
    user: User = args.pop("__user")

    contact_id: str | None = args.get("contact_id")
    company_name: str | None = args.get("company_name")

    if contact_id:
        try:
            cid = uuid.UUID(contact_id)
        except ValueError:
            return {"error": "invalid_uuid"}
        row = await db.execute(select(Contact).where(Contact.id == cid, Contact.user_id == user.id))
        contact = row.scalar_one_or_none()
        if not contact:
            return {"error": "not_found", "message": "Контакт не найден"}

        enrichment = contact.enrichment or {}
        result: dict[str, Any] = {
            "contact_id": str(contact.id),
            "name": contact.contact_name,
            "email": contact.email,
            "position": contact.position,
            "status": contact.status,
        }
        if enrichment.get("description"):
            result["description"] = enrichment["description"]
        if enrichment.get("services"):
            result["services"] = enrichment["services"]
        if enrichment.get("target"):
            result["target"] = enrichment["target"]
        if enrichment.get("city"):
            result["city"] = enrichment["city"]
        if not enrichment.get("description") and enrichment.get("website_summary"):
            result["website_summary"] = enrichment["website_summary"][:300]
        result["enriched"] = bool(enrichment.get("description"))
        return result

    if company_name:
        row = await db.execute(
            select(Company).where(
                Company.user_id == user.id,
                Company.name.ilike(f"%{company_name}%"),
            ).limit(1)
        )
        company = row.scalar_one_or_none()
        if not company:
            # Попробуем по контактам
            row2 = await db.execute(
                select(Contact).where(
                    Contact.user_id == user.id,
                    Contact.contact_name.ilike(f"%{company_name}%"),
                ).limit(1)
            )
            contact = row2.scalar_one_or_none()
            if contact:
                enrichment = contact.enrichment or {}
                return {
                    "contact_id": str(contact.id),
                    "name": contact.contact_name,
                    "description": enrichment.get("description"),
                    "services": enrichment.get("services"),
                    "city": enrichment.get("city") or contact.raw and contact.raw.get("city"),
                    "enriched": bool(enrichment.get("description")),
                }
            return {"error": "not_found", "message": f"Компания «{company_name}» не найдена в базе"}

        return {
            "company_id": str(company.id),
            "name": company.name,
            "industry": company.industry,
            "city": company.city,
            "website": company.website,
            "notes": company.notes,
        }

    return {"error": "missing_params", "message": "Укажи contact_id или company_name"}


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
    "import_contacts": _handle_import_contacts,
    "save_companies": _handle_save_companies,
    "get_company_info": _handle_get_company_info,
    "enrich_contacts": _handle_enrich_contacts,
    "create_campaign": _handle_create_campaign,
    "send_campaign": _handle_send_campaign,
    "list_resources": _handle_list_resources,
    "check_inbox": _handle_check_inbox,
    "suggest_reply": _handle_suggest_reply,
    "update_contact": _handle_update_contact,
    "set_reminder": _handle_set_reminder,
}
