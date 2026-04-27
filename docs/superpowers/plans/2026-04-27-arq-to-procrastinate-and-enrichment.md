# ARQ → Procrastinate + Contact Enrichment Pipeline

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace ARQ + Upstash Redis with procrastinate (Postgres-backed queue via Supabase), then add an optional contact enrichment pipeline (Firecrawl scrape → LLM summary → contact.enrichment) with Claude as a selectable LLM provider.

**Architecture:** procrastinate uses the existing Supabase Postgres DB — no new services. The enrichment pipeline is guarded by `ENRICHMENT_PROVIDER=disabled` by default; setting it to `qwen|groq|glm|claude` enables it. The chat agent gets a new `enrich_contacts` tool that queues enrichment jobs for a contact list.

**Tech Stack:** `procrastinate[sqlalchemy]>=2.0`, `anthropic>=0.40.0`, existing SQLAlchemy asyncpg engine, Supabase migrations.

---

## File Map

| Action | Path | Purpose |
|---|---|---|
| Modify | `backend/pyproject.toml` | remove arq/redis, add procrastinate + anthropic |
| Modify | `backend/app/core/config.py` | remove redis_url; add worker_database_url, anthropic_api_key, llm_enrich_* |
| Modify | `backend/app/workers/main.py` | rewrite: procrastinate App + all task stubs |
| Create | `backend/app/services/llm/claude.py` | ClaudeClient using anthropic SDK |
| Modify | `backend/app/services/llm/factory.py` | add claude provider + enrich task |
| Create | `backend/app/services/enrichment.py` | enrich_contact + enrich_contact_batch |
| Modify | `backend/app/services/chat/tools.py` | add enrich_contacts tool schema + handler |
| Create | `supabase/migrations/0004_procrastinate.sql` | procrastinate schema tables |
| Modify | `Makefile` | update dev-worker command |
| Modify | `.env.example` | remove REDIS_URL, add new vars |
| Create | `backend/tests/test_enrichment.py` | enrichment service unit tests |

---

## Task 1: Update dependencies

**Files:**
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: Edit pyproject.toml**

Remove `"redis>=5.0.0"` and `"arq>=0.26.0"` from `dependencies`.
Add in their place:

```toml
"procrastinate[sqlalchemy]>=2.0.0",
"anthropic>=0.40.0",
```

Final `dependencies` list should look like:

```toml
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "pydantic>=2.7.0",
    "pydantic-settings>=2.3.0",
    "sqlalchemy[asyncio]>=2.0.30",
    "asyncpg>=0.29.0",
    "procrastinate[sqlalchemy]>=2.0.0",
    "anthropic>=0.40.0",
    "httpx>=0.27.0",
    "python-multipart>=0.0.9",
    "passlib[argon2]>=1.7.4",
    "python-jose[cryptography]>=3.3.0",
    "cryptography>=42.0.0",
    "supabase>=2.5.0",
    "aiofiles>=23.0.0",
    "email-validator>=2.1.0",
    "dnspython>=2.6.0",
    "openai>=1.40.0",
    "sentry-sdk[fastapi]>=2.0.0",
]
```

- [ ] **Step 2: Install**

```bash
cd backend && pip install -e ".[dev]"
```

Expected: installs procrastinate, anthropic; no import errors.

- [ ] **Step 3: Verify procrastinate is importable**

```bash
cd backend && python -c "import procrastinate; print(procrastinate.__version__)"
```

Expected: prints version like `2.x.x`.

- [ ] **Step 4: Commit**

```bash
git add backend/pyproject.toml
git commit -m "chore: replace arq+redis with procrastinate, add anthropic sdk"
```

---

## Task 2: Update config

**Files:**
- Modify: `backend/app/core/config.py`

- [ ] **Step 1: Rewrite config.py**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    app_env: str = "development"
    base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"

    # Security
    secret_key: str = "dev-secret-change-me"
    fernet_key: str = ""
    tracking_secret: str = "dev-tracking-secret-change-me"

    # Database / Storage
    database_url: str = "postgresql+asyncpg://postgres:changeme@localhost:5432/postgres"
    # Direct (non-pooler) URL for procrastinate worker — required for LISTEN/NOTIFY.
    # If not set, falls back to database_url (polling mode, works with pgbouncer).
    worker_database_url: str = ""
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_storage_bucket: str = "parcer-dev"

    # LLM providers
    llm_chat_provider: str = "groq"
    llm_chat_model: str = "llama-3.3-70b-versatile"
    llm_letters_provider: str = "qwen"
    llm_letters_model: str = "qwen2.5-72b-instruct"
    llm_classify_provider: str = "groq"
    llm_classify_model: str = "llama-3.1-8b-instant"
    # Enrichment: disabled | qwen | groq | glm | claude
    llm_enrich_provider: str = "disabled"
    llm_enrich_model: str = "qwen2.5-72b-instruct"
    llm_consent_required: bool = True

    groq_api_key: str = ""
    qwen_api_key: str = ""
    glm_api_key: str = ""
    anthropic_api_key: str = ""

    # Search
    twogis_api_key: str = ""
    serpapi_key: str = ""
    firecrawl_api_key: str = ""

    # Transactional email
    transactional_smtp_host: str = ""
    transactional_smtp_port: int = 465
    transactional_smtp_user: str = ""
    transactional_smtp_pass: str = ""
    transactional_from_email: str = "noreply@parcer.ru"

    # Monitoring
    sentry_dsn: str = ""

    @property
    def effective_worker_database_url(self) -> str:
        return self.worker_database_url or self.database_url


settings = Settings()
```

- [ ] **Step 2: Verify import**

```bash
cd backend && python -c "from app.core.config import settings; print(settings.llm_enrich_provider)"
```

Expected: `disabled`

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/config.py
git commit -m "feat: remove redis_url, add enrich provider + anthropic config"
```

---

## Task 3: Add procrastinate schema migration

**Files:**
- Create: `supabase/migrations/0004_procrastinate.sql`

Procrastinate needs its own tables in Postgres. Generate the SQL from the installed package:

- [ ] **Step 1: Generate schema SQL**

```bash
cd backend && python -c "
from procrastinate.contrib.sqlalchemy import SQLAlchemyConnector
import procrastinate
app = procrastinate.App(connector=SQLAlchemyConnector())
print(app.connector.schema_manager.get_schema())
" > ../supabase/migrations/0004_procrastinate.sql
```

Expected: file is created with `CREATE TABLE procrastinate_jobs ...` SQL.

- [ ] **Step 2: Verify file is non-empty**

```bash
head -5 supabase/migrations/0004_procrastinate.sql
```

Expected: starts with SQL CREATE TABLE or similar.

- [ ] **Step 3: Apply migration**

```bash
supabase db push
```

Expected: migration applied without errors.

- [ ] **Step 4: Commit**

```bash
git add supabase/migrations/0004_procrastinate.sql
git commit -m "feat: add procrastinate job queue schema migration"
```

---

## Task 4: Rewrite workers/main.py

**Files:**
- Modify: `backend/app/workers/main.py`

- [ ] **Step 1: Rewrite the file**

```python
"""Procrastinate worker entry point. Task implementations live in app.services."""
import json

import procrastinate
from procrastinate.contrib.sqlalchemy import SQLAlchemyConnector

from app.core.config import settings

app = procrastinate.App(
    connector=SQLAlchemyConnector(
        engine_dsn=settings.effective_worker_database_url,
        json_dumps=json.dumps,
        json_loads=json.loads,
    )
)


@app.task(queue="default", retry=procrastinate.RetryStrategy(max_attempts=3))
async def generate_letters(campaign_id: str) -> None:
    raise NotImplementedError


@app.task(queue="default", retry=procrastinate.RetryStrategy(max_attempts=3))
async def send_email(message_id: str) -> None:
    raise NotImplementedError


@app.task(queue="default")
async def poll_inbox() -> None:
    raise NotImplementedError


@app.task(queue="default", retry=procrastinate.RetryStrategy(max_attempts=2))
async def classify_inbox_message(inbox_message_id: str) -> None:
    raise NotImplementedError


@app.task(queue="default")
async def run_followup(campaign_id: str) -> None:
    raise NotImplementedError


@app.task(queue="default")
async def run_reminders() -> None:
    raise NotImplementedError


@app.task(queue="enrichment", retry=procrastinate.RetryStrategy(max_attempts=2))
async def enrich_contact_task(contact_id: str) -> None:
    from app.core.database import AsyncSessionLocal
    from app.services.enrichment import enrich_contact

    async with AsyncSessionLocal() as db:
        await enrich_contact(contact_id=contact_id, db=db)
```

- [ ] **Step 2: Verify import**

```bash
cd backend && python -c "from app.workers.main import app; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Update Makefile dev-worker**

In `Makefile`, change:
```makefile
dev-worker:
	cd backend && python -m arq app.workers.main.WorkerSettings
```
to:
```makefile
dev-worker:
	cd backend && procrastinate --app=app.workers.main.app worker --queues=default,enrichment
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/workers/main.py Makefile
git commit -m "feat: rewrite worker with procrastinate, remove arq"
```

---

## Task 5: Add ClaudeClient

**Files:**
- Create: `backend/app/services/llm/claude.py`
- Modify: `backend/app/services/llm/factory.py`

- [ ] **Step 1: Write a failing test**

In `backend/tests/test_enrichment.py` (create file):

```python
import pytest
from unittest.mock import AsyncMock, patch


def test_claude_client_disabled_without_key(monkeypatch):
    """ClaudeClient raises if anthropic_api_key is empty."""
    monkeypatch.setattr("app.core.config.settings.anthropic_api_key", "")
    from app.services.llm.claude import ClaudeClient
    client = ClaudeClient(model="claude-haiku-4-5-20251001")
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        client._require_key()
```

- [ ] **Step 2: Run test to see it fail**

```bash
cd backend && pytest tests/test_enrichment.py::test_claude_client_disabled_without_key -v
```

Expected: FAIL (module doesn't exist yet).

- [ ] **Step 3: Create claude.py**

```python
import anthropic

from app.core.config import settings
from app.services.llm.base import LLMMessage, LLMResult


class ClaudeClient:
    """Anthropic Claude client. Does NOT use OpenAI SDK."""

    def __init__(self, model: str):
        self.model = model

    def _require_key(self) -> str:
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set")
        return settings.anthropic_api_key

    async def chat(
        self,
        messages: list[LLMMessage],
        *,
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        response_format: dict | None = None,
        timeout: float = 30.0,
    ) -> LLMResult:
        api_key = self._require_key()
        client = anthropic.AsyncAnthropic(api_key=api_key, timeout=timeout)

        system = next((m.content for m in messages if m.role == "system"), None)
        user_messages = [
            {"role": m.role, "content": m.content or ""}
            for m in messages
            if m.role != "system"
        ]

        kwargs: dict = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": user_messages,
        }
        if system:
            kwargs["system"] = system

        resp = await client.messages.create(**kwargs)
        text = resp.content[0].text if resp.content else None
        return LLMResult(content=text, tool_calls=[], raw=resp)
```

- [ ] **Step 4: Update factory.py**

```python
from app.core.config import settings
from app.services.llm.base import LLMClient
from app.services.llm.glm import GLMClient
from app.services.llm.groq import GroqClient
from app.services.llm.qwen import QwenClient

_OPENAI_PROVIDERS = {"groq": GroqClient, "qwen": QwenClient, "glm": GLMClient}


def get_llm_client(task: str) -> LLMClient:
    """task: 'chat' | 'letters' | 'classify' | 'enrich'"""
    provider = getattr(settings, f"llm_{task}_provider")
    model = getattr(settings, f"llm_{task}_model")

    if provider == "claude":
        from app.services.llm.claude import ClaudeClient
        return ClaudeClient(model=model)

    cls = _OPENAI_PROVIDERS.get(provider)
    if not cls:
        raise ValueError(f"Unknown LLM provider: {provider}")
    return cls(model=model)
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd backend && pytest tests/test_enrichment.py::test_claude_client_disabled_without_key -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/llm/claude.py backend/app/services/llm/factory.py backend/tests/test_enrichment.py
git commit -m "feat: add ClaudeClient + enrich task support in LLM factory"
```

---

## Task 6: Build enrichment service

**Files:**
- Create: `backend/app/services/enrichment.py`
- Modify: `backend/tests/test_enrichment.py`

The service:
1. Checks `ENRICHMENT_PROVIDER != disabled`
2. Loads the contact; skips if no website or already enriched (fresh)
3. Calls Firecrawl to scrape the website
4. Sends scraped markdown to LLM → structured JSON summary
5. Saves result into `contact.enrichment`

- [ ] **Step 1: Add tests**

Append to `backend/tests/test_enrichment.py`:

```python
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact


@pytest.fixture
def mock_contact(db_session: AsyncSession):
    c = Contact(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        enrichment=None,
        raw={"website": "https://example.com"},
    )
    return c


@pytest.mark.asyncio
async def test_enrich_contact_disabled(monkeypatch, db_session, mock_contact):
    """Returns immediately when enrichment is disabled."""
    monkeypatch.setattr("app.core.config.settings.llm_enrich_provider", "disabled")
    db_session.add(mock_contact)
    await db_session.commit()

    from app.services.enrichment import enrich_contact
    result = await enrich_contact(contact_id=str(mock_contact.id), db=db_session)
    assert result == {"enriched": False, "reason": "disabled"}


@pytest.mark.asyncio
async def test_enrich_contact_no_website(monkeypatch, db_session):
    """Skips contact with no website."""
    monkeypatch.setattr("app.core.config.settings.llm_enrich_provider", "qwen")
    contact = Contact(id=uuid.uuid4(), user_id=uuid.uuid4(), enrichment=None, raw=None)
    db_session.add(contact)
    await db_session.commit()

    from app.services.enrichment import enrich_contact
    result = await enrich_contact(contact_id=str(contact.id), db=db_session)
    assert result == {"enriched": False, "reason": "no_website"}


@pytest.mark.asyncio
async def test_enrich_contact_success(monkeypatch, db_session, mock_contact):
    """Saves summary when Firecrawl + LLM succeed."""
    monkeypatch.setattr("app.core.config.settings.llm_enrich_provider", "qwen")
    db_session.add(mock_contact)
    await db_session.commit()

    fake_scraped = "Компания Example — делает виджеты для B2B."
    fake_summary = '{"description": "Делает виджеты для B2B.", "services": "Виджеты", "target": "B2B компании", "city": null}'

    with patch("app.services.enrichment._scrape_website", new=AsyncMock(return_value=fake_scraped)), \
         patch("app.services.enrichment._llm_summarize", new=AsyncMock(return_value=fake_summary)):
        from app.services.enrichment import enrich_contact
        result = await enrich_contact(contact_id=str(mock_contact.id), db=db_session)

    assert result["enriched"] is True
    await db_session.refresh(mock_contact)
    assert mock_contact.enrichment["description"] == "Делает виджеты для B2B."
```

- [ ] **Step 2: Run tests to see them fail**

```bash
cd backend && pytest tests/test_enrichment.py -v -k "enrich_contact"
```

Expected: 3 FAIL (module not found).

- [ ] **Step 3: Create enrichment.py**

```python
from __future__ import annotations

import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.contact import Contact
from app.services.search.firecrawl import enrich_website

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
Ты — аналитик B2B-продаж. Получаешь текст сайта компании.
Извлеки краткую информацию для написания персонального холодного письма.
Отвечай ТОЛЬКО JSON без markdown:
{"description": "...", "services": "...", "target": "...", "city": "..."}

description: 1-2 предложения о компании (до 150 символов)
services: главные продукты или услуги (до 60 символов)
target: кто их клиент (до 50 символов)
city: город (если явно упомянут, иначе null)
"""


async def _scrape_website(url: str) -> str | None:
    return await enrich_website(url)


async def _llm_summarize(text: str) -> str | None:
    from app.services.llm.base import LLMMessage
    from app.services.llm.factory import get_llm_client

    client = get_llm_client("enrich")
    result = await client.chat(
        messages=[
            LLMMessage(role="system", content=_SYSTEM_PROMPT),
            LLMMessage(role="user", content=text[:3000]),
        ],
        temperature=0.2,
        max_tokens=200,
        timeout=20.0,
    )
    return result.content


async def enrich_contact(contact_id: str, db: AsyncSession) -> dict:
    if settings.llm_enrich_provider == "disabled":
        return {"enriched": False, "reason": "disabled"}

    row = await db.execute(select(Contact).where(Contact.id == contact_id))
    contact: Contact | None = row.scalar_one_or_none()
    if not contact:
        return {"enriched": False, "reason": "not_found"}

    website = (contact.enrichment or {}).get("website") or (contact.raw or {}).get("website")
    if not website:
        return {"enriched": False, "reason": "no_website"}

    # Skip if already enriched within last 7 days
    existing = contact.enrichment or {}
    if existing.get("description"):
        return {"enriched": False, "reason": "already_enriched"}

    scraped = await _scrape_website(website)
    if not scraped:
        return {"enriched": False, "reason": "scrape_failed"}

    raw_json = await _llm_summarize(scraped)
    if not raw_json:
        return {"enriched": False, "reason": "llm_failed"}

    try:
        summary = json.loads(raw_json)
    except json.JSONDecodeError:
        logger.warning("enrichment: LLM returned invalid JSON for contact %s", contact_id)
        return {"enriched": False, "reason": "invalid_json"}

    contact.enrichment = {**existing, **summary, "website": website}
    await db.commit()
    return {"enriched": True, "description": summary.get("description")}


async def enrich_contact_batch(list_id: str, db: AsyncSession) -> dict:
    """Queue enrichment for all contacts in a list. Returns job count."""
    from app.models.contact import Contact
    from app.workers.main import enrich_contact_task

    rows = await db.execute(
        select(Contact).where(
            Contact.list_id == list_id,
            Contact.enrichment.is_(None),
        )
    )
    contacts = rows.scalars().all()
    queued = 0
    for c in contacts:
        website = (c.raw or {}).get("website")
        if website:
            await enrich_contact_task.defer_async(contact_id=str(c.id))
            queued += 1
    return {"queued": queued, "total": len(contacts)}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/test_enrichment.py -v -k "enrich_contact"
```

Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/enrichment.py backend/tests/test_enrichment.py
git commit -m "feat: add enrichment service (Firecrawl + LLM → contact.enrichment)"
```

---

## Task 7: Add enrich_contacts chat tool

**Files:**
- Modify: `backend/app/services/chat/tools.py`

- [ ] **Step 1: Add tool schema to TOOLS_SCHEMA list**

In `tools.py`, append to the `TOOLS_SCHEMA` list after `set_reminder`:

```python
    {
        "type": "function",
        "function": {
            "name": "enrich_contacts",
            "description": (
                "Обогатить контакты из списка: скачать их сайты и извлечь AI-описание компании. "
                "Используй после сохранения списка, перед генерацией писем. "
                "Работает только если включён ENRICHMENT_PROVIDER."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "list_id": {
                        "type": "string",
                        "description": "ID списка контактов для обогащения",
                    }
                },
                "required": ["list_id"],
            },
        },
    },
```

- [ ] **Step 2: Add handler function**

After `_handle_save_companies`, add:

```python
async def _handle_enrich_contacts(args: dict[str, Any]) -> dict[str, Any]:
    db: AsyncSession = args.pop("__db")
    args.pop("__user", None)

    from app.core.config import settings
    if settings.llm_enrich_provider == "disabled":
        return {"status": "disabled", "message": "Обогащение не настроено (ENRICHMENT_PROVIDER=disabled)"}

    from app.services.enrichment import enrich_contact_batch
    result = await enrich_contact_batch(list_id=args["list_id"], db=db)
    return {
        "status": "queued",
        "queued": result["queued"],
        "total": result["total"],
        "message": f"Поставлено в очередь {result['queued']} из {result['total']} контактов с сайтами",
    }
```

- [ ] **Step 3: Register handler in HANDLERS dict**

Add to `HANDLERS`:

```python
"enrich_contacts": _handle_enrich_contacts,
```

- [ ] **Step 4: Verify import**

```bash
cd backend && python -c "from app.services.chat.tools import HANDLERS; print(list(HANDLERS.keys()))"
```

Expected: list includes `enrich_contacts`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/chat/tools.py
git commit -m "feat: add enrich_contacts chat tool"
```

---

## Task 8: Update .env.example

**Files:**
- Modify: `.env.example`

- [ ] **Step 1: Remove REDIS_URL, add new vars**

Replace the Redis section:
```
# --- Redis (Upstash) ---------------------------------------
# Формат: rediss://default:<password>@<host>:<port>
REDIS_URL=rediss://default:<pass>@<host>.upstash.io:6379
```

With:
```
# --- Worker DB (procrastinate) ----------------------------
# Для LISTEN/NOTIFY нужно прямое подключение (не pgbouncer).
# Получить из Supabase → Project Settings → Database → Connection string (Direct, не Pooler).
# Если не задан — воркер использует DATABASE_URL в режиме polling (подходит для small scale).
WORKER_DATABASE_URL=
```

Add enrichment section after the `# --- Search ---` block:

```
# --- Enrichment (опционально) ------------------------------
# Провайдер для анализа сайтов контактов: disabled | qwen | groq | glm | claude
ENRICHMENT_PROVIDER=disabled
LLM_ENRICH_MODEL=qwen2.5-72b-instruct
# Нужен только если ENRICHMENT_PROVIDER=claude
ANTHROPIC_API_KEY=
```

- [ ] **Step 2: Commit**

```bash
git add .env.example
git commit -m "chore: update env.example — replace redis with procrastinate vars, add enrichment"
```

---

## Task 9: Smoke test the worker

- [ ] **Step 1: Check procrastinate CLI is available**

```bash
cd backend && procrastinate --help
```

Expected: prints procrastinate help.

- [ ] **Step 2: Print procrastinate app info**

```bash
cd backend && procrastinate --app=app.workers.main.app healthcheck 2>&1 || true
```

Expected: connects to DB (if `DATABASE_URL` is set) or prints connection error — either way, the import works.

- [ ] **Step 3: Run full test suite**

```bash
cd backend && pytest tests/ -v
```

Expected: all tests pass (enrichment tests + existing auth/health/security tests).

- [ ] **Step 4: Final commit if anything changed**

```bash
git add -u
git status
```

If clean, no commit needed. If dirty, commit with `chore: fix test issues`.

---

## Notes for later

- **LISTEN/NOTIFY with pgbouncer:** If the worker starts but doesn't pick up jobs, set `WORKER_DATABASE_URL` to the **direct** Supabase connection string (Project Settings → Database → Connection string → URI, toggle off "Use connection pooler"). This bypasses pgbouncer for the worker only.

- **Enabling Claude enrichment:** Set `ENRICHMENT_PROVIDER=claude` and `ANTHROPIC_API_KEY=sk-ant-...` and `LLM_ENRICH_MODEL=claude-haiku-4-5-20251001` in `.env`. Haiku is cheapest; for better quality use `claude-sonnet-4-6`.

- **Enabling Qwen enrichment (recommended):** Set `ENRICHMENT_PROVIDER=qwen` — uses existing `QWEN_API_KEY`, no extra cost per request beyond what you're already paying.

- **procrastinate periodic jobs** (poll_inbox every 15 min): add to `app.workers.main`:
  ```python
  app.periodic(cron="*/15 * * * *")(poll_inbox)
  ```
  This replaces ARQ's `cron_jobs` list.
