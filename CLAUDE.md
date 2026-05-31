# CLAUDE.md — единственный источник правды для AI-агентов

> Версия: 4.0 (май 2026). Заменяет CLAUDE_ADDITIONAL.md, старый CLAUDE.md и AGENTS.md.
> Читать этот файл **перед любым** изменением кода.

---

## 1. Продукт

**Лида AI** — ИИ-агент для поиска, анализа и квалификации B2B-лидов. Старое кодовое имя `parcer` — только в репозитории и технических следах.

**Что делает:**
- Находит компании по нише и гео (SerpAPI → реальные сайты)
- Анализирует сайты (crawler → HTML extraction → Light AI → Deep AI)
- Оценивает качество лида и готовит персонализированное первое сообщение
- Ведёт CRM: статусы, активности, follow-up, inbox

**Что НЕ делает и как НЕ позиционировать:**
- Не парсер, не скрапер, не база email, не массовая рассылка
- Не обходит защиты, не продаёт контакты, не спам

**Целевая аудитория:** ИП, фрилансеры B2B, агентства без отдела продаж в РФ/СНГ.

---

## 2. Правила для агента (обязательны)

- Отвечать по-русски, если вопрос по-русски
- Говорить чётко, правду, трезво оценивать риски и не скрывать неопределённость
- **НЕ** предлагать: Google Search API, WhatsApp Business API, Kubernetes, Elasticsearch, Alembic, локальный Docker/Postgres/Redis, Авито как источник
- **НЕ** использовать слова «парсер», «скрапер», «база email», «массовая холодная рассылка» в копии продукта
- **Миграции — только через Supabase CLI** (`supabase/migrations/*.sql`). Никакого Alembic
- Бизнес-логика — в `backend/app/services/`, роутеры тонкие
- Все внешние вызовы (LLM, SMTP, IMAP, поиск) — с таймаутом и retry
- Секреты — только через env
- При изменении БД — новая миграция + обновить раздел 11 ниже
- При добавлении API-эндпоинта — обновить раздел 12 ниже
- При изменении промпта — обновить раздел 8 ниже
- Не хардкодить тарифные лимиты в бизнес-логике — только через config/константы
- Не выдумывать email, телефон, имя — если данных нет на сайте, писать `null`

---

## 3. Dev-команды

### Backend (из `backend/`)
```bash
pip install -e ".[dev]"
uvicorn app.main:app --reload
python -m procrastinate --app app.workers.main.app worker
ruff check .
ruff format .
pytest tests/ -v
pytest tests/test_auth.py::test_login_success -v
```

### Frontend (из `frontend/`)
```bash
npm install
npm run dev        # Vite :5173
npm run build
npm run lint
```

### БД (Supabase CLI)
```bash
supabase migration new <name>
supabase db push
supabase db reset
```

### Makefile
`make dev` — API + Vite одновременно.
`make dev-api`, `make dev-worker`, `make dev-web`, `make test`, `make lint`,
`make migrate-new name=...`, `make migrate-push`, `make migrate-reset`, `make seed`, `make types`.

### Quickstart
```bash
cp .env.example .env   # заполнить SUPABASE_*, LLM keys, SECRET_KEY, FERNET_KEY, TRACKING_SECRET
supabase link --project-ref <ref>
supabase db push
make install
make dev
```

---

## 4. Архитектура стека

**Cloud-first, без локального Docker:**
- Postgres + Storage — Supabase (облако)
- Очереди — Procrastinate в Supabase Postgres
- Локально: uvicorn, Procrastinate worker, Vite dev-server

**Backend:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 async, Procrastinate
**Frontend:** React 18 + Vite + TypeScript + Tailwind + shadcn/ui + TanStack Query + SSE
**LLM:** GLM-5.1 через NVIDIA API (chat, classify, enrich, letters), Claude (deep AI, prod)

```
backend/
  app/
    api/v1/       # тонкие роутеры
    core/         # config, database, security, tokens, fernet, tracking
    services/     # вся бизнес-логика
      auth_service.py
      llm/        # base, factory, groq, qwen, glm, nvidia, claude
      chat/       # agent.py, tools.py
      crm/        # companies_service, contacts_service, contact_import
      inbox/      # classifier
      letters/    # generator
      leads/      # pipeline.py, extraction.py, scoring.py  ← главный pipeline
      search/     # serp.py, yandex.py, firecrawl.py, hunter.py
      enrichment.py
      gmail.py
    workers/      # Procrastinate tasks
    models/       # SQLAlchemy ORM
    schemas/      # Pydantic

frontend/
  src/
    pages/
    features/
    components/ui/
    lib/          # api.ts, sse.ts, auth.ts

supabase/
  migrations/     # *.sql

docs/
  PROJECT.md      # продуктовый контекст (не для агентов)
  PROGRESS.md     # snapshot прогресса (может устареть — не опираться)
```

---

## 5. Pipeline поиска лидов (canonical, 13 шагов)

Это **единственная** правильная архитектура pipeline. Текущий `services/leads/pipeline.py` реализует основной backend-flow
по этой схеме: query generation, search, URL filter, cache check, crawler, HTML extraction, light/deep AI, scoring,
optional outreach и observability. URL classifier существует отдельным модулем и должен быть подключён к border cases
отдельной задачей.

```
User Input: "Найди стоматологии в Екб со слабым сайтом"
      ↓
STEP 1 — Query Generator
  Модель: GLM-5.1 через NVIDIA API
  Вход: 1 запрос → Выход: 5–15 поисковых вариантов + negative keywords
      ↓
STEP 2 — Search Module
  API: SerpAPI + Yandex Search API + Perplexity Sonar (LLM live web discovery, если OPENROUTER_API_KEY задан)
  Perplexity Sonar ищет компании напрямую по живому вебу (не из памяти модели); fallback — nvidia GLM.
  Выход: ~200 URL | Cache TTL: 7 дней (key: sha256(query+region))
      ↓
STEP 3 — URL Filter (детерминированный, без LLM)
  Блокировать: avito.ru, hh.ru, vc.ru, habr.com, 2gis.ru, wildberries.ru,
               zoon.ru, otzovik.com, prodoctorov.ru, yell.ru, flamp.ru
  Блокировать паттерны: /blog/, /news/, /tag/, /category/, /vakansii/,
                        /jobs/, /privacy/, /terms/, ?utm_, /page/\d+, \.pdf$
  Блокировать заголовки: "топ-", "рейтинг", "лучшие", "список", "как выбрать"
  Выход: ~80–100 URL
      ↓
STEP 4 — URL Classifier (LLM, только border cases)
  Модель: GLM-5.1 через NVIDIA API
  Запускать только если детерминированный слой не уверен
  Выход: company_homepage | contacts | services | garbage
      ↓
STEP 5 — Cache Check
  Проверить Supabase: есть ли готовый лид для домена?
  Cache TTL HTML: 30 дней | Cache TTL AI lead: 14 дней
  HIT → пропустить шаги 6–8, идти в Scoring
      ↓
STEP 6 — Crawler
  Лимиты страниц по тарифу: Free=2, Starter=3, Pro=5, Agency=7, Max=10
  Приоритет путей: /, /about, /o-kompanii, /contacts, /services, /price
  Пропускать: /blog, /news, /privacy, /cart, /login
  delay: рандом 1000–3000ms, max 1 concurrent per domain
  respect_robots_txt: true | user_agent_rotation: true
  Timeout: 15 сек/страница | Cache HTML: 30 дней
      ↓
STEP 7 — Basic HTML Extraction (детерминированный, без LLM)
  Извлекать: email, phone, title, h1–h3, meta description, schema.org,
             address, social_links (vk, telegram, whatsapp), has_contact_form,
             about_text (блок "О нас/О компании"), visible_text_snippet (первые 2000 символов)
      ↓
STEP 8 — Light AI (1 credit, если тариф позволяет)
  Модель: GLM-5.1 через NVIDIA API
  Выход: { industry, city, description, is_commercial, is_relevant_to_icp,
            relevance_score 0–100, pass_to_deep_ai }
  pass_to_deep_ai = true только если relevance_score >= 60 AND is_commercial = true
      ↓ (только лиды с pass_to_deep_ai=true)
STEP 9 — Deep AI Extraction (5 credits)
  Модель: Claude Sonnet 4.6 / GPT-5.4 (dev: не запускать без явного ключа)
  Задача: заполнить полную Lead JSON Schema (раздел 6)
      ↓
STEP 10 — Validation
  Дедупликация по hash(domain) — дубли не тратят credits
  Фильтр: confidence > 0.5 | email/phone формат
      ↓
STEP 11 — Lead Scoring
  Модель: Sonnet 4.6 для deep-leads, Haiku для light-leads
  Выход: score 0–100, priority (low/medium/high), reason
      ↓ (только deep AI лиды)
STEP 12 — Outreach Generation (3 credits)
  Модель: Sonnet 4.6 / GPT-5.4
  Выход: email_subject, email_body, telegram_message
  Требования: score >= 50, deep AI обязателен
      ↓
STEP 13 — Export + Observability Log
  Форматы по тарифу: CSV, XLSX, Google Sheets, Webhook, CRM
  Параллельно: LeadProcessingLog → Postgres
```

**Anti-loss правила (реализовать как guard перед каждым дорогим этапом):**
```python
ANTI_LOSS_RULES = {
    "deep_ai_requires_light_ai_pass": True,      # нет deep без light
    "light_ai_min_score_for_deep": 60,
    "deduplicate_by_domain": True,               # дубли не тратят credits
    "skip_if_not_commercial": True,
    "outreach_requires_deep_ai": True,
    "outreach_min_score": 50,
    "check_credits_before_any_llm_call": True,   # credits до вызова
    "check_cache_before_crawl": True,
    "enforce_max_pages_per_site": True,          # по тарифу
    "max_retry_attempts": 3,
    "no_free_provider_for_paid_tiers": True,     # Groq/Gemini free только для Free/MVP
}
```

---

## 6. Lead JSON Schema (canonical)

Единственно допустимая схема объекта лида. Не менять без обновления этого файла.

```typescript
interface Lead {
  id: string;                    // uuid v4
  domain: string;                // нормализованный домен без www
  website: string;
  created_at: string;
  user_id: string;
  campaign_id: string | null;

  company_name: string | null;
  city: string | null;
  region: string | null;
  address: string | null;
  industry: string | null;
  description: string | null;    // 1–2 предложения, только факты с сайта
  services: string[];

  phone: string | null;
  email: string | null;
  telegram: string | null;
  whatsapp: string | null;
  vk: string | null;
  instagram: string | null;
  has_contact_form: boolean;

  decision_maker: {
    name: string | null;
    role: string | null;
    source_url: string | null;
  };

  website_quality: {
    has_modern_design: boolean | null;
    has_mobile_adaptation: boolean | null;
    has_clear_cta: boolean | null;
    has_online_booking: boolean | null;
    has_outdated_content: boolean | null;
    seo_visible: boolean | null;
    comments: string | null;
  };

  lead_fit: {
    score: number;               // 0–100
    reason: string;
    priority: "low" | "medium" | "high";
  };
  pain_points: string[];
  reason_to_contact: string | null;

  personalized_outreach: {
    email_subject: string | null;
    email_body: string | null;
    telegram_message: string | null;
    regeneration_count: number;
  };

  processing: {
    ai_level: "basic" | "light" | "deep" | "premium";
    sources: string[];           // URL-источники
    confidence: number;          // 0..1
    cache_hit: boolean;
    cost_usd: number;
  };
}
```

**Правило anti-hallucination:** если данных нет на сайте — `null`. Никогда не придумывать email, телефон, имя. Все важные поля должны иметь `source_url`.

---

## 7. AI Credits и тарифы

### Стоимость операций
```python
AI_CREDIT_COSTS = {
    "light_ai_analysis":    1,   # Haiku / GLM-Flash
    "deep_ai_analysis":     5,   # Sonnet 4.6
    "premium_ai_analysis": 15,   # GLM-5 / Sonnet 4.6
    "outreach_generation":  3,   # Sonnet 4.6
    "outreach_regeneration": 3,
    "monitoring_signal":    2,
}
```

### Тарифная сетка (v3.1)

| Тариф | Цена/мес | Лидов | Deep AI | Стр./сайт | Себестоимость | Маржа |
|-------|----------|-------|---------|-----------|---------------|-------|
| Free | 0₽ | 20 | 0 | 2 | ~30₽ | — |
| Starter | 990₽ | 200 | 0 | 3 | ~306₽ | ~69% |
| Pro | 2990₽ | 500 | 150 | 5 | ~1297₽ | ~57% |
| Agency | 7990₽ | 1500 | 400 | 7 | ~3393₽ | ~57% |
| Max | 19990₽ | 3000 | 800+150 premium | 10 | ~9958₽ | ~50% |

**Не хардкодить эти числа в логике** — хранить в конфиге/БД.

---

## 8. Smart Model Routing

### Production routing по тарифам

| Задача | Free | Starter | Pro / Agency | Max |
|--------|------|---------|--------------|-----|
| Query Gen | Groq Llama 8B (free) | Gemini Flash-Lite | Haiku 4.5 | Haiku 4.5 |
| URL Classify | Groq Llama 8B (free) | Gemini Flash-Lite | Haiku 4.5 | Haiku 4.5 |
| Light AI | Gemini Flash (free) | DeepSeek V3 | Haiku 4.5 | Haiku 4.5 |
| Deep AI | ❌ | ❌ | Sonnet 4.6 | Sonnet 4.6 |
| Outreach | шаблонное | шаблонное | Sonnet 4.6 | Sonnet 4.6 |
| Premium AI | ❌ | ❌ | ❌ | GLM-5 / Sonnet 4.6 |

### Dev/MVP — текущий роутинг по стадиям

Источник правды — `backend/app/services/llm/routing.py` (`STAGE_ROUTING`).
Без OpenRouter-ключа все стадии падают в fallback nvidia GLM-5.1.

| Стадия | С OpenRouter-ключом | Fallback (без ключа) |
|--------|---------------------|----------------------|
| `query_gen` | google/gemini-2.0-flash-001 via OpenRouter | nvidia GLM-5.1 |
| `url_classify` | google/gemini-2.0-flash-8b via OpenRouter | groq llama-3.3-70b → nvidia GLM-5.1 |
| `light_ai` | deepseek/deepseek-chat via OpenRouter | nvidia GLM-5.1 |
| `deep_ai` | deepseek/deepseek-chat via OpenRouter | nvidia GLM-5.1 |
| `outreach` | deepseek/deepseek-chat via OpenRouter | nvidia GLM-5.1 |
| `inbox_classify` | google/gemini-2.0-flash-8b via OpenRouter | nvidia GLM-5.1 |
| `lead_discovery` | perplexity/sonar via OpenRouter | nvidia GLM-5.1 |

Легаси-таски (`chat`, `letters`, `classify`, `enrich`) по-прежнему читают `settings.llm_<task>_*`.

**Правило:** free tiers Groq/Gemini/GLM — только для Free-тарифа и MVP. Для платных тарифов — только платные API.

### Endpoints провайдеров
- NVIDIA GLM: `https://integrate.api.nvidia.com/v1`
- GLM direct: `https://open.bigmodel.cn/api/paas/v4`
- Groq: `https://api.groq.com/openai/v1`
- Qwen: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- OpenRouter: `https://openrouter.ai/api/v1`

---

## 9. Промпты (canonical)

### Query Generator
```
Ты генератор поисковых запросов для B2B лидогенерации.
Ниша: {niche} | Город: {city} | Услуга: {service_offered}

Сгенерируй 5–10 запросов для Google/Yandex.
Каждый запрос должен находить ОФИЦИАЛЬНЫЕ САЙТЫ, не агрегаторы и статьи.
Добавь negative keywords.

Отвечай строго JSON:
{"queries":[{"query":"...","intent":"company_homepage|contacts_page|services_page|price_page","priority":"high|medium|low"}],"negative_keywords":["..."],"expected_results_per_query":20}
```

### Light AI
```
Ты классификатор B2B-лидов. Отвечай только JSON.

Title: {title} | Description: {meta_description} | H1: {h1}
About section: {about_text}
Text: {visible_text_snippet}
Контакты: email={email}, phone={phone}
ICP: {icp_description} | Город: {city}

Задача: стоит ли лид глубокого анализа?

{"industry":"...","city":"...","description":null,"is_commercial":true|false,"is_relevant_to_icp":true|false,"relevance_score":0-100,"pass_to_deep_ai":true|false}

pass_to_deep_ai=true только если relevance_score>=60 AND is_commercial=true.
```

### Deep AI Extraction
```
Ты анализируешь сайт компании как B2B-специалист.
Пользователь продаёт: {service_offered}

{scraped_pages_combined_text}

Контакты из парсера: email={email}, phone={phone}, telegram={telegram}

Заполни Lead JSON Schema. Данные ТОЛЬКО из текста выше. Если нет — null. НЕ ВЫДУМЫВАЙ.
Отвечай строго JSON, без текста вне JSON.
```

### Outreach Generation
```
Ты пишешь первое холодное сообщение от лица специалиста.

Специалист продаёт: {service_offered}
Компания: {company_name} | Ниша: {industry}
Описание: {description} | Слабые места: {pain_points} | Повод: {reason_to_contact}

Правила:
1. Только факты из данных выше — не выдумывать
2. Не писать "вы теряете клиентов" — только наблюдения
3. Email: тема + тело, не более 120 слов
4. Telegram: не более 60 слов

{"email_subject":"...","email_body":"...","telegram_message":"..."}
```

### Chat-агент (Лида)
```
Ты — Лида, ИИ-агент по продажам для бизнеса пользователя в России.
Помогаешь: искать компании-клиенты, писать персональные письма, вести CRM, отвечать на входящие.

Говоришь по-русски, кратко, без канцелярита.
Когда данных достаточно — сразу действуй через tool. Не переспрашивай лишнего.
Никогда не выдумывай факты о клиентах. Не упоминай, что ты AI.

Профиль: Бизнес={business} | Оффер={offer} | Город={city} | Тон={tone_default}
```
Parameters: temperature=0.4, max_tokens=1500, timeout=30s, retry=2x.

### Генерация писем (Qwen/Sonnet)
System: кратко, без канцелярита, без эмодзи, max 1 восклицательный знак, структура: тема + приветствие + причина + оффер + мягкий CTA, {max_words} слов, тональность {tone_ru}. Только JSON `{"subject":"...","body":"..."}`.

---

## 10. Cache Layer

Кэш обязателен — без него каждый повторный запрос тратит деньги на краулинг и LLM.

| Что кэшируем | TTL | Хранилище | Ключ |
|---|---|---|---|
| Search results | 7 дней | Supabase Postgres | sha256(query + region) |
| Raw HTML страниц | 30 дней | Supabase Storage (S3) | sha256(url) |
| Basic extraction result | 30 дней | Postgres | sha256(domain) |
| AI lead (light/deep) | 14 дней | Postgres | sha256(domain + schema_version) |
| Outreach | ❌ не кэшируется | — | всегда персонально |

Инвалидация: по `content_hash` — если HTML изменился, AI-результат устарел.

```sql
-- Поля для инвалидации на таблице leads/contacts
content_hash         TEXT,
last_scraped_at      TIMESTAMPTZ,
last_ai_analysis_at  TIMESTAMPTZ,
cache_valid          BOOLEAN DEFAULT TRUE
```

**Правило:** `check_cache_before_crawl: true` — всегда проверять кэш до краулинга.

---

## 11. Crawler Safety & Rate Limiting

Реализовать с первого дня — не "потом".

```python
CRAWLER_CONFIG = {
    # Задержки
    "delay_same_domain_ms":      (1000, 3000),   # рандом в диапазоне
    "delay_diff_domain_ms":      (200, 800),
    # Параллелизм
    "max_concurrent_per_domain": 1,
    "max_concurrent_total":      10,
    # Безопасность
    "respect_robots_txt":        True,           # обязательно
    "user_agent_rotation":       True,           # пул 20+ реальных UA
    "timeout_per_page_ms":       15_000,
    # Прокси
    "proxy_datacenter":          [...],          # $0.5–1/GB, большинство сайтов
    "proxy_residential":         [...],          # $5–15/GB, Cloudflare-защищённые
}

PRIORITY_PATHS = ["/", "/about", "/o-kompanii", "/o-nas",
                  "/services", "/uslugi", "/contacts", "/kontakty",
                  "/price", "/prices", "/stoimost", "/portfolio"]

SKIP_PATHS = ["/blog", "/news", "/novosti", "/privacy", "/politika",
              "/terms", "/cart", "/login", "/register", "/cabinet"]
```

На потом (не MVP): JS-challenge solving, Playwright stealth, CAPTCHA solvers.

---

## 12. Observability — логирование каждого лида

Обязательно реализовать с первого дня. Без этого не видно, где сжигаются деньги.

Каждый LLM-вызов логировать в `lead_processing_logs.llm_calls[]`:

```python
# Полная структура LeadProcessingLog
{
    "log_id": "uuid",
    "lead_id": "uuid | null",
    "user_id": "uuid",
    "campaign_id": "uuid | null",
    "created_at": "ISO8601",

    # Что искали
    "search_query_original": str,
    "search_queries_generated": [str],   # сколько вариантов сделал Query Gen
    "urls_found": int,
    "urls_after_filter": int,
    "urls_crawled": int,
    "pages_crawled_total": int,

    # Кэш
    "cache_hits": int,
    "cache_misses": int,

    # Каждый LLM-вызов
    "llm_calls": [
        {
            "call_id": "uuid",
            "model": str,
            "stage": "query_gen|url_classify|light_ai|deep_ai|premium_ai|scoring|outreach",
            "input_tokens": int,
            "output_tokens": int,
            "cached_input_tokens": int,
            "cost_usd": float,
            "duration_ms": int,
            "success": bool,
            "error": "str | null",
        }
    ],

    # Итог
    "total_cost_usd": float,
    "ai_credits_used": int,
    "lead_score": "int | null",
    "confidence": "float | null",
    "outcome": "success|partial|failed|filtered_out",
    "failure_reason": "str | null",
    "duration_ms": int,
}
```

---

## 13. Job Types (очередь Procrastinate)

```python
JOB_TYPES = {
    "search_job":        0,   # credits (бесплатно)
    "scrape_job":        0,   # credits (бесплатно)
    "light_ai_job":      1,   # credit
    "deep_ai_job":       5,   # credits
    "premium_ai_job":   15,   # credits
    "outreach_job":      3,   # credits
    "outreach_regen_job": 3,  # credits
    "monitoring_job":    2,   # credits
}
```

Каждый job: `id, type, user_id, campaign_id, payload, status (pending|running|done|failed|cancelled), priority, retry_count, max_retries, created_at, started_at, finished_at, error, cost_usd`.

---

## 14. UI Формулировки (что показывать пользователю)

**Вместо одного "AI analyzed" показывать прогресс pipeline:**
```
Собрано компаний:            500
Прошло базовую обработку:    500
Light AI обработано:         500
Глубоко проанализировано:    143 / 150
Сгенерировано сообщений:     143 / 150
Осталось AI credits:         218 / 800
```

**Описания тарифов (не "X AI-лидов", а конкретно):**
| Тариф | Формулировка |
|-------|-------------|
| Free | До 20 найденных лидов для теста. Бесплатные модели, без deep/premium анализа. |
| Starter | До 200 найденных лидов. Light AI, без deep/premium анализа. |
| Pro | До 500 лидов, Light AI для всех, глубокий анализ до 150 лучших, до 150 персональных сообщений. |
| Agency | До 1500 лидов, Light AI для всех, глубокий анализ до 400 лучших, мониторинг 50 компаний. |
| Max | До 3000 лидов, Light AI для всех, до 800 глубоких анализов, до 150 premium-анализов, CRM-интеграции. |

**Anti-hallucination в письмах:**
- Плохо: «Я вижу, что ваша клиника теряет клиентов из-за плохого сайта.»
- Хорошо: «Заметил, что на сайте нет онлайн-записи на первом экране. Возможно, это снижает конверсию.»

---

## 15. E2E сценарий (пример финального лида)

**Вход:** «Найди стоматологии в Екатеринбурге со слабым сайтом»

**Выход после полного pipeline:**
```json
{
  "domain": "example-dental.ru",
  "company_name": "Стоматология Улыбка",
  "city": "Екатеринбург",
  "industry": "Стоматология",
  "phone": "+7 (343) 123-45-67",
  "email": null,
  "telegram": "https://t.me/example_dental",
  "services": ["лечение зубов", "имплантация", "ортодонтия"],
  "website_quality": {
    "has_modern_design": false,
    "has_mobile_adaptation": true,
    "has_clear_cta": false,
    "has_online_booking": false,
    "seo_visible": false,
    "comments": "Нет онлайн-записи. Слабый CTA. Meta-теги не заполнены."
  },
  "lead_fit": {
    "score": 82,
    "reason": "Коммерческий сайт с реальными услугами. Нет онлайн-записи и SEO — прямой повод для предложения.",
    "priority": "high"
  },
  "pain_points": ["нет онлайн-записи", "слабый CTA", "не заполнены meta-теги"],
  "personalized_outreach": {
    "email_subject": "Идея по увеличению заявок с сайта вашей клиники",
    "email_body": "Здравствуйте!\n\nИзучил ваш сайт и заметил, что пользователям сложно быстро записаться онлайн — такой кнопки нет на первом экране. Плюс мета-теги не настроены, что снижает видимость в поиске.\n\nЕсли интересно — могу показать, как небольшие изменения увеличивают количество заявок.",
    "telegram_message": "Добрый день! Посмотрел ваш сайт — нет онлайн-записи и SEO не настроен. Могу показать быстрое решение. Удобно коротко созвониться?",
    "regeneration_count": 0
  },
  "processing": {
    "ai_level": "deep",
    "sources": ["https://example-dental.ru/", "https://example-dental.ru/uslugi"],
    "confidence": 0.81,
    "cache_hit": false,
    "cost_usd": 0.047
  }
}
```

---

## 16. Текущий статус реализации  <!-- обновлять при каждом изменении -->

### Реализовано (рабочее)
| Модуль | Файл |
|--------|------|
| Auth (register/login/verify/reset) | `api/v1/auth.py`, `services/auth_service.py` |
| Chat SSE + tool-calling (GLM-5.1 через NVIDIA) | `services/chat/agent.py`, `api/v1/chat.py`, `services/llm/glm_nvidia.py` |
| Генерация писем (GLM-5.1 через NVIDIA) | `services/letters/generator.py`, `services/llm/glm_nvidia.py` |
| Отправка SMTP + Gmail OAuth | `workers/main.py:send_email`, `services/gmail.py` |
| Tracking (pixel, click, unsub) | `api/v1/tracking.py`, `core/tracking.py` |
| Inbox poll + AI-классификация | `workers/main.py:poll_inbox,classify_inbox_message` |
| CSV-импорт контактов | `services/crm/contact_import.py` |
| Lead search pipeline: Query Gen, Search (SerpAPI + Perplexity Sonar), URL Filter, URL Classifier, Cache, Crawler, HTML Extraction, Light/Deep AI, Validation, Scoring, optional Outreach, Observability | `services/leads/pipeline.py`, `services/leads/*`, `services/llm/logged.py` |
| LLM роутинг по стадиям (STAGE_ROUTING + OpenRouter + Perplexity fallback) | `services/llm/routing.py`, `services/llm/factory.py`, `services/search/perplexity_search.py` |
| AI Credits: баланс пользователя + атомарный check/deduct перед дорогими LLM-вызовами | `services/credits.py`, `models/user.py` |
| Companies / Contacts / Campaigns / Templates / SMTP API | `api/v1/*.py` |
| run_followup, run_reminders (по расписанию) | `workers/main.py` |
| Periodic cleanup пустых списков | `workers/main.py:cleanup_empty_contact_lists` |
| Fernet-шифрование SMTP-паролей | `core/fernet.py` |

### Заглушки / не реализовано
| Что | Где | Приоритет |
|-----|-----|-----------|
| Тарифные лимиты/квоты для lead pipeline вынести в config/service | частично в коде | Высокий |
| Квоты leads_quota / sends_quota полностью провести по workflow | частично в коде | Высокий |
| Карточка контакта `/app/contacts/:id` | нет | Средний |
| Карточка компании `/app/companies/:id` | нет | Средний |
| Дашборд кампании `/app/campaigns/:id` | нет | Средний |
| Export lead lists: CSV/XLSX/Google Sheets/Webhook | нет | Средний |
| Rate-limit на эндпоинтах | нет | Средний |
| Лендинг `/` | нет | До запуска |
| ЮKassa биллинг | нет | После MVP |

---

## 17. Схема БД

Миграции: `supabase/migrations/*.sql`. Применение: `supabase db push`.

Ключевые таблицы: `users`, `companies`, `contacts`, `contact_lists`, `lead_lists`, `leads`, `activities`, `smtp_accounts`, `suppressions`, `templates`, `campaigns`, `campaign_messages`, `inbox_messages`, `chat_sessions`, `chat_messages`, `reminders`, `events`, `lead_processing_logs`, `token_store`.

**Инварианты:**
- Контакты в `suppressions` — исключаются при генерации и отправке
- Отправлять можно только `campaigns.status = ready`
- Квоты декрементируются атомарно: `UPDATE users SET sends_quota = sends_quota - $1 WHERE id=$2 AND sends_quota >= $1 RETURNING *`

**При изменении схемы:** создать новую миграцию + обновить этот раздел.

---

## 18. API (REST, `/api/v1`)

Auth: `Authorization: Bearer <access>` + httpOnly refresh cookie. Ошибки: `{"error": {"code", "message"}}`.

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
| Lead Search | POST /lead-search, GET /lead-search/{log_id} (status + leads), GET /lead-search/logs |
| Inbox | GET /inbox, POST /inbox/{id}/reply, PATCH /inbox/{id} |
| Suppressions | GET/POST /suppressions, DELETE /suppressions/{email} |
| Tracking (без auth, HMAC) | GET /t/o/{id}.gif, /t/c/{id}, /t/u/{id} |

**При добавлении эндпоинта — обновить эту таблицу.**

---

## 19. Безопасность

- Argon2 для паролей
- JWT access 15 мин + httpOnly refresh cookie 7 дней
- SMTP-пароли — Fernet, ключ `FERNET_KEY` в env
- HMAC-подписанный `tracking_id` (ключ `TRACKING_SECRET`)
- Rate-limit: `/auth/*` 10/min/IP, `/campaigns/*/send` 5/min/user, `/chat/*` 30/min/user
- RLS в Supabase: `user_id = auth.uid()` на всех таблицах

---

## 20. 152-ФЗ и LLM-трансграничка

- Данные пользователя и контактов — в Supabase
- AI-функции отправляют данные в Groq (США), Qwen (Китай), GLM (Китай), Claude (США)
- Требуется явное согласие пользователя (`users.llm_consent_at`)
- Без согласия — AI-функции заблокированы
- В каждом письме: принудительный unsubscribe, глобальный suppression по отпискам

---

## 21. Coding style

- Backend: Python 3.12, Ruff, line length 120. Typed Pydantic schemas. Роутеры тонкие
- Frontend: TypeScript, React function components, Vite, Tailwind. PascalCase компоненты, camelCase функции
- Типы API на фронте — через `openapi-typescript`, не руками
- Server state — только TanStack Query
- Тесты: `backend/tests/test_<feature>.py`, pytest + pytest-asyncio
- Коммиты: `feat:`, `fix:`, `chore:` — Conventional Commits style
- PR: summary + test results + migration notes + screenshots для UI
