# CLAUDE.md — единственный источник правды для AI-агентов

> Версия: 4.1 (июнь 2026). Читать **перед любым** изменением кода.
> Живой статус задач и навигация по коду — в **PLAN.md** (корень репо). Здесь — правила и канон.

---

## 1. Продукт

**Лида AI** — ИИ-агент для поиска, анализа и квалификации B2B-лидов (старое кодовое имя `parcer` — только в репо).
Находит компании по нише и гео (SerpAPI/Yandex → реальные сайты) → анализирует (crawler → HTML extraction → Light/Deep AI) → оценивает лид и готовит первое сообщение → ведёт CRM (статусы, follow-up, inbox).

**НЕ позиционировать как:** парсер, скрапер, база email, массовая рассылка. Не обходит защиты, не продаёт контакты, не спам.
**Аудитория:** ИП, B2B-фрилансеры, агентства без отдела продаж в РФ/СНГ.

---

## 2. Правила для агента (обязательны)

- Отвечать по-русски, если вопрос по-русски. Говорить правду, трезво оценивать риски, не скрывать неопределённость.
- **НЕ** предлагать: Google Search API, WhatsApp Business API, Kubernetes, Elasticsearch, Alembic, локальный Docker/Postgres/Redis, Авито как источник.
- **НЕ** использовать слова «парсер», «скрапер», «база email», «массовая холодная рассылка» в копии продукта.
- **Продакшен LLM — только РФ-хостинг.** Провайдер `yandex` (Yandex AI Studio) разрешён для платных РФ — включая open-weight модели галереи (DeepSeek, Qwen, gpt-oss): инференс в Yandex Cloud РФ, трансграничной передачи нет. Прямые иностранные API (Claude/GPT/Gemini через openrouter/nvidia/groq/anthropic) — только dev/MVP, НЕ для платных РФ (152-ФЗ + риск блокировки/ToS). GigaChat — целевой второй РФ-провайдер.
- **Discovery живого веба — только реальные поисковики** (SerpAPI + Yandex Search API). LLM НЕ источник списка компаний (галлюцинирует малый бизнес).
- **ФИО / decision_maker НЕ извлекаем и НЕ храним.** Только публичные контакты компании (email, телефон, соцсети, форма) + ссылка на источник.
- **Миграции — только через Supabase CLI** (`supabase/migrations/*.sql`). Никакого Alembic.
- Бизнес-логика — в `backend/app/services/`, роутеры тонкие.
- Все внешние вызовы (LLM, SMTP, IMAP, поиск) — с таймаутом и retry. Секреты — только через env.
- **Не хардкодить** доменную логику под один запрос (как было с «мраморной крошкой») — обобщать через LLM/конфиг. Не хардкодить тарифные лимиты — только config/константы.
- Не выдумывать email/телефон/имя — нет данных на сайте → `null`.
- При изменении: БД → новая миграция + §11(БД); API-эндпоинт → §12(API); промпт → §8(промпты). Статус задач → PLAN.md.

---

## 3. Dev-команды

**Backend** (`backend/`): `pip install -e ".[dev]"` · `uvicorn app.main:app --reload` · `python -m procrastinate --app app.workers.main.app worker` · `ruff check .` · `ruff format .` · `pytest tests/ -v`
**Frontend** (`frontend/`): `npm install` · `npm run dev` (Vite :5173) · `npm run build` · `npm run lint`
**БД** (Supabase CLI): `supabase migration new <name>` · `supabase db push` · `supabase db reset`
**Makefile:** `make dev` (API+Vite) · `dev-api` · `dev-worker` · `dev-web` · `test` · `lint` · `migrate-new name=...` · `migrate-push` · `migrate-reset` · `seed` · `types`
**Quickstart:** `cp .env.example .env` (заполнить SUPABASE_*, LLM keys, SECRET_KEY, FERNET_KEY, TRACKING_SECRET) → `supabase link --project-ref <ref>` → `supabase db push` → `make install` → `make dev`

---

## 4. Архитектура стека

**Cloud-first, без локального Docker:** Postgres + Storage — Supabase (облако); очереди — Procrastinate в Supabase Postgres; локально — uvicorn + Procrastinate worker + Vite.
**Backend:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 async, Procrastinate.
**Frontend:** React 18 + Vite + TypeScript + Tailwind + shadcn/ui + TanStack Query + SSE.

```
backend/app/
  api/v1/        # тонкие роутеры
  core/          # config, database, security, tokens, fernet, tracking
  services/
    auth_service.py
    llm/         # base, factory, routing, yandex, groq, qwen, glm, nvidia, claude, logged
    chat/        # agent.py, tools.py
    crm/         # companies, contacts, contact_import
    inbox/       # classifier
    letters/     # generator
    leads/       # pipeline.py ← главный flow; icp.py, icp_parser.py, query_gen.py,
                 #   icp_filter.py, crawler.py, extraction.py, html_extraction.py,
                 #   light_ai.py, deep_ai.py, scoring.py, funnel.py
    search/      # serp.py, yandex.py, firecrawl.py, hunter.py, __init__.py
  workers/       # Procrastinate tasks
  models/        # SQLAlchemy ORM
  schemas/       # Pydantic
frontend/src/    # pages/ features/ components/ui/ lib/(api.ts, sse.ts, auth.ts)
supabase/migrations/  # *.sql
docs/            # PROJECT.md (продукт), PROGRESS.md (может устареть)
```

---

## 5. Pipeline поиска лидов (canonical)

Канонический backend-flow реализован в `services/leads/pipeline.py`. Стадии и модели:

| # | Стадия | Модель / тип | Вход → Выход |
|---|--------|--------------|--------------|
| 0 | **Prompt parsing / ICP** (`icp_parser.py`) | РФ LLM lite | запрос+профиль продавца → ICP (intent buyers/niche, buyer_segments, positive/negative keywords, excluded). Обобщённо для ЛЮБОЙ ниши; fallback → детерминированный `build_icp_profile`. |
| 1 | Query Generator (`query_gen.py`) | РФ LLM lite | ICP → 5–15 поисковых запросов + negative keywords |
| 2 | Search (`search/`) | SerpAPI + Yandex Search API | реальные поисковики; LLM-discovery (Sonar) за флагом, default OFF. Cache 7д (sha256(query+region)). reflection-петля при малом числе кандидатов |
| 3 | URL Filter (детерм.) | без LLM | блок-домены (avito/hh/vc/2gis/zoon/prodoctorov/yell/flamp…), паттерны (`/blog/ /news/ /tag/ /vakansii/ /privacy/ ?utm_ /page/\d+ .pdf`), листикл-заголовки («топ/рейтинг/лучшие/список») |
| 4 | URL Classifier (`url_classifier.py`) | РФ LLM lite | только border cases → company_homepage\|contacts\|services\|garbage |
| 5 | Cache Check | — | готовый лид по домену? HIT → сразу скоринг. TTL HTML 30д, AI lead 14д |
| 6 | Crawler (`crawler.py`) | — | стр./сайт по тарифу (Free2/Starter3/Pro5/Agency7/Max10); priority/skip paths; delay 1–3с; robots; UA-rotation; timeout 15с/стр |
| 7 | HTML Extraction (детерм.) | без LLM | email, phone, title, h1–h3, meta, schema.org, address, social_links, has_contact_form, about_text, visible_text_snippet(2000) |
| 8 | Light AI (1 credit) | РФ LLM lite | → industry, city, is_commercial, relevance_score, pass_to_deep_ai (true только если score≥60 AND is_commercial) |
| 9 | Deep AI (5 credits) | РФ LLM pro | заполнить Lead Schema (§6); decision_maker всегда null |
| 10 | Validation | — | dedup по hash(domain); confidence>0.5; формат email/phone |
| 11 | Scoring (`scoring.py`) | РФ LLM + детерм. бонусы | score 0–100, priority, reason |
| 12 | Outreach (3 credits) | РФ LLM pro | email_subject/body, telegram_message. Требует deep AI + score≥50 |
| 13 | Export + Observability | — | CSV/XLSX/Sheets/Webhook по тарифу; LeadProcessingLog → Postgres |

**Anti-loss guards** (перед каждым дорогим этапом) — `ANTI_LOSS_RULES` в `pipeline.py`:
```python
deep_ai_requires_light_ai_pass=True, light_ai_min_score_for_deep=60,
deduplicate_by_domain=True, skip_if_not_commercial=True,
outreach_requires_deep_ai=True, outreach_min_score=50,
check_credits_before_any_llm_call=True, check_cache_before_crawl=True,
enforce_max_pages_per_site=True, max_retry_attempts=3,
no_free_provider_for_paid_tiers=True,  # Groq/Gemini free только Free/MVP
```

---

## 6. Lead JSON Schema (canonical)

Единственно допустимая схема. Не менять без обновления этого файла.

```typescript
interface Lead {
  id: string; domain: string; website: string; created_at: string;
  user_id: string; campaign_id: string | null;
  company_name: string | null; city: string | null; region: string | null;
  address: string | null; industry: string | null;
  description: string | null;    // 1–2 предложения, только факты с сайта
  services: string[];
  phone: string | null; email: string | null; telegram: string | null;
  whatsapp: string | null; vk: string | null; instagram: string | null;
  has_contact_form: boolean;
  // decision_maker НЕ собираем (152-ФЗ, ПД третьих лиц). Всегда null. Поле — для совместимости схемы.
  decision_maker: { name: null; role: null; source_url: string | null };
  website_quality: {
    has_modern_design: boolean | null; has_mobile_adaptation: boolean | null;
    has_clear_cta: boolean | null; has_online_booking: boolean | null;
    has_outdated_content: boolean | null; seo_visible: boolean | null;
    comments: string | null;
  };
  lead_fit: { score: number; reason: string; priority: "low"|"medium"|"high" };
  pain_points: string[]; reason_to_contact: string | null;
  personalized_outreach: {
    email_subject: string | null; email_body: string | null;
    telegram_message: string | null; regeneration_count: number;
  };
  processing: {
    ai_level: "basic"|"light"|"deep"|"premium"; sources: string[];
    confidence: number; cache_hit: boolean; cost_usd: number;
  };
}
```
**Anti-hallucination:** нет данных на сайте → `null`. Никогда не придумывать email/телефон/имя. Важные поля — с `source_url`.

---

## 7. AI Credits и тарифы

```python
AI_CREDIT_COSTS = {  # YandexGPT Lite/Pro · GigaChat
  "light_ai_analysis": 1, "deep_ai_analysis": 5, "premium_ai_analysis": 15,
  "outreach_generation": 3, "outreach_regeneration": 3, "monitoring_signal": 2,
}
```

| Тариф | Цена/мес | Лидов | Deep AI | Стр./сайт | Себест. | Маржа |
|-------|----------|-------|---------|-----------|---------|-------|
| Free | 0₽ | 20 | 0 | 2 | ~30₽ | — |
| Starter | 990₽ | 200 | 0 | 3 | ~306₽ | ~69% |
| Pro | 2990₽ | 500 | 150 | 5 | ~1297₽ | ~57% |
| Agency | 7990₽ | 1500 | 400 | 7 | ~3393₽ | ~57% |
| Max | 19990₽ | 3000 | 800+150 premium | 10 | ~9958₽ | ~50% |

**Не хардкодить эти числа в логике** — config/БД.

---

## 8. Smart Model Routing и промпты

### Routing (целевое: только РФ — 152-ФЗ)
`lead_discovery` через LLM **отсутствует** (discovery = реальные поисковики). Стадии: Query Gen / URL Classify / Light AI / Inbox Classify → YandexGPT Lite (GigaChat lite); Deep AI / Outreach / Premium / Scoring(deep) → YandexGPT Pro (GigaChat Pro/Max).

**Текущее состояние (dev/MVP, мигрируем):** `routing.py` `STAGE_ROUTING` — Yandex первым приоритетом при наличии `YANDEX_API_KEY`+`YANDEX_FOLDER_ID`, иначе fallback на иностранные (OpenRouter gpt-4o-mini/gemini/sonar → nvidia GLM-5.1). Легаси-таски (`chat`, `letters`, `classify`, `enrich`) читают `settings.llm_<task>_*`. Иностранные модели — только dev/MVP, не для платных РФ. Прогресс РФ-миграции — PLAN.md.

**Endpoints:** YandexGPT `https://llm.api.cloud.yandex.net/foundationModels/v1` · GigaChat `https://gigachat.devices.sberbank.ru/api/v1` · (dev) NVIDIA `https://integrate.api.nvidia.com/v1` · (dev) OpenRouter `https://openrouter.ai/api/v1`

### Промпты (canonical — при изменении обновить здесь)

**ICP Parser** (`icp_parser.py`): по запросу + профилю продавца определяет intent (ищем покупателей/пользователей продукта vs компании в нише) и строит ICP: seller_summary, products, buyer_segments (конкретные отрасли/типы компаний, которые ПРИМЕНЯЮТ продукт), use_cases, positive/negative_keywords, excluded_industries. Строго JSON. Fallback на детерминированный профиль при сбое.

**Query Generator:** генератор поисковых запросов для B2B. Вход niche/city/service+ICP → 5–10 запросов на ОФИЦИАЛЬНЫЕ САЙТЫ (не агрегаторы/статьи) + negative keywords. JSON `{"queries":[{"query","intent","priority"}],"negative_keywords":[...]}`.

**Light AI:** классификатор лида, только JSON. Вход title/meta/h1/about/text/контакты/ICP/city → `{"industry","city","description","is_commercial","is_relevant_to_icp","relevance_score":0-100,"pass_to_deep_ai"}`. pass_to_deep_ai=true только если relevance_score≥60 AND is_commercial.

**Deep AI:** анализ сайта как B2B-специалист. Вход: продукт продавца + scraped pages + контакты парсера. Заполнить Lead Schema, данные ТОЛЬКО из текста, нет → null, НЕ ВЫДУМЫВАТЬ. decision_maker всегда null. Строго JSON.

**Outreach:** первое холодное сообщение от лица специалиста. Только факты из данных, без «вы теряете клиентов» — только наблюдения. Email: тема+тело ≤120 слов. Telegram ≤60 слов. JSON `{"email_subject","email_body","telegram_message"}`.

**Chat-агент (Лида):** ИИ по продажам, по-русски, кратко, без канцелярита, не упоминать что AI. Когда данных достаточно — сразу действовать через tool. Не выдумывать факты о клиентах. Профиль: business/offer/city/tone. temperature=0.4, max_tokens=1500, timeout=30s, retry=2x.

**Генерация писем:** кратко, без канцелярита, без эмодзи, max 1 «!», структура тема+приветствие+причина+оффер+мягкий CTA, {max_words} слов, тон {tone_ru}. JSON `{"subject","body"}`.

---

## 9. Cache Layer

Кэш обязателен — иначе повтор тратит деньги на краулинг и LLM.

| Что | TTL | Хранилище | Ключ |
|---|---|---|---|
| Search results | 7д | Postgres | sha256(query+region) |
| Raw HTML | 30д | Supabase Storage | sha256(url) |
| Basic extraction | 30д | Postgres | sha256(domain) |
| AI lead (light/deep) | 14д | Postgres | sha256(domain+schema_version) |
| Outreach | ❌ не кэшируется | — | всегда персонально |

Инвалидация по `content_hash` (HTML изменился → AI устарел). Поля в `leads/contacts`: `content_hash`, `last_scraped_at`, `last_ai_analysis_at`, `cache_valid`. Правило: **всегда проверять кэш до краулинга**.

---

## 10. Crawler Safety & Rate Limiting

```python
CRAWLER_CONFIG = {
  "delay_same_domain_ms": (1000, 3000), "delay_diff_domain_ms": (200, 800),
  "max_concurrent_per_domain": 1, "max_concurrent_total": 10,
  "respect_robots_txt": True, "user_agent_rotation": True,  # пул 20+ реальных UA
  "timeout_per_page_ms": 15_000,
  "proxy_datacenter": [...], "proxy_residential": [...],  # residential для Cloudflare
}
PRIORITY_PATHS = ["/", "/about", "/o-kompanii", "/o-nas", "/services", "/uslugi",
                  "/contacts", "/kontakty", "/price", "/prices", "/stoimost", "/portfolio"]
SKIP_PATHS = ["/blog", "/news", "/novosti", "/privacy", "/politika",
              "/terms", "/cart", "/login", "/register", "/cabinet"]
```
На потом (не MVP): JS-challenge solving, Playwright stealth, CAPTCHA solvers.

---

## 11. Observability + Схема БД

**LeadProcessingLog** — каждый LLM-вызов в `lead_processing_logs.llm_calls[]`. Поля лога: `search_query_original`, `search_queries_generated[]`, `urls_found/after_filter/crawled`, `pages_crawled_total`, `cache_hits/misses`, `total_cost_usd`, `ai_credits_used`, `lead_score`, `confidence`, `outcome (success|partial|failed|filtered_out)`, `failure_reason`, `duration_ms`. Каждый `llm_calls[]`: `call_id, model, stage (query_gen|url_classify|light_ai|deep_ai|premium_ai|scoring|outreach), input/output/cached_input_tokens, cost_usd, duration_ms, success, error`.

**Job Types** (Procrastinate, credits): search 0, scrape 0, light_ai 1, deep_ai 5, premium_ai 15, outreach 3, outreach_regen 3, monitoring 2. Каждый job: `id, type, user_id, campaign_id, payload, status (pending|running|done|failed|cancelled), priority, retry_count, max_retries, timestamps, error, cost_usd`.

**Таблицы БД** (`supabase/migrations/*.sql`, `supabase db push`): `users, companies, contacts, contact_lists, lead_lists, leads, activities, smtp_accounts, suppressions, templates, campaigns, campaign_messages, inbox_messages, chat_sessions, chat_messages, reminders, events, lead_processing_logs, token_store`.
**Инварианты:** контакты в `suppressions` исключаются при генерации/отправке; отправка только при `campaigns.status = ready`; квоты атомарно `UPDATE users SET sends_quota = sends_quota - $1 WHERE id=$2 AND sends_quota >= $1 RETURNING *`.
**При изменении схемы:** новая миграция + обновить этот список.

---

## 12. API (REST, `/api/v1`)

Auth: `Authorization: Bearer <access>` + httpOnly refresh cookie. Ошибки: `{"error":{"code","message"}}`.

| Группа | Эндпоинты |
|--------|-----------|
| Auth | POST /auth/register, /login, /verify-email, /refresh, /logout, /forgot-password, /reset-password |
| Me | GET/PATCH /me |
| Chat | POST /chat/sessions, GET /chat/sessions, GET /chat/sessions/{id}/messages, POST /chat/sessions/{id}/message (SSE) |
| CRM | GET/POST /companies, PATCH/DELETE /companies/{id}; GET/POST /contacts, PATCH/DELETE /contacts/{id}, GET /contacts/{id}/activities, POST /contacts/{id}/notes |
| Списки | GET/POST /contact-lists, DELETE /contact-lists/{id}, POST /contacts/import |
| SMTP | GET/POST /smtp-accounts, PATCH/DELETE /smtp-accounts/{id}, POST /smtp-accounts/{id}/verify |
| Templates | GET/POST /templates, PATCH/DELETE /templates/{id} |
| Campaigns | GET/POST /campaigns, GET /campaigns/{id}, POST /campaigns/{id}/generate, GET/PATCH /campaigns/{id}/messages, POST /campaigns/{id}/send, /pause, /resume, /followup, GET /campaigns/{id}/export.csv |
| Lead Search | POST /lead-search, GET /lead-search/{log_id}, GET /lead-search/{log_id}/export.csv, GET /lead-search/logs |
| Inbox | GET /inbox, POST /inbox/{id}/reply, PATCH /inbox/{id} |
| Suppressions | GET/POST /suppressions, DELETE /suppressions/{email} |
| Tracking (без auth, HMAC) | GET /t/o/{id}.gif, /t/c/{id}, /t/u/{id} |

**При добавлении эндпоинта — обновить таблицу.**

---

## 13. UI Формулировки

Показывать прогресс pipeline (не одно «AI analyzed»): Собрано / Базовая обработка / Light AI / Глубоко проанализировано N/M / Сообщений N/M / Осталось credits.
Описания тарифов — конкретно (не «X AI-лидов»): Free «до 20 лидов для теста, без deep/premium»; Starter «до 200, Light AI»; Pro «до 500, Light всем, deep до 150, до 150 сообщений»; Agency «до 1500, deep до 400, мониторинг 50»; Max «до 3000, deep до 800, premium до 150, CRM-интеграции».
Anti-hallucination в письмах: ❌«вы теряете клиентов из-за сайта» → ✅«нет онлайн-записи на первом экране — возможно, снижает конверсию».

---

## 14. Безопасность

- Argon2 пароли. JWT access 15 мин + httpOnly refresh 7 дней.
- SMTP-пароли — Fernet (`FERNET_KEY`). HMAC `tracking_id` (`TRACKING_SECRET`).
- Rate-limit: `/auth/*` 10/min/IP, `/campaigns/*/send` 5/min/user, `/chat/*` 30/min/user, `/lead-search` POST 10/min/user, `/webhooks/*` 60/min.
- RLS в Supabase: `user_id = auth.uid()` на всех таблицах.

---

## 15. 152-ФЗ

**Модели — только РФ-хостинг (целевое):** провайдер `yandex` + GigaChat, данные не покидают РФ. Open-weight галереи Yandex AI Studio (DeepSeek/Qwen/gpt-oss) разрешены для платных РФ (инференс в Yandex Cloud РФ; подтвердить российский ДЦ в договоре перед платным запуском). Прямые иностранные API — только dev/MVP. Если включается иностранный API (опц. Sonar) — только под явным согласием (`users.llm_consent_at`), default выкл.

**Хранение данных — осознанный отложенный риск:** локализация (ст.18 ч.5) требует БД в РФ; триггер — аккаунты пользователей, не только лиды. Supabase(EU/US)+Vercel(US) не соответствуют. На MVP остаёмся (принятый риск, не «легально»). Переезд на РФ VPS (свой Postgres + РФ Storage: Yandex Object Storage/Selectel/VK Cloud + RLS в app-слое) — milestone перед платным запуском, не блокер MVP.

**ПД лидов (третьих лиц):** ФИО/ЛПР не собираем (§2, §6), только публичные контакты компании; основание — общедоступные источники (ст.8); обеспечить право на удаление (запрос → удаление из БД).

**Обязательно сейчас (дёшево):** privacy policy + согласие на обработку ПД пользователя; чекбокс трансграничной передачи (если иностранные модели); в каждом письме — принудительный unsubscribe + глобальный suppression.

---

## 16. Coding style

- Backend: Python 3.12, Ruff, line length 120, typed Pydantic, тонкие роутеры.
- Frontend: TypeScript, React function components, Tailwind. PascalCase компоненты, camelCase функции. Типы API — через `openapi-typescript`. Server state — только TanStack Query.
- Тесты: `backend/tests/test_<feature>.py`, pytest + pytest-asyncio.
- Коммиты: Conventional Commits (`feat:`, `fix:`, `chore:`). PR: summary + test results + migration notes + screenshots для UI.
