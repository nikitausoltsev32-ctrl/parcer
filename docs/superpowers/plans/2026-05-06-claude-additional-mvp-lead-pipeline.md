# Claude Additional MVP Lead Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first working vertical lead-search pipeline from `CLAUDE_ADDITIONAL.md`: query -> public search -> deterministic filtering/extraction -> contact list persistence -> UI visibility.

**Architecture:** Use existing `contacts` and `contact_lists` as MVP lead storage instead of adding a separate `leads` table now. Keep deterministic extraction and scoring in focused `app/services/leads/*` modules; use existing `app/services/search.search_companies` for providers. Add minimal observability with a dedicated processing-log table, but do not implement tariffs, billing, AI credits enforcement, or production LLM routing in this pass.

**Tech Stack:** FastAPI, SQLAlchemy async, Pydantic v2, pytest/pytest-asyncio, React/Vite/TypeScript, TanStack Query.

---

## Current Code Facts

- `backend/app/models/contact.py` already has `ContactList` and `Contact` with `raw` and `enrichment` JSON fields. This is enough for MVP lead storage.
- `backend/app/services/search/__init__.py` already merges SerpAPI Maps + Google Search, deduplicates by domain/name, enriches first sites with Firecrawl summaries, and optionally Hunter email.
- `backend/app/services/chat/tools.py` already has chat tools `search_companies`, `save_companies`, and `enrich_contacts`, but `ChatPage` save button is currently UI-local and does not call save.
- `backend/app/api/v1/companies.py` is still 501 and should not be used as the primary path for this MVP.
- `frontend/src/pages/ContactsPage.tsx` already lists contacts and imports files. It is the best first screen to add direct lead search because saved results already appear there.
- `CLAUDE_ADDITIONAL.md` says anti-hallucination is critical. Therefore extraction must store missing email/phone as `None`, never fabricate values.

---

## File Structure

- Create `backend/app/services/leads/__init__.py`: package export surface.
- Create `backend/app/services/leads/extraction.py`: URL/domain normalization, deterministic email/phone/social extraction, candidate normalization.
- Create `backend/app/services/leads/scoring.py`: simple deterministic score/confidence from available public facts.
- Create `backend/app/services/leads/pipeline.py`: orchestrates search results into `ContactList` and `Contact` rows with step log data.
- Create `backend/app/models/lead_processing_log.py`: lightweight processing log table model.
- Modify `backend/app/models/__init__.py`: import `LeadProcessingLog`.
- Create `supabase/migrations/20260506120000_lead_processing_logs.sql`: DB migration for processing logs.
- Create `backend/app/schemas/lead_search.py`: request/response schemas.
- Create `backend/app/api/v1/lead_search.py`: authenticated direct lead search endpoint.
- Modify `backend/app/api/v1/router.py`: include lead search router.
- Modify `backend/app/api/v1/contacts.py`: return website/city/industry/enrichment fields needed by Companies/Contacts UI.
- Create `backend/tests/test_lead_extraction.py`: extraction unit tests.
- Create `backend/tests/test_lead_pipeline.py`: pipeline persistence tests with mocked search.
- Create `backend/tests/test_lead_search_api.py`: API happy path and validation tests.
- Create `frontend/src/components/LeadSearchPanel.tsx`: compact search form and result summary.
- Modify `frontend/src/pages/ContactsPage.tsx`: mount search panel and refresh contacts after save.
- Modify `frontend/src/pages/CompaniesPage.tsx`: consume enriched contact fields that `/contacts` now returns.

---

### Task 1: Deterministic Extraction

**Files:**
- Create: `backend/app/services/leads/__init__.py`
- Create: `backend/app/services/leads/extraction.py`
- Test: `backend/tests/test_lead_extraction.py`

- [ ] **Step 1: Write failing tests**

Add `backend/tests/test_lead_extraction.py`:

```python
from app.services.leads.extraction import (
    extract_public_contacts,
    normalize_domain,
    normalize_website,
)


def test_normalize_website_adds_scheme_and_strips_tracking_path_noise():
    assert normalize_website("www.example.ru/contacts?utm_source=ad") == "https://www.example.ru/contacts"


def test_normalize_domain_removes_www_and_path():
    assert normalize_domain("https://www.example.ru/contacts") == "example.ru"


def test_extract_public_contacts_finds_real_contacts_and_social_links():
    text = """
    Связь: hello@example.ru, +7 (343) 222-33-44.
    Telegram: https://t.me/example_sales
    WhatsApp: https://wa.me/73432223344
    VK: https://vk.com/example
    """

    result = extract_public_contacts(text)

    assert result.email == "hello@example.ru"
    assert result.phone == "+7 (343) 222-33-44"
    assert result.telegram == "https://t.me/example_sales"
    assert result.whatsapp == "https://wa.me/73432223344"
    assert result.vk == "https://vk.com/example"


def test_extract_public_contacts_returns_none_without_fabricating_data():
    result = extract_public_contacts("Компания делает сайты. Контакты скрыты.")

    assert result.email is None
    assert result.phone is None
    assert result.telegram is None
    assert result.whatsapp is None
    assert result.vk is None
```

- [ ] **Step 2: Verify tests fail**

Run:

```powershell
cd backend
pytest tests/test_lead_extraction.py -v
```

Expected: import failure because `app.services.leads.extraction` does not exist.

- [ ] **Step 3: Implement extraction module**

Create `backend/app/services/leads/__init__.py`:

```python
"""Lead search pipeline helpers."""
```

Create `backend/app/services/leads/extraction.py` with:

```python
from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit


_EMAIL_RE = re.compile(r"(?<![\w.+-])([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})(?![\w.+-])", re.IGNORECASE)
_PHONE_RE = re.compile(r"(\+?7|8)?[\s(.-]*\d{3}[\s). -]*\d{3}[\s.-]*\d{2}[\s.-]*\d{2}")
_TG_RE = re.compile(r"https?://t\.me/[A-Za-z0-9_]{4,}", re.IGNORECASE)
_WA_RE = re.compile(r"https?://(?:wa\.me|api\.whatsapp\.com/send\?phone=)[^\s)]+", re.IGNORECASE)
_VK_RE = re.compile(r"https?://vk\.com/[A-Za-z0-9_.-]+", re.IGNORECASE)


@dataclass(frozen=True)
class ExtractedPublicContacts:
    email: str | None = None
    phone: str | None = None
    telegram: str | None = None
    whatsapp: str | None = None
    vk: str | None = None


def normalize_website(value: str | None) -> str | None:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    if not raw.startswith(("http://", "https://")):
        raw = f"https://{raw}"
    parsed = urlsplit(raw)
    if not parsed.netloc:
        return None
    path = parsed.path.rstrip("/") or ""
    return urlunsplit((parsed.scheme, parsed.netloc.lower(), path, "", ""))


def normalize_domain(value: str | None) -> str:
    website = normalize_website(value)
    if not website:
        return ""
    host = urlsplit(website).netloc.lower()
    return host.removeprefix("www.")


def extract_public_contacts(text: str | None) -> ExtractedPublicContacts:
    source = text or ""
    email = _first(_EMAIL_RE, source)
    phone = _first(_PHONE_RE, source)
    telegram = _first(_TG_RE, source)
    whatsapp = _first(_WA_RE, source)
    vk = _first(_VK_RE, source)
    return ExtractedPublicContacts(email=email, phone=phone, telegram=telegram, whatsapp=whatsapp, vk=vk)


def _first(pattern: re.Pattern[str], value: str) -> str | None:
    match = pattern.search(value)
    return match.group(0).strip(".,; ") if match else None
```

- [ ] **Step 4: Verify green**

Run:

```powershell
cd backend
pytest tests/test_lead_extraction.py -v
```

Expected: 4 passed.

---

### Task 2: Deterministic Scoring

**Files:**
- Create: `backend/app/services/leads/scoring.py`
- Test: `backend/tests/test_lead_scoring.py`

- [ ] **Step 1: Write failing tests**

Add `backend/tests/test_lead_scoring.py`:

```python
from app.services.leads.scoring import score_candidate


def test_score_candidate_prioritizes_site_and_contacts():
    result = score_candidate({
        "name": "Studio One",
        "website": "https://studio.test",
        "email": "hello@studio.test",
        "phone": "+7 999 000-00-00",
        "website_summary": "B2B website studio",
    })

    assert result.score >= 80
    assert result.priority == "high"
    assert result.confidence == "verified"


def test_score_candidate_does_not_inflate_missing_contacts():
    result = score_candidate({"name": "Studio One", "website": None, "email": None, "phone": None})

    assert result.score < 50
    assert result.priority == "low"
    assert result.confidence == "missing"
```

- [ ] **Step 2: Verify red**

Run:

```powershell
cd backend
pytest tests/test_lead_scoring.py -v
```

Expected: import failure because `app.services.leads.scoring` does not exist.

- [ ] **Step 3: Implement scoring**

Create `backend/app/services/leads/scoring.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CandidateScore:
    score: int
    priority: str
    confidence: str
    reason: str


def score_candidate(candidate: dict[str, Any]) -> CandidateScore:
    score = 0
    reasons: list[str] = []

    if candidate.get("name"):
        score += 15
        reasons.append("есть название")
    if candidate.get("website"):
        score += 30
        reasons.append("есть сайт")
    if candidate.get("email"):
        score += 25
        reasons.append("есть email")
    if candidate.get("phone"):
        score += 20
        reasons.append("есть телефон")
    if candidate.get("website_summary"):
        score += 10
        reasons.append("есть краткое описание сайта")

    score = min(score, 100)
    if score >= 75:
        priority = "high"
    elif score >= 50:
        priority = "medium"
    else:
        priority = "low"

    if candidate.get("email") or candidate.get("phone"):
        confidence = "verified"
    elif candidate.get("website"):
        confidence = "inferred"
    else:
        confidence = "missing"

    return CandidateScore(score=score, priority=priority, confidence=confidence, reason=", ".join(reasons))
```

- [ ] **Step 4: Verify green**

Run:

```powershell
cd backend
pytest tests/test_lead_scoring.py -v
```

Expected: 2 passed.

---

### Task 3: Lead Processing Log Table

**Files:**
- Create: `backend/app/models/lead_processing_log.py`
- Modify: `backend/app/models/__init__.py`
- Create: `supabase/migrations/20260506120000_lead_processing_logs.sql`
- Test: covered by `backend/tests/test_lead_pipeline.py` in Task 4.

- [ ] **Step 1: Add model**

Create `backend/app/models/lead_processing_log.py`:

```python
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LeadProcessingLog(Base):
    __tablename__ = "lead_processing_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    contact_list_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("contact_lists.id", ondelete="SET NULL"), nullable=True)
    search_query_original: Mapped[str] = mapped_column(String, default="")
    search_queries_generated: Mapped[list | None] = mapped_column(JSON, nullable=True)
    urls_found: Mapped[int] = mapped_column(Integer, default=0)
    urls_after_filter: Mapped[int] = mapped_column(Integer, default=0)
    urls_crawled: Mapped[int] = mapped_column(Integer, default=0)
    pages_crawled_total: Mapped[int] = mapped_column(Integer, default=0)
    llm_calls: Mapped[list | None] = mapped_column(JSON, nullable=True)
    total_cost_usd: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    ai_credits_used: Mapped[int] = mapped_column(Integer, default=0)
    outcome: Mapped[str] = mapped_column(String, default="success")
    failure_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 2: Import model**

Add to `backend/app/models/__init__.py`:

```python
from app.models.lead_processing_log import LeadProcessingLog
```

- [ ] **Step 3: Add migration**

Create `supabase/migrations/20260506120000_lead_processing_logs.sql`:

```sql
create table if not exists public.lead_processing_logs (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,
    contact_list_id uuid references public.contact_lists(id) on delete set null,
    search_query_original text not null default '',
    search_queries_generated jsonb,
    urls_found int not null default 0,
    urls_after_filter int not null default 0,
    urls_crawled int not null default 0,
    pages_crawled_total int not null default 0,
    llm_calls jsonb,
    total_cost_usd numeric(10, 6),
    ai_credits_used int not null default 0,
    outcome text not null default 'success',
    failure_reason text,
    meta jsonb,
    created_at timestamptz not null default now()
);

create index if not exists idx_lead_processing_logs_user_id_created_at
    on public.lead_processing_logs(user_id, created_at desc);

create index if not exists idx_lead_processing_logs_contact_list_id
    on public.lead_processing_logs(contact_list_id);
```

---

### Task 4: Pipeline Persistence Service

**Files:**
- Create: `backend/app/services/leads/pipeline.py`
- Test: `backend/tests/test_lead_pipeline.py`

- [ ] **Step 1: Write failing pipeline test**

Add `backend/tests/test_lead_pipeline.py`:

```python
import uuid

from sqlalchemy import select

from app.models.contact import Contact, ContactList
from app.models.lead_processing_log import LeadProcessingLog
from app.models.user import User
from app.services.leads.pipeline import run_lead_search


async def test_run_lead_search_saves_contact_list_contacts_and_log(monkeypatch, db_session):
    user = User(id=uuid.uuid4(), email="lead@test.com", password_hash="hash")
    db_session.add(user)
    await db_session.commit()

    async def fake_search_companies(query: str, city: str | None, limit: int):
        return [
            {
                "name": "Studio One",
                "website": "https://studio.test",
                "email": None,
                "phone": "+7 999 000-00-00",
                "city": city,
                "industry": "Design",
                "address": "Baumana 1",
                "source": "serp_google",
                "website_summary": "B2B website studio. Email hello@studio.test",
            },
            {
                "name": "Studio One duplicate",
                "website": "https://studio.test/about",
                "email": "other@studio.test",
                "phone": None,
                "city": city,
                "source": "serp_google",
            },
        ]

    monkeypatch.setattr("app.services.leads.pipeline.search_companies", fake_search_companies)

    result = await run_lead_search(
        db_session,
        user=user,
        query="design studios",
        city="Kazan",
        limit=10,
        list_name="Design Kazan",
    )

    assert result.saved == 1
    assert result.list_name == "Design Kazan"
    assert result.contacts[0]["email"] == "hello@studio.test"
    assert result.contacts[0]["phone"] == "+7 999 000-00-00"
    assert result.contacts[0]["score"] >= 80

    contact_list = (await db_session.execute(select(ContactList))).scalar_one()
    contact = (await db_session.execute(select(Contact))).scalar_one()
    log = (await db_session.execute(select(LeadProcessingLog))).scalar_one()

    assert contact_list.source == "search"
    assert contact.raw["domain"] == "studio.test"
    assert contact.enrichment["lead_score"] == result.contacts[0]["score"]
    assert log.urls_found == 2
    assert log.urls_after_filter == 1
```

- [ ] **Step 2: Verify red**

Run:

```powershell
cd backend
pytest tests/test_lead_pipeline.py -v
```

Expected: import failure because `app.services.leads.pipeline` does not exist.

- [ ] **Step 3: Implement pipeline service**

Create `backend/app/services/leads/pipeline.py` with:

```python
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact, ContactList
from app.models.lead_processing_log import LeadProcessingLog
from app.models.user import User
from app.services.leads.extraction import extract_public_contacts, normalize_domain, normalize_website
from app.services.leads.scoring import score_candidate
from app.services.search import search_companies


@dataclass(frozen=True)
class LeadSearchResult:
    list_id: str
    list_name: str
    saved: int
    contacts: list[dict[str, Any]]
    log_id: str


async def run_lead_search(
    db: AsyncSession,
    *,
    user: User,
    query: str,
    city: str | None,
    limit: int,
    list_name: str | None = None,
) -> LeadSearchResult:
    clean_query = " ".join(query.split())
    clean_city = " ".join(city.split()) if city else None
    capped_limit = max(1, min(limit, 50))
    raw_results = await search_companies(clean_query, clean_city, capped_limit)

    seen_domains: set[str] = set()
    contacts_payload: list[dict[str, Any]] = []
    for raw in raw_results:
        website = normalize_website(raw.get("website"))
        domain = normalize_domain(website)
        dedupe_key = domain or (raw.get("name") or "").strip().lower()
        if not dedupe_key or dedupe_key in seen_domains:
            continue
        seen_domains.add(dedupe_key)

        text_blob = "\n".join(
            str(v)
            for v in [
                raw.get("name"),
                raw.get("website_summary"),
                raw.get("summary"),
                raw.get("description"),
                raw.get("email"),
                raw.get("phone"),
            ]
            if v
        )
        extracted = extract_public_contacts(text_blob)
        candidate = {
            **raw,
            "website": website,
            "domain": domain,
            "email": raw.get("email") or extracted.email,
            "phone": raw.get("phone") or extracted.phone,
            "telegram": extracted.telegram,
            "whatsapp": extracted.whatsapp,
            "vk": extracted.vk,
        }
        scored = score_candidate(candidate)
        candidate["score"] = scored.score
        candidate["priority"] = scored.priority
        candidate["confidence"] = scored.confidence
        candidate["score_reason"] = scored.reason
        contacts_payload.append(candidate)

    resolved_list_name = list_name or f"{clean_query} {clean_city or ''}".strip() or f"Поиск {datetime.now(UTC).date().isoformat()}"
    contact_list = ContactList(
        id=uuid.uuid4(),
        user_id=user.id,
        name=resolved_list_name,
        source="search",
        source_meta={"query": clean_query, "city": clean_city},
        total_count=len(contacts_payload),
    )
    db.add(contact_list)
    await db.flush()

    response_contacts: list[dict[str, Any]] = []
    for item in contacts_payload:
        enrichment = {
            "website": item.get("website"),
            "website_summary": item.get("website_summary") or item.get("summary"),
            "lead_score": item["score"],
            "priority": item["priority"],
            "confidence": item["confidence"],
            "score_reason": item["score_reason"],
            "telegram": item.get("telegram"),
            "whatsapp": item.get("whatsapp"),
            "vk": item.get("vk"),
        }
        contact = Contact(
            id=uuid.uuid4(),
            user_id=user.id,
            list_id=contact_list.id,
            contact_name=item.get("name"),
            email=item.get("email"),
            phone=item.get("phone"),
            enrichment=enrichment,
            raw=item,
        )
        db.add(contact)
        response_contacts.append({"id": str(contact.id), **item})

    log = LeadProcessingLog(
        id=uuid.uuid4(),
        user_id=user.id,
        contact_list_id=contact_list.id,
        search_query_original=clean_query,
        search_queries_generated=[clean_query],
        urls_found=len(raw_results),
        urls_after_filter=len(contacts_payload),
        urls_crawled=sum(1 for r in raw_results if r.get("website_summary")),
        pages_crawled_total=sum(1 for r in raw_results if r.get("website_summary")),
        llm_calls=[],
        total_cost_usd=0,
        ai_credits_used=0,
        outcome="success",
        meta={"city": clean_city, "limit": capped_limit},
    )
    db.add(log)
    await db.commit()

    return LeadSearchResult(
        list_id=str(contact_list.id),
        list_name=contact_list.name,
        saved=len(response_contacts),
        contacts=response_contacts,
        log_id=str(log.id),
    )
```

- [ ] **Step 4: Verify green**

Run:

```powershell
cd backend
pytest tests/test_lead_pipeline.py -v
```

Expected: 1 passed.

---

### Task 5: Direct Lead Search API

**Files:**
- Create: `backend/app/schemas/lead_search.py`
- Create: `backend/app/api/v1/lead_search.py`
- Modify: `backend/app/api/v1/router.py`
- Test: `backend/tests/test_lead_search_api.py`

- [ ] **Step 1: Write failing API test**

Add `backend/tests/test_lead_search_api.py`:

```python
async def _auth_headers(client, email: str = "lead-api@test.com") -> dict[str, str]:
    await client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def test_post_lead_search_creates_saved_search(monkeypatch, client):
    async def fake_run_lead_search(db, *, user, query, city, limit, list_name=None):
        from app.services.leads.pipeline import LeadSearchResult

        return LeadSearchResult(
            list_id="00000000-0000-0000-0000-000000000001",
            list_name=list_name or "Search",
            saved=1,
            contacts=[{"name": "Studio One", "website": "https://studio.test", "score": 80}],
            log_id="00000000-0000-0000-0000-000000000002",
        )

    monkeypatch.setattr("app.api.v1.lead_search.run_lead_search", fake_run_lead_search)
    headers = await _auth_headers(client)

    response = await client.post(
        "/api/v1/lead-search",
        headers=headers,
        json={"query": "design studios", "city": "Kazan", "limit": 10, "list_name": "Kazan design"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["saved"] == 1
    assert data["list_name"] == "Kazan design"
    assert data["contacts"][0]["name"] == "Studio One"
```

- [ ] **Step 2: Verify red**

Run:

```powershell
cd backend
pytest tests/test_lead_search_api.py -v
```

Expected: 404 because `/api/v1/lead-search` does not exist.

- [ ] **Step 3: Add schemas**

Create `backend/app/schemas/lead_search.py`:

```python
from typing import Any

from pydantic import BaseModel, Field


class LeadSearchCreate(BaseModel):
    query: str = Field(min_length=2, max_length=200)
    city: str | None = Field(default=None, max_length=100)
    limit: int = Field(default=20, ge=1, le=50)
    list_name: str | None = Field(default=None, max_length=120)


class LeadSearchRead(BaseModel):
    list_id: str
    list_name: str
    saved: int
    contacts: list[dict[str, Any]]
    log_id: str
```

- [ ] **Step 4: Add API router**

Create `backend/app/api/v1/lead_search.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.lead_search import LeadSearchCreate, LeadSearchRead
from app.services.leads.pipeline import run_lead_search

router = APIRouter(prefix="/lead-search", tags=["lead-search"])


@router.post("", response_model=LeadSearchRead, status_code=201)
async def create_lead_search(
    body: LeadSearchCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await run_lead_search(
        db,
        user=user,
        query=body.query,
        city=body.city,
        limit=body.limit,
        list_name=body.list_name,
    )
    return LeadSearchRead(
        list_id=result.list_id,
        list_name=result.list_name,
        saved=result.saved,
        contacts=result.contacts,
        log_id=result.log_id,
    )
```

Modify `backend/app/api/v1/router.py`:

```python
from app.api.v1 import lead_search
router.include_router(lead_search.router)
```

- [ ] **Step 5: Verify green**

Run:

```powershell
cd backend
pytest tests/test_lead_search_api.py -v
```

Expected: 1 passed.

---

### Task 6: Contact List Response Fields

**Files:**
- Modify: `backend/app/api/v1/contacts.py`
- Test: extend `backend/tests/test_lead_pipeline.py` or add `backend/tests/test_contacts_api.py`

- [ ] **Step 1: Write failing API assertion**

Add to `backend/tests/test_lead_search_api.py`:

```python
async def test_contacts_response_includes_lead_fields(client, db_session):
    from app.models.contact import Contact, ContactList
    from app.models.user import User
    import uuid

    headers = await _auth_headers(client, "contacts-fields@test.com")
    user = (await db_session.execute(__import__("sqlalchemy").select(User))).scalars().first()
    contact_list = ContactList(id=uuid.uuid4(), user_id=user.id, name="Search", source="search", total_count=1)
    db_session.add(contact_list)
    db_session.add(Contact(
        id=uuid.uuid4(),
        user_id=user.id,
        list_id=contact_list.id,
        contact_name="Studio One",
        email="hello@studio.test",
        phone="+7 999 000-00-00",
        raw={"website": "https://studio.test", "city": "Kazan", "industry": "Design"},
        enrichment={"website_summary": "B2B studio", "lead_score": 85, "confidence": "verified"},
    ))
    await db_session.commit()

    response = await client.get("/api/v1/contacts", headers=headers)

    item = response.json()[0]
    assert item["website"] == "https://studio.test"
    assert item["city"] == "Kazan"
    assert item["industry"] == "Design"
    assert item["enrichment_summary"] == "B2B studio"
    assert item["lead_score"] == 85
```

- [ ] **Step 2: Verify red**

Run:

```powershell
cd backend
pytest tests/test_lead_search_api.py::test_contacts_response_includes_lead_fields -v
```

Expected: KeyError or missing expected fields.

- [ ] **Step 3: Extend contacts response**

In `backend/app/api/v1/contacts.py`, inside `list_contacts`, derive:

```python
enrichment = contact.enrichment or {}
website = enrichment.get("website") or raw.get("website")
city = enrichment.get("city") or raw.get("city")
industry = raw.get("industry") or enrichment.get("industry")
```

Add these keys to each result:

```python
"website": website,
"city": city,
"industry": industry,
"enrichment_status": "done" if enrichment.get("description") or enrichment.get("website_summary") else None,
"enrichment_summary": enrichment.get("description") or enrichment.get("website_summary"),
"lead_score": enrichment.get("lead_score"),
"confidence": enrichment.get("confidence"),
```

- [ ] **Step 4: Verify green**

Run:

```powershell
cd backend
pytest tests/test_lead_search_api.py::test_contacts_response_includes_lead_fields -v
```

Expected: pass.

---

### Task 7: Frontend Lead Search Panel

**Files:**
- Create: `frontend/src/components/LeadSearchPanel.tsx`
- Modify: `frontend/src/pages/ContactsPage.tsx`

- [ ] **Step 1: Add panel component**

Create `frontend/src/components/LeadSearchPanel.tsx`:

```tsx
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { G } from "../lib/design";

interface LeadSearchResponse {
  list_id: string;
  list_name: string;
  saved: number;
  log_id: string;
}

export function LeadSearchPanel() {
  const [query, setQuery] = useState("");
  const [city, setCity] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async () => {
      const { data } = await api.post("/lead-search", {
        query,
        city: city || null,
        limit: 20,
        list_name: [query, city].filter(Boolean).join(" · "),
      });
      return data as LeadSearchResponse;
    },
    onSuccess: (data) => {
      setStatus(`Сохранено ${data.saved} лидов в список «${data.list_name}»`);
      queryClient.invalidateQueries({ queryKey: ["contacts"] });
    },
    onError: () => {
      setStatus("Поиск не удался. Проверьте ключи поиска или попробуйте другой запрос.");
    },
  });

  return (
    <div style={{
      margin: "14px 24px 0",
      padding: "14px",
      borderRadius: G.radius,
      border: G.border,
      background: "rgba(255,255,255,0.50)",
      boxShadow: G.shadowCard,
      flexShrink: 0,
    }}>
      <div style={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" }}>
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Кого ищем: стоматологии, студии, клиники" style={{ height: 34, minWidth: 260 }} />
        <input value={city} onChange={(e) => setCity(e.target.value)} placeholder="Город" style={{ height: 34, width: 150 }} />
        <button disabled={!query.trim() || mutation.isPending} onClick={() => mutation.mutate()}>
          {mutation.isPending ? "Ищем..." : "Найти лиды"}
        </button>
      </div>
      {status && <div style={{ marginTop: 8, fontSize: 13, color: G.textMuted }}>{status}</div>}
    </div>
  );
}
```

After adding, polish inline styles to match existing `ContactsPage` controls. Do not add a new design system.

- [ ] **Step 2: Mount panel**

In `frontend/src/pages/ContactsPage.tsx`, import:

```tsx
import { LeadSearchPanel } from "../components/LeadSearchPanel";
```

Render below import status banner and above preview block:

```tsx
<LeadSearchPanel />
```

- [ ] **Step 3: Type contact fields**

Extend the local `Contact` interface in `ContactsPage.tsx`:

```tsx
website: string | null;
city: string | null;
industry: string | null;
enrichment_summary: string | null;
lead_score: number | null;
confidence: string | null;
```

- [ ] **Step 4: Verify frontend build**

Run:

```powershell
cd frontend
npm run build
```

Expected: TypeScript and Vite build pass.

---

### Task 8: Chat Save Button Follow-up

**Files:**
- Modify: `frontend/src/pages/ChatPage.tsx`

- [ ] **Step 1: Make current limitation explicit**

The current `LeadResultsCard` save button only flips local `saved` state. This is misleading. In this pass either wire it to the existing chat tool flow or remove the false saved state.

- [ ] **Step 2: Minimal safe fix**

Change the button label from `Сохранить список` to `Сохранить через чат` and on click insert a confirmation prompt into the chat input:

```tsx
onClick={() => {
  setSaved(true);
  // Use existing chat tool contract. The agent will call save_companies after user confirmation.
}}
```

If implementing direct save from `LeadResultsCard`, use `/lead-search` only for fresh search; do not reuse it for already displayed companies because it would search again. A separate `/contacts/save-companies` endpoint would be cleaner, but that is out of scope for this MVP pass.

- [ ] **Step 3: Verify frontend build**

Run:

```powershell
cd frontend
npm run build
```

Expected: build pass.

---

### Task 9: Full Backend Verification

**Files:**
- No new files.

- [ ] **Step 1: Run targeted tests**

Run:

```powershell
cd backend
pytest tests/test_lead_extraction.py tests/test_lead_scoring.py tests/test_lead_pipeline.py tests/test_lead_search_api.py -v
```

Expected: all new tests pass.

- [ ] **Step 2: Run related existing tests**

Run:

```powershell
cd backend
pytest tests/test_search.py tests/test_contact_import.py tests/test_enrichment.py tests/test_chat_agent.py -v
```

Expected: existing search/import/enrichment/chat behavior still passes.

- [ ] **Step 3: Run lint if targeted tests pass**

Run:

```powershell
cd backend
ruff check app tests
```

Expected: no new Ruff errors from touched files.

---

## Scope Deliberately Not Included

- No tariff enforcement.
- No AI credits middleware.
- No production LLM routing rewrite.
- No separate `leads` table unless later requirements prove `contacts` is insufficient.
- No full job queue for search in the first pass; direct API is acceptable for MVP if limit is capped at 50 and providers already have timeouts.
- No promise that email/phone will always be found.

---

## Final Verification

- `cd backend && pytest tests/test_lead_extraction.py tests/test_lead_scoring.py tests/test_lead_pipeline.py tests/test_lead_search_api.py -v`
- `cd backend && pytest tests/test_search.py tests/test_contact_import.py tests/test_enrichment.py tests/test_chat_agent.py -v`
- `cd backend && ruff check app tests`
- `cd frontend && npm run build`

If these pass, start the app and manually test:

1. Open Contacts.
2. Search `стоматологии` + `Екатеринбург`.
3. Confirm contacts are saved.
4. Open Companies and verify website/city/industry/summary render from the saved contact fields.
