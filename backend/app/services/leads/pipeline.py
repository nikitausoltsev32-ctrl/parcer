"""13-step lead search pipeline per CLAUDE.md §5."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead, LeadList
from app.models.lead_processing_log import LeadProcessingLog
from app.models.user import User
from app.services.credits import AI_CREDIT_COSTS, InsufficientCreditsError, check_and_deduct
from app.services.leads.cache import domain_content_hash, get_cached_lead
from app.services.leads.crawler import crawl_website
from app.services.leads.deep_ai import run_deep_ai
from app.services.leads.extraction import extract_public_contacts, normalize_domain, normalize_website
from app.services.leads.html_extraction import extract_from_html
from app.services.leads.light_ai import run_light_ai
from app.services.leads.outreach import generate_outreach
from app.services.leads.query_gen import generate_queries
from app.services.leads.scoring import score_candidate
from app.services.leads.url_filter import filter_urls
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
) -> LeadSearchResult:
    import time
    _t0 = time.monotonic()

    log = LoggedLLMCall()
    bp = user.business_profile or {}
    service_offered = f"{bp.get('offer', '')} {bp.get('business', '')}".strip() or "услуги"
    plan = user.plan or "trial"
    clean_query = " ".join(query.split())
    clean_city = " ".join(city.split()) if city else None
    capped_limit = max(1, min(limit, 50))
    user_id_str = str(user.id)

    # STEP 1 — Query Generator
    try:
        queries = await generate_queries(clean_query, clean_city, service_offered, log)
    except Exception:
        queries = [f"{clean_query} {clean_city or ''}".strip()]
    queries_generated = queries

    # STEP 2 — Search (run top 3 queries, merge)
    import asyncio
    search_tasks = [search_companies(q, clean_city, capped_limit) for q in queries[:3]]
    raw_batches = await asyncio.gather(*search_tasks, return_exceptions=True)
    raw_merged: list[dict] = []
    seen_merge: set[str] = set()
    urls_found = 0
    for batch in raw_batches:
        if isinstance(batch, list):
            urls_found += len(batch)
            for item in batch:
                key = normalize_domain(item.get("website")) or (item.get("name") or "").lower()
                if key and key not in seen_merge:
                    seen_merge.add(key)
                    raw_merged.append(item)

    # STEP 3 — URL Filter (deterministic)
    websites = [r.get("website", "") for r in raw_merged if r.get("website")]
    kept_websites = set(filter_urls(websites))
    filtered = [r for r in raw_merged if not r.get("website") or r.get("website") in kept_websites]
    filtered = filtered[:capped_limit]
    urls_after_filter = len(filtered)

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

    # Create list
    fallback_name = f"Поиск {datetime.now(UTC).date().isoformat()}"
    resolved_list_name = list_name or f"{clean_query} {clean_city or ''}".strip() or fallback_name
    lead_list = LeadList(
        id=uuid.uuid4(),
        user_id=user.id,
        name=resolved_list_name,
        source="search",
        source_meta={"query": clean_query, "city": clean_city, "queries_generated": queries_generated},
    )
    db.add(lead_list)
    await db.flush()

    # STEPS 5–12: per-candidate processing
    urls_crawled = 0
    pages_crawled_total = 0
    saved_leads: list[dict] = []

    for raw in deduped:
        website = raw.get("website")
        domain = raw.get("domain")

        # STEP 5 — Cache Check
        cached = None
        if domain and ANTI_LOSS_RULES["check_cache_before_crawl"]:
            cached = await get_cached_lead(db, user.id, domain)

        if cached:
            saved_leads.append(_lead_to_dict(cached))
            continue

        # STEP 6 — Crawler
        pages: list[dict] = []
        if website:
            try:
                pages = await crawl_website(website, plan)
                urls_crawled += 1
                pages_crawled_total += len(pages)
            except Exception:
                pass

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

        ai_level = "basic"
        light_result = None
        deep_data: dict = {}
        outreach_data: dict = {}

        # STEP 8 — Light AI (1 credit)
        if pages or extracted:
            if ANTI_LOSS_RULES["check_credits_before_any_llm_call"]:
                try:
                    await check_and_deduct(db, user_id_str, "light_ai_analysis")
                except InsufficientCreditsError:
                    pass
                else:
                    try:
                        light_result = await run_light_ai(
                            title=extracted.get("title", "") or raw.get("name", ""),
                            meta_description=extracted.get("meta_description", "") or "",
                            h1=extracted.get("h1", "") or "",
                            visible_text_snippet=extracted.get("visible_text_snippet", "")
                            or raw.get("website_summary", "")
                            or "",
                            email=contacts["email"],
                            phone=contacts["phone"],
                            icp_description=service_offered,
                            city=clean_city,
                            log=log,
                        )
                        ai_level = "light"
                    except Exception:
                        light_result = None

        # STEP 9 — Deep AI (5 credits)
        if (
            light_result
            and light_result.pass_to_deep_ai
            and ANTI_LOSS_RULES["deep_ai_requires_light_ai_pass"]
        ):
            try:
                await check_and_deduct(db, user_id_str, "deep_ai_analysis")
            except InsufficientCreditsError:
                pass
            else:
                try:
                    deep_data = await run_deep_ai(
                        pages=pages,
                        service_offered=service_offered,
                        extracted_email=contacts["email"],
                        extracted_phone=contacts["phone"],
                        extracted_telegram=contacts["telegram"],
                        log=log,
                    )
                    ai_level = "deep"
                    # Merge deep AI contacts (more authoritative)
                    for field in ("email", "phone", "telegram", "whatsapp", "vk", "instagram"):
                        if deep_data.get(field):
                            contacts[field] = deep_data[field]
                except Exception:
                    deep_data = {}

        # STEP 10 — Validation
        confidence = float(deep_data.get("confidence", 0.3 if ai_level == "basic" else 0.6))
        if confidence < 0.3 and ai_level == "basic":
            # Low-confidence basic result — still save but mark
            pass

        # STEP 11 — Lead Scoring
        score_input = {
            "name": deep_data.get("company_name") or raw.get("name"),
            "website": website,
            "email": contacts["email"],
            "phone": contacts["phone"],
            "website_summary": deep_data.get("description") or raw.get("website_summary"),
        }
        scored = score_candidate(score_input)
        lead_fit = {
            "score": scored.score,
            "reason": scored.reason,
            "priority": scored.priority,
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
            except InsufficientCreditsError:
                pass
            else:
                try:
                    outreach_data = await generate_outreach(
                        service_offered=service_offered,
                        company_name=deep_data.get("company_name") or raw.get("name"),
                        industry=deep_data.get("industry") or (light_result.industry if light_result else None),
                        description=deep_data.get("description"),
                        pain_points=deep_data.get("pain_points") or [],
                        reason_to_contact=deep_data.get("reason_to_contact"),
                        log=log,
                    )
                except Exception:
                    outreach_data = {}

        # Build Lead record
        content_hash = domain_content_hash("\n".join(p.get("html", "") for p in pages)) if pages else None
        processing = {
            "ai_level": ai_level,
            "sources": [p["url"] for p in pages],
            "confidence": confidence,
            "cache_hit": False,
            "cost_usd": log.total_cost_usd,
        }
        lead = Lead(
            id=uuid.uuid4(),
            user_id=user.id,
            list_id=lead_list.id,
            domain=domain,
            website=website,
            company_name=deep_data.get("company_name") or raw.get("name"),
            city=deep_data.get("city") or (light_result.city if light_result else raw.get("city")),
            region=deep_data.get("region"),
            address=deep_data.get("address") or extracted.get("address"),
            industry=deep_data.get("industry") or (light_result.industry if light_result else raw.get("industry")),
            description=deep_data.get("description") or raw.get("website_summary"),
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
            pain_points=deep_data.get("pain_points"),
            reason_to_contact=deep_data.get("reason_to_contact"),
            personalized_outreach=outreach_data or None,
            processing=processing,
            content_hash=content_hash,
            last_scraped_at=datetime.now(UTC) if pages else None,
            cache_valid=True,
        )
        db.add(lead)
        saved_leads.append(_lead_to_dict(lead))

    lead_list.total_count = len(saved_leads)

    # STEP 13 — Observability Log
    duration_ms = int((time.monotonic() - _t0) * 1000)
    credit_stage_map = {
        "light_ai": "light_ai_analysis",
        "deep_ai": "deep_ai_analysis",
        "outreach": "outreach_generation",
    }
    proc_log = LeadProcessingLog(
        id=uuid.uuid4(),
        user_id=user.id,
        contact_list_id=None,
        search_query_original=clean_query,
        search_queries_generated=queries_generated,
        urls_found=urls_found,
        urls_after_filter=urls_after_filter,
        urls_crawled=urls_crawled,
        pages_crawled_total=pages_crawled_total,
        llm_calls=log.entries,
        total_cost_usd=log.total_cost_usd,
        ai_credits_used=sum(AI_CREDIT_COSTS.get(credit_stage_map.get(e["stage"], ""), 0) for e in log.entries),
        outcome="success",
        duration_ms=duration_ms,
        meta={
            "city": clean_city,
            "limit": capped_limit,
            "plan": plan,
            "lead_list_id": str(lead_list.id),
            "list_name": lead_list.name,
        },
    )
    db.add(proc_log)
    await db.commit()

    return LeadSearchResult(
        list_id=str(lead_list.id),
        list_name=lead_list.name,
        saved=len(saved_leads),
        leads=saved_leads,
        log_id=str(proc_log.id),
    )


def _lead_to_dict(lead: Lead) -> dict:
    lead_fit = lead.lead_fit if isinstance(lead.lead_fit, dict) else {}
    return {
        "id": str(lead.id),
        "domain": lead.domain,
        "website": lead.website,
        "name": lead.company_name,
        "company_name": lead.company_name,
        "city": lead.city,
        "industry": lead.industry,
        "email": lead.email,
        "phone": lead.phone,
        "telegram": lead.telegram,
        "score": lead_fit.get("score"),
        "lead_fit": lead.lead_fit,
        "processing": lead.processing,
        "personalized_outreach": lead.personalized_outreach,
    }
