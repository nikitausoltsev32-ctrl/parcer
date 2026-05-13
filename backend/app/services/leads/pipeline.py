"""13-step lead search pipeline per CLAUDE.md §5."""
from __future__ import annotations

import asyncio
import logging
import re
import uuid
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from inspect import signature
from typing import Any
from urllib.parse import unquote, urlsplit

logger = logging.getLogger(__name__)

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead, LeadList
from app.models.lead_processing_log import LeadProcessingLog
from app.models.user import User
from app.services.credits import AI_CREDIT_COSTS, InsufficientCreditsError, check_and_deduct
from app.services.leads.cache import domain_content_hash, get_cached_lead
from app.services.leads.crawler import crawl_website
from app.services.leads.deep_ai import run_deep_ai
from app.services.leads.dedup import deduplicate_candidates
from app.services.leads.extraction import extract_public_contacts, normalize_domain, normalize_website
from app.services.leads.html_extraction import extract_from_html
from app.services.leads.light_ai import run_light_ai
from app.services.leads.outreach import generate_outreach
from app.services.leads.policy import deep_ai_allowed_for_plan, effective_search_limit
from app.services.leads.query_gen import generate_queries
from app.services.leads.scoring import score_candidate
from app.services.leads.url_classifier import classify_url
from app.services.leads.url_filter import filter_urls, is_blocked_domain, is_blocked_path
from app.services.llm.logged import LoggedLLMCall
from app.services.search import search_companies

ANTI_LOSS_RULES = {
    "deep_ai_requires_light_ai_pass": True,
    "light_ai_min_score_for_deep": 60,
    "deduplicate_by_domain": True,
    "skip_if_not_commercial": True,
    "outreach_requires_deep_ai": True,
    "outreach_min_score": 50,
    "check_credits_before_any_llm_call": True,
    "check_cache_before_crawl": True,
    "enforce_max_pages_per_site": True,
    "max_retry_attempts": 3,
}

URL_CLASSIFIER_KEEP_LABELS = {"company_homepage", "contacts", "services"}
_CONTACT_PATHS = {"contact", "contacts", "kontakty", "kontakt", "svyaz", "feedback"}
_SERVICE_PATHS = {"service", "services", "uslugi", "products", "product", "price", "prices", "portfolio"}
_ABOUT_PATHS = {"about", "o-kompanii", "o-nas", "company"}
_BORDER_TEXT_HINTS = (
    "top",
    "rating",
    "review",
    "catalog",
    "directory",
    "article",
    "blog",
    "топ",
    "рейтинг",
    "обзор",
    "каталог",
    "список",
    "статья",
)
_SERP_LISTICLE_HINTS = (
    "top",
    "best",
    "rating",
    "ranked",
    "directory",
    "catalog",
    "list of",
    "топ",
    "рейтинг",
    "лучшие",
    "список",
    "каталог",
    "подборка",
)
_SERP_LISTICLE_SUBJECTS = (
    "companies",
    "clinics",
    "firms",
    "providers",
    "services",
    "agencies",
    "studios",
    "компани",
    "клиник",
    "фирм",
    "агентств",
    "студий",
    "салон",
    "стоматолог",
    "услуг",
)
_VALID_EMAIL_RE = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.IGNORECASE)
FAST_TARGET_LIMIT = 5
FAST_CANDIDATE_MIN = 12

_PROGRESS_DEFAULT_LABELS = {
    "queued": "Поиск поставлен в очередь",
    "query": "Генерирую поисковые запросы",
    "search": "Ищу сайты компаний",
    "filter": "Отсекаю статьи, каталоги и мусорные ссылки",
    "crawl": "Читаю сайты компаний",
    "ai": "AI обрабатывает описания и зацепки",
    "save": "Сохраняю найденные лиды",
    "done": "Поиск завершен",
    "partial": "Поиск завершен частично",
    "failed": "Поиск завершился с ошибкой",
}


def _url_path_segments(url: str) -> list[str]:
    parsed = urlsplit(url if "://" in url else f"https://{url}")
    path = unquote(parsed.path or "").lower()
    return [segment for segment in path.split("/") if segment]


def _deterministic_url_label(url: str) -> str:
    segments = _url_path_segments(url)
    if not segments:
        return "company_homepage"

    first = segments[0]
    if first in _CONTACT_PATHS:
        return "contacts"
    if first in _SERVICE_PATHS:
        return "services"
    if first in _ABOUT_PATHS and len(segments) == 1:
        return "company_homepage"
    return "unknown"


def _needs_url_classification(raw: dict) -> bool:
    url = raw.get("website") or ""
    if not url or is_blocked_domain(url) or is_blocked_path(url):
        return False

    label = _deterministic_url_label(url)
    if label in URL_CLASSIFIER_KEEP_LABELS:
        return False

    segments = _url_path_segments(url)
    text = " ".join(
        str(part).lower()
        for part in [raw.get("name"), raw.get("website_summary"), raw.get("description")]
        if part
    )
    return len(segments) >= 2 or label == "unknown" or any(hint in text for hint in _BORDER_TEXT_HINTS)


def _serp_text(raw: dict) -> str:
    return " ".join(
        str(part).lower()
        for part in [
            raw.get("name"),
            raw.get("title"),
            raw.get("website_summary"),
            raw.get("description"),
            raw.get("snippet"),
        ]
        if part
    )


def _is_serp_listicle(raw: dict) -> bool:
    text = _serp_text(raw)
    if not text:
        return False
    has_listicle_hint = any(hint in text for hint in _SERP_LISTICLE_HINTS)
    has_subject = any(subject in text for subject in _SERP_LISTICLE_SUBJECTS)
    return has_listicle_hint and has_subject


def _clean_description(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def _headings_description(extracted: dict) -> str | None:
    h1 = _clean_description(extracted.get("h1"))
    h2s = [_clean_description(value) for value in extracted.get("h2s", []) if _clean_description(value)]
    parts = [part for part in [h1, *h2s[:2]] if part]
    if not parts:
        return None
    return ". ".join(parts)


def _lead_description(
    deep_data: dict,
    extracted: dict,
    raw: dict,
    light_description: str | None = None,
) -> str | None:
    for candidate in (
        deep_data.get("description"),
        light_description,
        extracted.get("meta_description"),
        extracted.get("og_description"),
        extracted.get("schema_org_description"),
        extracted.get("about_text"),
        _headings_description(extracted),
        extracted.get("business_summary"),
        raw.get("website_summary"),
        raw.get("industry"),
    ):
        cleaned = _clean_description(candidate)
        if cleaned:
            return cleaned
    return None


def _valid_email(value: Any) -> str | None:
    cleaned = _clean_description(value)
    if cleaned and _VALID_EMAIL_RE.fullmatch(cleaned):
        return cleaned
    return None


def _valid_phone(value: Any) -> str | None:
    cleaned = _clean_description(value)
    if not cleaned:
        return None
    digits = re.sub(r"\D", "", cleaned)
    if len(digits) == 11 and digits[0] in {"7", "8"}:
        return cleaned
    return None


def _validated_contacts(contacts: dict[str, Any]) -> dict[str, Any]:
    validated = dict(contacts)
    validated["email"] = _valid_email(validated.get("email"))
    validated["phone"] = _valid_phone(validated.get("phone"))
    return validated


def _is_transient_connection_error(exc: Exception) -> bool:
    text = f"{type(exc).__name__} {exc!r}".lower()
    return (
        "connectiondoesnotexisterror" in text
        or "connection was closed" in text
        or "server closed the connection" in text
        or "connection is closed" in text
    )


async def _commit_with_retry(
    db: AsyncSession,
    *,
    context: str,
    reapply: Callable[[], Awaitable[None]] | None = None,
) -> None:
    try:
        await db.commit()
        return
    except Exception as exc:
        if not _is_transient_connection_error(exc):
            raise
        logger.warning("[pipeline] transient DB connection error during %s; retrying once: %r", context, exc)
        with suppress(Exception):
            await db.rollback()

    if reapply is not None:
        await reapply()
    try:
        await db.commit()
    except IntegrityError as exc:
        logger.warning("[pipeline] retry hit integrity error during %s; treating as already persisted: %r", context, exc)
        with suppress(Exception):
            await db.rollback()


async def _release_read_transaction(db: AsyncSession) -> None:
    if db.in_transaction():
        with suppress(Exception):
            await db.rollback()


def _with_progress_meta(
    meta: dict[str, Any] | None,
    *,
    stage: str,
    label: str | None = None,
    percent: int | None = None,
    found: int | None = None,
    filtered: int | None = None,
    crawled: int | None = None,
    pages_crawled: int | None = None,
    saved: int | None = None,
    target: int | None = None,
    current_domain: str | None = None,
    llm_calls: int | None = None,
    event: bool = True,
) -> dict[str, Any]:
    merged = dict(meta or {})
    progress = dict(merged.get("progress") or {})
    progress.update(
        {
            "stage": stage,
            "label": label or _PROGRESS_DEFAULT_LABELS.get(stage, stage),
            "percent": max(0, min(100, int(percent if percent is not None else progress.get("percent", 0)))),
            "found": found if found is not None else progress.get("found", 0),
            "filtered": filtered if filtered is not None else progress.get("filtered", 0),
            "crawled": crawled if crawled is not None else progress.get("crawled", 0),
            "saved": saved if saved is not None else progress.get("saved", 0),
            "target": target if target is not None else progress.get("target", 0),
            "pages_crawled": pages_crawled if pages_crawled is not None else progress.get("pages_crawled", 0),
            "llm_calls": llm_calls if llm_calls is not None else progress.get("llm_calls", 0),
            "current_domain": current_domain,
        }
    )
    merged["progress"] = progress
    if saved is not None:
        merged["saved_leads"] = saved
    if event:
        events = list(merged.get("events") or [])
        events.append(
            {
                "ts": datetime.now(UTC).isoformat(),
                "stage": stage,
                "message": progress["label"],
                "domain": current_domain,
            }
        )
        merged["events"] = events[-20:]
    return merged


async def _update_progress(
    db: AsyncSession,
    pre_log_id: uuid.UUID | None,
    *,
    stage: str,
    label: str | None = None,
    percent: int | None = None,
    lead_list_id: uuid.UUID | str | None = None,
    list_name: str | None = None,
    city: str | None = None,
    limit: int | None = None,
    found: int | None = None,
    filtered: int | None = None,
    crawled: int | None = None,
    pages_crawled: int | None = None,
    saved: int | None = None,
    target: int | None = None,
    current_domain: str | None = None,
    llm_calls: int | None = None,
    event: bool = True,
) -> None:
    if pre_log_id is None:
        return

    async def apply() -> None:
        log_row = await db.get(LeadProcessingLog, pre_log_id)
        if log_row is None:
            return
        meta = dict(log_row.meta or {})
        if lead_list_id is not None:
            meta["lead_list_id"] = str(lead_list_id)
        if list_name is not None:
            meta["list_name"] = list_name
        if city is not None:
            meta["city"] = city
        if limit is not None:
            meta["limit"] = limit
        log_row.meta = _with_progress_meta(
            meta,
            stage=stage,
            label=label,
            percent=percent,
            found=found,
            filtered=filtered,
            crawled=crawled,
            pages_crawled=pages_crawled,
            saved=saved,
            target=target,
            current_domain=current_domain,
            llm_calls=llm_calls,
            event=event,
        )
        if found is not None:
            log_row.urls_found = found
        if filtered is not None:
            log_row.urls_after_filter = filtered
        if crawled is not None:
            log_row.urls_crawled = crawled
        if pages_crawled is not None:
            log_row.pages_crawled_total = pages_crawled

    await apply()
    await _commit_with_retry(db, context=f"progress {stage}", reapply=apply)


async def _call_search_companies(
    query: str, city: str | None, limit: int, *, fast_mode: bool, niche: str | None = None
) -> list[dict]:
    params = signature(search_companies).parameters
    kw: dict = {}
    if "niche" in params:
        kw["niche"] = niche or query
    if fast_mode and "enrich" in params and "hunter" in params:
        return await search_companies(query, city, limit, enrich=False, hunter=False, **kw)
    return await search_companies(query, city, limit, **kw)


async def _call_crawl_website(website: str, plan: str, *, fast_mode: bool) -> list[dict]:
    if "fast_mode" in signature(crawl_website).parameters:
        return await crawl_website(website, plan, fast_mode=fast_mode)
    return await crawl_website(website, plan)


async def _call_generate_queries(
    query: str,
    city: str | None,
    service_offered: str,
    log: LoggedLLMCall,
    *,
    model_override: str | None,
) -> list[str]:
    if "model_override" in signature(generate_queries).parameters:
        return await generate_queries(query, city, service_offered, log, model_override=model_override)
    return await generate_queries(query, city, service_offered, log)


async def _call_classify_url(
    url: str,
    title: str,
    description: str,
    log: LoggedLLMCall,
    *,
    model_override: str | None,
) -> str:
    if "model_override" in signature(classify_url).parameters:
        return await classify_url(url, title, description, log, model_override=model_override)
    return await classify_url(url, title, description, log)


@dataclass(frozen=True)
class LeadSearchResult:
    list_id: str
    list_name: str
    saved: int
    leads: list[dict[str, Any]]
    log_id: str

    @property
    def contacts(self) -> list[dict[str, Any]]:
        return self.leads


async def run_lead_search(
    db: AsyncSession,
    *,
    user: User,
    query: str,
    city: str | None,
    limit: int,
    list_name: str | None = None,
    generate_outreach_messages: bool = False,
    pre_log_id: uuid.UUID | None = None,
    fast_mode: bool = False,
    ai_model: str | None = None,
) -> LeadSearchResult:
    import time
    _t0 = time.monotonic()

    log = LoggedLLMCall()
    user_id = user.id
    bp = dict(user.business_profile or {})
    service_offered = f"{bp.get('offer', '')} {bp.get('business', '')}".strip() or "услуги"
    plan = user.plan or "trial"
    clean_query = " ".join(query.split())
    clean_city = " ".join(city.split()) if city else None
    requested_limit = max(1, min(limit, 50))
    capped_limit = effective_search_limit(
        requested_limit=requested_limit,
        fast_mode=fast_mode,
        leads_quota=user.leads_quota,
    )
    candidate_limit = (
        min(
            50,
            max(capped_limit * (3 if fast_mode else 1), FAST_CANDIDATE_MIN if fast_mode else capped_limit),
        )
        if capped_limit > 0
        else 0
    )
    user_id_str = str(user_id)

    await _update_progress(
        db,
        pre_log_id,
        stage="query",
        percent=5,
        city=clean_city,
        limit=capped_limit,
        target=capped_limit,
        saved=0,
    )

    # STEP 1 — Query Generator
    # Create the lead list up front so zero-quota runs can still persist a traceable result.
    fallback_name = f"РџРѕРёСЃРє {datetime.now(UTC).date().isoformat()}"
    resolved_list_name = list_name or f"{clean_query} {clean_city or ''}".strip() or fallback_name
    lead_list_id = uuid.uuid4()
    lead_list = LeadList(
        id=lead_list_id,
        user_id=user_id,
        name=resolved_list_name,
        source="search",
        source_meta={
            "query": clean_query,
            "city": clean_city,
            "queries_generated": [],
            "ai_model": ai_model,
        },
        total_count=0,
    )
    db.add(lead_list)
    await db.flush()

    if capped_limit <= 0:
        duration_ms = int((time.monotonic() - _t0) * 1000)
        quota_label = "Поиск не запущен: квота лидов исчерпана"
        await _update_progress(
            db,
            pre_log_id,
            stage="partial",
            percent=100,
            lead_list_id=lead_list_id,
            list_name=resolved_list_name,
            city=clean_city,
            limit=0,
            target=0,
            saved=0,
            label=quota_label,
        )
        proc_log = await db.get(LeadProcessingLog, pre_log_id) if pre_log_id is not None else None
        existing_meta = dict(proc_log.meta or {}) if proc_log is not None else {}
        log_meta = {
            **existing_meta,
            "city": clean_city,
            "limit": 0,
            "requested_limit": requested_limit,
            "candidate_limit": 0,
            "fast_mode": fast_mode,
            "plan": plan,
            "deep_ai_allowed": deep_ai_allowed_for_plan(plan),
            "lead_list_id": str(lead_list_id),
            "list_name": resolved_list_name,
            "saved_leads": 0,
            "serp_prescreened_out": 0,
            "quota_blocked": True,
        }
        log_meta = _with_progress_meta(
            log_meta,
            stage="partial",
            label=quota_label,
            percent=100,
            found=0,
            filtered=0,
            crawled=0,
            pages_crawled=0,
            saved=0,
            target=0,
            current_domain=None,
            llm_calls=0,
            event=False,
        )
        if proc_log is None:
            proc_log = LeadProcessingLog(id=pre_log_id or uuid.uuid4(), user_id=user_id)
            db.add(proc_log)
        proc_log.contact_list_id = None
        proc_log.search_query_original = clean_query
        proc_log.search_queries_generated = []
        proc_log.urls_found = 0
        proc_log.urls_after_filter = 0
        proc_log.urls_crawled = 0
        proc_log.pages_crawled_total = 0
        proc_log.llm_calls = []
        proc_log.total_cost_usd = 0
        proc_log.ai_credits_used = 0
        proc_log.outcome = "partial"
        proc_log.duration_ms = duration_ms
        proc_log.meta = log_meta

        async def _reapply_quota_blocked() -> None:
            db.add(lead_list)
            lead_list.total_count = 0
            db.add(proc_log)

        await _commit_with_retry(db, context="finalize quota blocked lead search", reapply=_reapply_quota_blocked)
        return LeadSearchResult(
            list_id=str(lead_list_id),
            list_name=resolved_list_name,
            saved=0,
            leads=[],
            log_id=str(proc_log.id),
        )

    try:
        queries = await _call_generate_queries(
            clean_query,
            clean_city,
            service_offered,
            log,
            model_override=ai_model,
        )
    except Exception:
        queries = [f"{clean_query} {clean_city or ''}".strip()]
    queries_generated = queries

    # STEP 2 — Search (run top 3 queries, merge)
    max_queries = 2 if fast_mode else 3
    await _update_progress(
        db,
        pre_log_id,
        stage="search",
        percent=15,
        label="Ищу сайты компаний в поиске и картах",
        target=capped_limit,
        saved=0,
    )
    search_tasks = [
        _call_search_companies(q, clean_city, candidate_limit, fast_mode=fast_mode, niche=clean_query)
        for q in queries[:max_queries]
    ]
    raw_batches = await asyncio.gather(*search_tasks, return_exceptions=True)
    raw_merged: list[dict] = []
    seen_merge: set[str] = set()
    urls_found = 0
    for batch in raw_batches:
        if isinstance(batch, list):
            urls_found += len(batch)
            for item in batch:
                if item.get("website"):
                    item["website"] = normalize_website(item.get("website"))
                key = normalize_domain(item.get("website")) or (item.get("name") or "").lower()
                if key and key not in seen_merge:
                    seen_merge.add(key)
                    raw_merged.append(item)

    await _update_progress(
        db,
        pre_log_id,
        stage="filter",
        percent=28,
        label=f"Нашла {urls_found} ссылок, отсекаю статьи и каталоги",
        found=urls_found,
        target=capped_limit,
        saved=0,
    )

    # STEP 3 — URL Filter (deterministic)
    websites = [r.get("website", "") for r in raw_merged if r.get("website")]
    kept_websites = set(filter_urls(websites))
    filtered = [r for r in raw_merged if not r.get("website") or r.get("website") in kept_websites]
    classified: list[dict] = []
    serp_prescreened_out = 0
    for raw in filtered:
        website = raw.get("website")
        if not website:
            raw["url_label"] = "no_website"
            classified.append(raw)
            continue

        if is_blocked_domain(website) or is_blocked_path(website):
            continue
        if _is_serp_listicle(raw):
            raw["url_label"] = "serp_prescreen_reject"
            serp_prescreened_out += 1
            continue

        label = _deterministic_url_label(website)
        if _needs_url_classification(raw):
            try:
                label = await _call_classify_url(
                    website,
                    raw.get("name") or "",
                    raw.get("website_summary") or raw.get("description") or "",
                    log,
                    model_override=ai_model,
                )
            except Exception:
                label = "unclassified"

        raw["url_label"] = label
        if label == "garbage":
            continue
        if label in URL_CLASSIFIER_KEEP_LABELS:
            classified.append(raw)

    filtered = classified[:candidate_limit]
    urls_after_filter = len(filtered)
    await _update_progress(
        db,
        pre_log_id,
        stage="filter",
        percent=36,
        label=f"После фильтра осталось {urls_after_filter} сайтов компаний",
        found=urls_found,
        filtered=urls_after_filter,
        target=capped_limit,
        saved=0,
        llm_calls=len(log.entries),
    )

    # Deduplicate by domain
    seen_domains: set[str] = set()
    deduped: list[dict] = []
    for raw in filtered:
        website = normalize_website(raw.get("website"))
        domain = normalize_domain(website) if website else None
        key = domain or (raw.get("name") or "").strip().lower()
        if not key or key in seen_domains:
            continue
        seen_domains.add(key)
        raw["website"] = website
        raw["domain"] = domain
        deduped.append(raw)
    deduped = deduplicate_candidates(deduped)

    # Create list
    fallback_name = f"Поиск {datetime.now(UTC).date().isoformat()}"
    resolved_list_name = list_name or f"{clean_query} {clean_city or ''}".strip() or fallback_name
    lead_list.source_meta = {
        "query": clean_query,
        "city": clean_city,
        "queries_generated": queries_generated,
        "ai_model": ai_model,
    }

    # Persist list and register its id in the log immediately so polling
    # can return partial leads while the pipeline is still running.
    async def _readd_lead_list() -> None:
        db.add(lead_list)

    await _commit_with_retry(db, context="create lead list", reapply=_readd_lead_list)
    await _update_progress(
        db,
        pre_log_id,
        stage="crawl",
        percent=40,
        label="Начинаю читать сайты компаний",
        lead_list_id=lead_list_id,
        list_name=resolved_list_name,
        city=clean_city,
        limit=capped_limit,
        found=urls_found,
        filtered=urls_after_filter,
        target=capped_limit,
        saved=0,
        llm_calls=len(log.entries),
    )

    # STEPS 5–12: per-candidate processing
    urls_crawled = 0
    pages_crawled_total = 0
    saved_leads: list[dict] = []

    for raw in deduped:
        if len(saved_leads) >= capped_limit:
            break

        website = raw.get("website")
        domain = raw.get("domain")
        display_domain = domain or raw.get("name") or website

        await _update_progress(
            db,
            pre_log_id,
            stage="crawl",
            percent=min(85, 40 + int((len(saved_leads) / max(capped_limit, 1)) * 40)),
            label=f"Читаю сайт компании: {display_domain}",
            found=urls_found,
            filtered=urls_after_filter,
            crawled=urls_crawled,
            pages_crawled=pages_crawled_total,
            saved=len(saved_leads),
            target=capped_limit,
            current_domain=display_domain,
            llm_calls=len(log.entries),
        )

        # STEP 5 — Cache Check
        cached = None
        if domain and ANTI_LOSS_RULES["check_cache_before_crawl"]:
            cached = await get_cached_lead(db, user_id, domain)

        if cached:
            saved_leads.append(_lead_to_dict(cached))
            await _release_read_transaction(db)
            await _update_progress(
                db,
                pre_log_id,
                stage="save",
                percent=min(95, 45 + int((len(saved_leads) / max(capped_limit, 1)) * 45)),
                label=f"Взяла готовый лид из кэша: {display_domain}",
                found=urls_found,
                filtered=urls_after_filter,
                crawled=urls_crawled,
                pages_crawled=pages_crawled_total,
                saved=len(saved_leads),
                target=capped_limit,
                current_domain=display_domain,
                llm_calls=len(log.entries),
            )
            continue
        await _release_read_transaction(db)

        # STEP 6 — Crawler
        pages: list[dict] = []
        if website:
            try:
                pages = await asyncio.wait_for(
                    _call_crawl_website(website, plan, fast_mode=fast_mode),
                    timeout=30.0,
                )
                urls_crawled += 1
                pages_crawled_total += len(pages)
            except TimeoutError:
                logger.warning("[pipeline] crawl timeout for %s — skipping", domain)
            except Exception:
                pass
        await _update_progress(
            db,
            pre_log_id,
            stage="crawl",
            percent=min(88, 42 + int((urls_crawled / max(len(deduped), 1)) * 28)),
            label=f"Сайт прочитан: {display_domain}",
            found=urls_found,
            filtered=urls_after_filter,
            crawled=urls_crawled,
            pages_crawled=pages_crawled_total,
            saved=len(saved_leads),
            target=capped_limit,
            current_domain=display_domain,
            llm_calls=len(log.entries),
            event=bool(pages),
        )

        # STEP 7 — Basic HTML Extraction
        extracted: dict = {}
        if pages:
            combined_html = "\n".join(p.get("html", "") for p in pages[:3])
            extracted = extract_from_html(combined_html, website or "")

        # Base contacts (prefer raw search data over extraction)
        contacts = {
            "email": raw.get("email") or extracted.get("email"),
            "phone": raw.get("phone") or extracted.get("phone"),
            "telegram": extracted.get("social_links", {}).get("telegram") or raw.get("telegram"),
            "whatsapp": extracted.get("social_links", {}).get("whatsapp") or raw.get("whatsapp"),
            "vk": extracted.get("social_links", {}).get("vk") or raw.get("vk"),
            "instagram": extracted.get("social_links", {}).get("instagram"),
        }
        snippet_contacts = extract_public_contacts(raw.get("website_summary"))
        contacts["email"] = contacts["email"] or snippet_contacts.email
        contacts["phone"] = contacts["phone"] or snippet_contacts.phone
        contacts["telegram"] = contacts["telegram"] or snippet_contacts.telegram
        contacts["whatsapp"] = contacts["whatsapp"] or snippet_contacts.whatsapp
        contacts["vk"] = contacts["vk"] or snippet_contacts.vk
        contacts = _validated_contacts(contacts)

        ai_level = "basic"
        light_result = None
        deep_data: dict = {}
        outreach_data: dict = {}

        # STEP 8 — Light AI (1 credit)
        # Run on any available signal: crawled pages, HTML extraction, or raw SerpAPI data.
        has_any_content = bool(
            pages or extracted
            or raw.get("website_summary")
            or raw.get("name")
        )
        logger.info("[pipeline] %s — pages=%d extracted=%s has_content=%s", domain, len(pages), bool(extracted), has_any_content)
        if has_any_content:
            await _update_progress(
                db,
                pre_log_id,
                stage="ai",
                percent=min(92, 55 + int((len(saved_leads) / max(capped_limit, 1)) * 35)),
                label=f"AI анализирует сайт: {display_domain}",
                found=urls_found,
                filtered=urls_after_filter,
                crawled=urls_crawled,
                pages_crawled=pages_crawled_total,
                saved=len(saved_leads),
                target=capped_limit,
                current_domain=display_domain,
                llm_calls=len(log.entries),
            )
            if ANTI_LOSS_RULES["check_credits_before_any_llm_call"]:
                try:
                    await check_and_deduct(db, user_id_str, "light_ai_analysis")
                    await db.commit()
                except InsufficientCreditsError:
                    logger.warning("[pipeline] INSUFFICIENT CREDITS for light_ai on %s — скipping AI", domain)
                    with suppress(Exception):
                        await db.rollback()
                except Exception as exc:
                    logger.warning("[pipeline] credit deduction failed for light_ai on %s: %r", domain, exc)
                    with suppress(Exception):
                        await db.rollback()
                else:
                    try:
                        logger.info("[pipeline] Light AI START for %s", domain)
                        meta_description = (
                            extracted.get("meta_description")
                            or extracted.get("og_description")
                            or extracted.get("schema_org_description")
                            or raw.get("website_summary")
                            or raw.get("description")
                            or raw.get("industry")
                            or ""
                        )
                        visible_text = (
                            extracted.get("visible_text_snippet")
                            or extracted.get("about_text")
                            or raw.get("website_summary")
                            or raw.get("description")
                            or raw.get("name")
                            or ""
                        )
                        light_result = await asyncio.wait_for(
                            run_light_ai(
                                title=extracted.get("title", "") or raw.get("name", ""),
                                meta_description=meta_description,
                                h1=extracted.get("h1", "") or "",
                                about_text=extracted.get("about_text", "") or "",
                                visible_text_snippet=visible_text,
                                email=contacts["email"],
                                phone=contacts["phone"],
                                icp_description=service_offered,
                                city=clean_city,
                                log=log,
                                model_override=ai_model,
                            ),
                            timeout=45.0,
                        )
                        ai_level = "light"
                        logger.info(
                            "[pipeline] Light AI DONE for %s: score=%d pass_deep=%s hook=%r",
                            domain, light_result.relevance_score, light_result.pass_to_deep_ai, light_result.hook
                        )
                    except TimeoutError:
                        logger.warning("[pipeline] Light AI timeout for %s — skipping", domain)
                        light_result = None
                    except Exception as exc:
                        logger.exception("[pipeline] Light AI ERROR for %s: %s", domain, exc)
                        light_result = None

        # STEP 9 — Deep AI (5 credits): requires actual crawled pages to analyse
        if (
            light_result
            and light_result.pass_to_deep_ai
            and pages
            and deep_ai_allowed_for_plan(plan)
            and ANTI_LOSS_RULES["deep_ai_requires_light_ai_pass"]
        ):
            try:
                await check_and_deduct(db, user_id_str, "deep_ai_analysis")
                await db.commit()
            except InsufficientCreditsError:
                logger.warning("[pipeline] INSUFFICIENT CREDITS for deep_ai on %s", domain)
                with suppress(Exception):
                    await db.rollback()
            except Exception as exc:
                logger.warning("[pipeline] credit deduction failed for deep_ai on %s: %r", domain, exc)
                with suppress(Exception):
                    await db.rollback()
            else:
                try:
                    logger.info("[pipeline] Deep AI START for %s", domain)
                    deep_data = await asyncio.wait_for(
                        run_deep_ai(
                            pages=pages,
                            service_offered=service_offered,
                            extracted_email=contacts["email"],
                            extracted_phone=contacts["phone"],
                            extracted_telegram=contacts["telegram"],
                            log=log,
                        ),
                        timeout=60.0,
                    )
                    ai_level = "deep"
                    logger.info("[pipeline] Deep AI DONE for %s: lead_fit=%s", domain, deep_data.get("lead_fit"))
                    # Merge deep AI contacts (more authoritative)
                    for field in ("email", "phone", "telegram", "whatsapp", "vk", "instagram"):
                        if deep_data.get(field):
                            contacts[field] = deep_data[field]
                    contacts = _validated_contacts(contacts)
                except TimeoutError:
                    logger.warning("[pipeline] Deep AI timeout for %s — falling back to light AI result", domain)
                    deep_data = {}
                except Exception as exc:
                    logger.exception("[pipeline] Deep AI ERROR for %s: %s", domain, exc)
                    deep_data = {}

        # STEP 10 — Validation
        confidence = float(deep_data.get("confidence", 0.3 if ai_level == "basic" else 0.6))
        if confidence < 0.3 and ai_level == "basic":
            # Low-confidence basic result — still save but mark
            pass

        # STEP 11 — Lead Scoring
        light_description = light_result.description if light_result else None
        description = _lead_description(deep_data, extracted, raw, light_description)

        deep_fit = deep_data.get("lead_fit") if isinstance(deep_data.get("lead_fit"), dict) else {}
        deep_fit_score = deep_fit.get("score")
        deep_fit_reason = _clean_description(deep_fit.get("reason"))

        # Use deep AI's lead_fit when available; fall back to light AI relevance_score
        ai_score = (
            int(deep_fit_score)
            if isinstance(deep_fit_score, int | float) and deep_fit_score > 0
            else (light_result.relevance_score if light_result else None)
        )
        ai_reason = deep_fit_reason or _clean_description(deep_data.get("reason_to_contact"))

        score_input = {
            "name": deep_data.get("company_name") or raw.get("name"),
            "website": website,
            "email": contacts["email"],
            "phone": contacts["phone"],
            "website_summary": description,
            "ai_score": ai_score,
            "ai_reason": ai_reason,
            "maps_rating": raw.get("maps_rating"),
            "maps_reviews_count": raw.get("maps_reviews_count"),
            "serp_position": raw.get("serp_position"),
        }
        scored = score_candidate(score_input)
        logger.info(
            "[pipeline] SCORE for %s: ai_level=%s score=%d priority=%s ai_score_input=%s",
            domain, ai_level, scored.score, scored.priority, ai_score
        )
        lead_fit = {
            "score": scored.score,
            "reason": deep_fit_reason or scored.reason,
            "priority": deep_fit.get("priority") or scored.priority,
        }

        # STEP 12 — Outreach Generation (3 credits, only for deep AI + score >= 50)
        if (
            generate_outreach_messages
            and ai_level == "deep"
            and scored.score >= ANTI_LOSS_RULES["outreach_min_score"]
            and ANTI_LOSS_RULES["outreach_requires_deep_ai"]
        ):
            try:
                await check_and_deduct(db, user_id_str, "outreach_generation")
                await db.commit()
            except InsufficientCreditsError:
                with suppress(Exception):
                    await db.rollback()
                pass
            except Exception as exc:
                logger.warning("[pipeline] credit deduction failed for outreach on %s: %r", domain, exc)
                with suppress(Exception):
                    await db.rollback()
            else:
                try:
                    outreach_data = await generate_outreach(
                        service_offered=service_offered,
                        company_name=deep_data.get("company_name") or raw.get("name"),
                        industry=deep_data.get("industry") or (light_result.industry if light_result else None),
                        description=description,
                        pain_points=deep_data.get("pain_points") or [],
                        reason_to_contact=deep_data.get("reason_to_contact"),
                        log=log,
                    )
                except Exception:
                    outreach_data = {}

        # Build Lead record
        content_hash = domain_content_hash("\n".join(p.get("html", "") for p in pages)) if pages else None
        source_urls = [p["url"] for p in pages]
        if not source_urls and website:
            source_urls = [website]
        processing = {
            "ai_level": ai_level,
            "sources": source_urls,
            "source": raw.get("source"),
            "url_label": raw.get("url_label"),
            "confidence": confidence,
            "cache_hit": False,
            "cost_usd": log.total_cost_usd,
            "maps_rating": raw.get("maps_rating"),
            "maps_reviews_count": raw.get("maps_reviews_count"),
            "serp_position": raw.get("serp_position"),
        }
        lead = Lead(
            id=uuid.uuid4(),
            user_id=user_id,
            list_id=lead_list_id,
            domain=domain,
            website=website,
            company_name=deep_data.get("company_name") or raw.get("name"),
            city=deep_data.get("city") or (light_result.city if light_result else raw.get("city")),
            region=deep_data.get("region"),
            address=deep_data.get("address") or extracted.get("address") or raw.get("address"),
            industry=deep_data.get("industry") or (light_result.industry if light_result else raw.get("industry")),
            description=description,
            services=deep_data.get("services"),
            email=contacts["email"],
            phone=contacts["phone"],
            telegram=contacts["telegram"],
            whatsapp=contacts["whatsapp"],
            vk=contacts["vk"],
            instagram=contacts["instagram"],
            has_contact_form=deep_data.get("has_contact_form") or extracted.get("has_contact_form", False),
            decision_maker=deep_data.get("decision_maker"),
            website_quality=deep_data.get("website_quality"),
            lead_fit=lead_fit,
            pain_points=deep_data.get("pain_points") or [],
            reason_to_contact=deep_data.get("reason_to_contact") or (light_result.hook if light_result else None),
            personalized_outreach=outreach_data or None,
            processing=processing,
            content_hash=content_hash,
            last_scraped_at=datetime.now(UTC) if pages else None,
            cache_valid=True,
        )
        db.add(lead)

        async def _readd_lead() -> None:
            db.add(lead)

        # Commit each lead immediately so polling can return partial results.
        await _commit_with_retry(db, context=f"insert lead {domain or raw.get('name')}", reapply=_readd_lead)
        saved_leads.append(_lead_to_dict(lead))
        await _update_progress(
            db,
            pre_log_id,
            stage="save",
            percent=min(98, 50 + int((len(saved_leads) / max(capped_limit, 1)) * 45)),
            label=f"Сохранила лид: {lead.company_name or display_domain}",
            found=urls_found,
            filtered=urls_after_filter,
            crawled=urls_crawled,
            pages_crawled=pages_crawled_total,
            saved=len(saved_leads),
            target=capped_limit,
            current_domain=display_domain,
            llm_calls=len(log.entries),
        )

    lead_list.total_count = len(saved_leads)

    # STEP 13 — Observability Log
    duration_ms = int((time.monotonic() - _t0) * 1000)
    credit_stage_map = {
        "light_ai": "light_ai_analysis",
        "deep_ai": "deep_ai_analysis",
        "outreach": "outreach_generation",
    }
    outcome = "success" if len(saved_leads) >= capped_limit else "partial"
    final_label = (
        f"Готово: сохранено {len(saved_leads)} из {capped_limit} лидов"
        if outcome == "success"
        else f"Частично готово: сохранено {len(saved_leads)} из {capped_limit}, кандидаты закончились"
    )
    existing_meta: dict[str, Any] = {}
    proc_log = None
    if pre_log_id is not None:
        proc_log = await db.get(LeadProcessingLog, pre_log_id)
        existing_meta = dict(proc_log.meta or {}) if proc_log is not None else {}
    log_meta = {
        **existing_meta,
        "city": clean_city,
        "limit": capped_limit,
        "requested_limit": requested_limit,
        "candidate_limit": candidate_limit,
        "fast_mode": fast_mode,
        "plan": plan,
        "deep_ai_allowed": deep_ai_allowed_for_plan(plan),
        "lead_list_id": str(lead_list_id),
        "list_name": resolved_list_name,
        "saved_leads": len(saved_leads),
        "serp_prescreened_out": serp_prescreened_out,
    }
    log_meta = _with_progress_meta(
        log_meta,
        stage="done" if outcome == "success" else "partial",
        label=final_label,
        percent=100,
        found=urls_found,
        filtered=urls_after_filter,
        crawled=urls_crawled,
        pages_crawled=pages_crawled_total,
        saved=len(saved_leads),
        target=capped_limit,
        current_domain=None,
        llm_calls=len(log.entries),
    )
    if pre_log_id is None or proc_log is None:
        proc_log = LeadProcessingLog(id=pre_log_id or uuid.uuid4(), user_id=user_id)
        db.add(proc_log)
    proc_log.contact_list_id = None
    proc_log.search_query_original = clean_query
    proc_log.search_queries_generated = queries_generated
    proc_log.urls_found = urls_found
    proc_log.urls_after_filter = urls_after_filter
    proc_log.urls_crawled = urls_crawled
    proc_log.pages_crawled_total = pages_crawled_total
    proc_log.llm_calls = log.entries
    proc_log.total_cost_usd = log.total_cost_usd
    proc_log.ai_credits_used = sum(AI_CREDIT_COSTS.get(credit_stage_map.get(e["stage"], ""), 0) for e in log.entries)
    proc_log.outcome = outcome
    proc_log.duration_ms = duration_ms
    proc_log.meta = log_meta

    async def _reapply_final() -> None:
        db.add(lead_list)
        lead_list.total_count = len(saved_leads)
        db.add(proc_log)

    await _commit_with_retry(db, context="finalize lead search log", reapply=_reapply_final)

    return LeadSearchResult(
        list_id=str(lead_list_id),
        list_name=resolved_list_name,
        saved=len(saved_leads),
        leads=saved_leads,
        log_id=str(proc_log.id),
    )


def _lead_to_dict(lead: Lead) -> dict:
    lead_fit = lead.lead_fit if isinstance(lead.lead_fit, dict) else {}
    processing = lead.processing if isinstance(lead.processing, dict) else {}
    return {
        "id": str(lead.id),
        "domain": lead.domain,
        "website": lead.website,
        "name": lead.company_name,
        "company_name": lead.company_name,
        "city": lead.city,
        "address": lead.address,
        "industry": lead.industry,
        "description": lead.description,
        "email": lead.email,
        "phone": lead.phone,
        "telegram": lead.telegram,
        "whatsapp": lead.whatsapp,
        "vk": lead.vk,
        "instagram": lead.instagram,
        "has_contact_form": lead.has_contact_form,
        "source": processing.get("source"),
        "confidence": processing.get("confidence"),
        "ai_level": processing.get("ai_level"),
        "url_label": processing.get("url_label"),
        "score": lead_fit.get("score"),
        "lead_fit": lead.lead_fit,
        "reason_to_contact": lead.reason_to_contact,
        "pain_points": lead.pain_points or [],
        "website_quality": lead.website_quality,
        "processing": lead.processing,
        "personalized_outreach": lead.personalized_outreach,
        "maps_rating": processing.get("maps_rating"),
        "maps_reviews_count": processing.get("maps_reviews_count"),
        "serp_position": processing.get("serp_position"),
    }
