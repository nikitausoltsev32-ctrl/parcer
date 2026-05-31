"""Quick smoke test: run lead search and report timing, model routing, results."""
import asyncio
import time
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.lead import Lead
from app.models.lead_processing_log import LeadProcessingLog
from app.models.user import User
from app.services.leads.pipeline import run_lead_search
from app.services.llm.routing import STAGE_ROUTING, resolve_stage


def print_routing():
    print("\n=== Текущий роутинг ===")
    for stage in STAGE_ROUTING:
        provider, model = resolve_stage(stage)
        print(f"  {stage:<16} -> {provider}/{model}")


async def main():
    print_routing()

    url = settings.database_url.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
    engine = create_async_engine(url, echo=False)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with SessionLocal() as db:
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                id=uuid.uuid4(),
                email="test_search@lida.ai",
                password_hash="placeholder",
                plan="dev",
                leads_quota=10_000,
                ai_credits_balance=100_000,
            )
            db.add(user)
            await db.commit()
            print(f"\nСоздан тестовый пользователь: {user.email} plan=dev")
        else:
            if user.plan != "dev":
                user.plan = "dev"
                user.leads_quota = 10_000
                user.ai_credits_balance = 100_000
                await db.commit()
            print(f"\nПользователь: {user.email} | plan={user.plan} quota={user.leads_quota} credits={user.ai_credits_balance}")

        query = "стоматологии"
        city = "Екатеринбург"
        limit = 5

        log_id = uuid.uuid4()
        pre_log = LeadProcessingLog(
            id=log_id,
            user_id=user.id,
            search_query_original=query,
            outcome="pending",
            meta={"city": city, "limit": limit, "target": limit, "progress": {"target": limit}},
        )
        db.add(pre_log)
        await db.commit()

        user_id = user.id  # capture before pipeline expires the ORM object

        print(f"\n=== Запуск: '{query}' в {city}, limit={limit} ===")
        t0 = time.monotonic()
        try:
            result = await run_lead_search(
                db,
                user=user,
                query=query,
                city=city,
                limit=limit,
                list_name=f"Test {query} {city}",
                generate_outreach_messages=False,
                pre_log_id=log_id,
                fast_mode=True,
            )
            elapsed = time.monotonic() - t0
            print(f"\nГотово за {elapsed:.1f}с | сохранено: {result.saved}/{limit}")
        except Exception as exc:
            elapsed = time.monotonic() - t0
            print(f"\nОШИБКА за {elapsed:.1f}с: {exc}")
            raise

        log = await db.get(LeadProcessingLog, log_id)
        if log and log.meta:
            p = log.meta.get("progress", {})
            print(f"Стадия: {p.get('stage')} | найдено URL: {log.urls_found} | после фильтра: {log.urls_after_filter}")
            print(f"Краулинг: {log.urls_crawled} сайтов | LLM-вызовов: {len(log.llm_calls or [])} | cost: ${log.total_cost_usd:.4f}")
            events = log.meta.get("events", [])
            if events:
                print("\nСобытия пайплайна:")
                for e in events:
                    print(f"  [{e['stage']:12}] {e['message']}")

        leads_res = await db.execute(select(Lead).where(Lead.user_id == user_id).order_by(Lead.created_at.desc()).limit(limit))
        leads = leads_res.scalars().all()
        print(f"\n=== Лиды ({len(leads)}) ===")
        for lead in leads:
            score = (lead.lead_fit or {}).get("score", "?")
            ai_level = (lead.processing or {}).get("ai_level", "?")
            print(f"  [{score:>3}] {lead.company_name or lead.domain:<30} {lead.phone or '':>16}  {lead.email or '':<25}  ai={ai_level}")


if __name__ == "__main__":
    asyncio.run(main())
