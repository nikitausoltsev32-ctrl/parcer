# CLAUDE.md — AI Lead Scraping Platform (Parcer Bot)

> Мастер-документ для AI-агентов (Cursor, Claude Code и др.).
> Описывает продуктовую логику, архитектуру, тарифную экономику, схемы данных и правила реализации.
> Версия: 3.1 (май 2026). Источник: product_logic_v1 + addendum_v2 + tariff_margin_logic.

---

## РАЗДЕЛ 0 — Для агента: как читать этот файл

Этот файл — единственный источник правды о продукте. При написании кода:

1. **Сначала читай этот файл целиком** перед тем как писать любой модуль.
2. **Имена функций, типов, констант** — бери из схем и таблиц ниже, не придумывай.
3. **Архитектура pipeline** — строго по разделу 3. Порядок этапов нельзя менять.
4. **Модели** — выбирай по smart routing из раздела 8. Не фиксируй premium-модель без проверки экономики тарифа.
5. **Тарифные лимиты** — реализуй через `ai_credits` систему (раздел 7). Не хардкодь числа в логике.
6. **JSON Schema лида** — строго по разделу 5. Не добавляй поля без необходимости.
7. **Anti-loss правила** — раздел 12 обязателен к реализации.
8. **Observability** — каждый LLM-вызов логируется (раздел 11).

---

## РАЗДЕЛ 1 — Продуктовая идея

**Продукт:** AI-агент для поиска, анализа и квалификации B2B-лидов.

Не парсер. Не просто база контактов. Система, которая:
- сама находит компании по нише и гео;
- заходит на их сайты;
- понимает, чем компания занимается и есть ли повод предложить услугу;
- оценивает качество лида;
- готовит персонализированное сообщение для первого контакта.

**Целевая аудитория:** фрилансеры, веб-агентства, B2B-отделы продаж в России и СНГ.

**Позиционирование:**

```
AI-агент для поиска, анализа и квалификации B2B-лидов.
Он сам находит компании, анализирует их сайты, вытаскивает контакты,
оценивает релевантность и готовит персонализированное первое сообщение.
```

**Не позиционировать как:** "скрапер сайтов" — это дешевле и уже, чем реальная ценность продукта.

---

## РАЗДЕЛ 2 — Почему нужен AI, а не только парсер

| Ограничение парсера | Что решает AI |
|---------------------|---------------|
| Разная структура у каждого сайта | AI читает смысл, а не CSS-селекторы |
| Не понимает, чем занимается компания | AI определяет нишу и ICP-fit |
| Не видит "боль" клиента | AI выявляет слабые места сайта |
| Не умеет писать письма | AI генерирует персонализированный outreach |
| Контакты скрыты в JS или формах | AI ищет косвенные признаки (TG, VK, WhatsApp) |

**Ключевой принцип:** AI нужен не вместо парсинга, а как слой понимания поверх него.
Сначала дешёвое детерминированное извлечение — потом AI только там, где он добавляет ценность.

---

## РАЗДЕЛ 3 — Архитектура pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│  User Input                                                      │
│  "Найди стоматологии в Екб со слабым сайтом"                    │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1 — Query Generator                                        │
│  Модель: Haiku 4.5 / GPT-5.4 Mini                               │
│  Вход: 1 запрос пользователя                                     │
│  Выход: 5–15 поисковых вариантов + negative keywords            │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│  STEP 2 — Search Module                                          │
│  API: SerpAPI / Yandex Search API                               │
│  Выход: ~200 URL                                                 │
│  Cache TTL: 7 дней (ключ: hash(query + region))                 │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│  STEP 3 — URL Filter (детерминированный, бесплатно)             │
│  regex по паттернам: /blog/, /news/, /tag/, hh.ru, avito.ru…    │
│  title-маркеры: "ТОП-10", "Рейтинг", "Лучшие"                  │
│  Выход: ~80–100 URL                                              │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│  STEP 4 — URL Classifier (LLM, только border cases)             │
│  Модель: Haiku 4.5                                               │
│  Вход: title + URL                                               │
│  Выход: company_homepage | contacts | services | garbage        │
│  Запускается только если детерминированный слой не уверен       │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│  STEP 5 — Cache Check                                            │
│  Проверяем Redis / Supabase: есть ли уже готовый лид для домена │
│  Cache TTL HTML: 30 дней                                         │
│  Cache TTL AI lead: 14 дней                                      │
│  HIT → пропускаем шаги 6–8, идём сразу в Scoring               │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│  STEP 6 — Crawler                                                │
│  Rate-limited, прокси, rotating UA                               │
│  Лимиты: Free=2, Starter=3, Pro=5, Agency=7, Max=10 стр         │
│  Приоритет: /, /about, /contacts, /services, /price             │
│  Timeout: 15 сек / страница                                      │
│  Cache HTML: 30 дней                                             │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│  STEP 7 — Basic HTML Extraction (детерминированный, бесплатно)  │
│  Извлекает: email, phone, title, h1–h3, meta description,       │
│  schema.org, address, social links, WhatsApp/TG/VK ссылки       │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│  STEP 8 — Light AI (если тариф это позволяет)                   │
│  Модель: GLM-4.7-Flash / Gemini Flash-Lite / Haiku 4.5         │
│  Задача: ниша, релевантность, базовый score, "годится или нет"  │
│  Стоимость: 1 AI credit                                          │
│  Применяется по лимитам Free/Starter/Pro/Agency/Max             │
└────────────────────┬────────────────────────────────────────────┘
                     ↓ (только top leads после Light AI)
┌─────────────────────────────────────────────────────────────────┐
│  STEP 9 — Deep AI Extraction                                     │
│  Модель: Claude Sonnet 4.6 / GPT-5.4                            │
│  Задача: полная JSON Schema лида, pain points, website_quality  │
│  Стоимость: 5 AI credits                                         │
│  Лимит: Pro=150, Agency=400, Max=800 лидов/мес                 │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│  STEP 10 — Validation                                            │
│  Детерминированно: валидность email, телефона, confidence > 0.5 │
│  Блокирует дубли (hash домена)                                   │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│  STEP 11 — Lead Scoring                                          │
│  Модель: Sonnet 4.6 (Deep AI leads) / Haiku (Light AI leads)   │
│  Выход: score 0–100, priority (low/medium/high), reason         │
└────────────────────┬────────────────────────────────────────────┘
                     ↓ (только для лидов с deep AI)
┌─────────────────────────────────────────────────────────────────┐
│  STEP 12 — Outreach Generation                                   │
│  Модель: Sonnet 4.6 / GPT-5.4; premium: GLM-5 по routing       │
│  Выход: email_subject, email_body, telegram_message             │
│  Стоимость: 3 AI credits                                         │
│  Регенерации: Free=0, Starter=0, Pro=1, Agency=2, Max=3        │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│  STEP 13 — Export                                                │
│  Форматы: CSV, XLSX, Google Sheets, Webhook, CRM (по тарифу)   │
│  Параллельно: Observability log → Postgres                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## РАЗДЕЛ 4 — Модули: детальное описание

### 4.1 Query Generator

**Задача:** развернуть один запрос пользователя в 5–15 поисковых вариантов.

**Входной формат:**
```typescript
interface QueryInput {
  niche: string;           // "стоматология"
  city: string;            // "Екатеринбург"
  service_offered: string; // "разработка сайтов и SEO"
  icp_notes?: string;      // опционально
}
```

**Выходной формат:**
```typescript
interface QueryOutput {
  queries: Array<{
    query: string;
    intent: "company_homepage" | "contacts_page" | "services_page" | "price_page";
    priority: "high" | "medium" | "low";
  }>;
  negative_keywords: string[];
  expected_results_per_query: number;
}
```

**Пример выхода для "стоматологии Екатеринбург":**
```json
{
  "queries": [
    { "query": "стоматология Екатеринбург официальный сайт", "intent": "company_homepage", "priority": "high" },
    { "query": "частная стоматологическая клиника Екатеринбург контакты", "intent": "contacts_page", "priority": "high" },
    { "query": "стоматологическая клиника Екатеринбург услуги цены", "intent": "price_page", "priority": "medium" },
    { "query": "зубная клиника Екатеринбург запись онлайн", "intent": "company_homepage", "priority": "medium" }
  ],
  "negative_keywords": ["вакансии", "форум", "отзывы", "рейтинг лучших", "статья", "ТОП"],
  "expected_results_per_query": 20
}
```

---

### 4.2 URL Filter

**Детерминированные правила (реализовывать первыми — без LLM):**

```typescript
const BLOCKED_DOMAINS = [
  "avito.ru", "hh.ru", "vc.ru", "habr.com", "yandex.ru/maps",
  "2gis.ru", "wildberries.ru", "ozon.ru", "zoon.ru", "otzovik.com",
  "prodoctorov.ru", "yell.ru", "flamp.ru", "tripadvisor.com"
];

const BLOCKED_URL_PATTERNS = [
  /\/blog\//i, /\/news\//i, /\/tag\//i, /\/category\//i,
  /\/vakansii\//i, /\/jobs\//i, /\/career\//i,
  /\/privacy/i, /\/terms/i, /\/politika/i,
  /\?utm_/i, /\/page\/\d+/i, /\.pdf$/i
];

const BLOCKED_TITLE_KEYWORDS = [
  "топ-", "рейтинг", "лучшие", "список", "обзор", "сравнение",
  "как выбрать", "что такое", "статья"
];
```

**LLM-классификатор (только для border cases):**

```typescript
interface URLClassification {
  page_type: "company_homepage" | "contacts" | "services" | "aggregator" | "article" | "catalog" | "other";
  is_target_company_site: boolean;
  confidence: number; // 0..1
}
```
Запускать только если детерминированные правила возвращают `uncertain`.

---

### 4.3 Crawler

```typescript
interface CrawlerConfig {
  max_pages: number;       // Free=2, Starter=3, Pro=5, Agency=7, Max=10
  max_depth: number;       // 2
  timeout_ms: number;      // 15000
  delay_between_requests_ms: [number, number]; // [1000, 3000] рандом
  max_concurrent_per_domain: number; // 1
  respect_robots_txt: boolean; // true (обязательно)
  user_agent_rotation: boolean; // true (обязательно)
  proxy_enabled: boolean;  // true для защищённых сайтов
}

const PRIORITY_PATHS = [
  "/", "/about", "/o-kompanii", "/o-nas",
  "/services", "/uslugi",
  "/contacts", "/kontakty",
  "/price", "/prices", "/prays", "/stoimost",
  "/portfolio", "/cases"
];

const SKIP_PATHS = [
  "/blog", "/news", "/novosti",
  "/privacy", "/politika", "/terms",
  "/cart", "/login", "/register", "/cabinet"
];
```

---

### 4.4 Basic HTML Extraction

Запускать **до** LLM. Бесплатно. Достаёт:

```typescript
interface BasicExtraction {
  title: string | null;
  meta_description: string | null;
  h1: string[];
  h2: string[];
  emails: string[];
  phones: string[];
  address: string | null;
  social_links: {
    vk: string | null;
    telegram: string | null;
    whatsapp: string | null;
    instagram: string | null;
    youtube: string | null;
  };
  has_contact_form: boolean;
  schema_org: Record<string, unknown> | null;
  visible_text_snippet: string; // первые 2000 символов видимого текста
}
```

---

### 4.5 AI Extraction Levels

#### Light AI (1 credit)

**Модель:** GLM-4.7-Flash / Gemini 2.5 Flash-Lite / DeepSeek V3 / Claude Haiku 4.5 по тарифу.

**Промпт-ответственность:** короткий, строгий JSON, не писать длинных объяснений.

```typescript
interface LightAIOutput {
  industry: string | null;
  city: string | null;
  is_commercial: boolean;
  is_relevant_to_icp: boolean;
  relevance_score: number; // 0..100
  pass_to_deep_ai: boolean; // главное поле: идти дальше или нет
}
```

#### Deep AI (5 credits)

**Модель:** Claude Sonnet 4.6 / GPT-5.4

**Задача:** полная JSON Schema лида (раздел 5).

#### Premium AI (15 credits)

**Модель:** GLM-5 / Claude Sonnet 4.6 / GPT-5.4 по premium routing. Claude Opus не фиксировать как обязательный вариант, если экономика не сходится.

**Только для Max-тарифа.** Несколько проходов по сайту, расширенный анализ, 3 варианта outreach, аргументация для менеджера.

---

## РАЗДЕЛ 5 — JSON Schema лида (canonical)

Это **единственная** допустимая схема объекта лида в БД и в API-ответах. Не менять без обновления этого файла.

```typescript
interface Lead {
  // Идентификация
  id: string;                    // uuid v4
  domain: string;                // нормализованный домен без www
  website: string;               // полный URL
  created_at: string;            // ISO 8601
  updated_at: string;
  user_id: string;               // кто запросил
  campaign_id: string | null;

  // Основные данные
  company_name: string | null;
  city: string | null;
  region: string | null;
  address: string | null;
  industry: string | null;
  description: string | null;    // краткое описание бизнеса, 1–2 предложения
  services: string[];

  // Контакты
  phone: string | null;
  email: string | null;
  telegram: string | null;
  whatsapp: string | null;
  vk: string | null;
  instagram: string | null;
  has_contact_form: boolean;

  // Лицо принимающее решение
  decision_maker: {
    name: string | null;
    role: string | null;
    source_url: string | null;
  };

  // Качество сайта (заполняет Deep AI)
  website_quality: {
    has_modern_design: boolean | null;
    has_mobile_adaptation: boolean | null;
    has_clear_cta: boolean | null;
    has_online_booking: boolean | null;
    has_outdated_content: boolean | null;
    seo_visible: boolean | null;   // есть ли meta, заголовки
    comments: string | null;
  };

  // AI-оценка
  lead_fit: {
    score: number;                 // 0–100
    reason: string;
    priority: "low" | "medium" | "high";
  };
  pain_points: string[];
  reason_to_contact: string | null;

  // Outreach (заполняется отдельным job'ом)
  personalized_outreach: {
    email_subject: string | null;
    email_body: string | null;
    telegram_message: string | null;
    regeneration_count: number;    // сколько раз перегенерировали
  };

  // Метаданные обработки
  processing: {
    ai_level: "basic" | "light" | "deep" | "premium";
    sources: string[];             // URL-источники, откуда брали данные
    confidence: number;            // 0..1
    cache_hit: boolean;
    cost_usd: number;              // реальная стоимость обработки этого лида
  };
}
```

**Правило hallucination prevention:** если данных нет на сайте — `null`. Никогда не выдумывать email, телефон, имя. Все важные поля должны иметь `source_url`.

---

## РАЗДЕЛ 6 — Примеры промптов для агентов

### Промпт для Query Generator

```
Ты генератор поисковых запросов для B2B лидогенерации.

Пользователь хочет найти потенциальных клиентов.
Ниша: {niche}
Город: {city}
Услуга, которую продаёт пользователь: {service_offered}

Сгенерируй 5–10 поисковых запросов для Google/Yandex.
Каждый запрос должен находить ОФИЦИАЛЬНЫЕ САЙТЫ компаний, а не агрегаторы, статьи или каталоги.
Добавь список negative keywords.

Отвечай строго в JSON. Никакого текста до или после JSON.

Формат:
{
  "queries": [{"query": "...", "intent": "company_homepage|contacts_page|services_page|price_page", "priority": "high|medium|low"}],
  "negative_keywords": ["..."],
  "expected_results_per_query": 20
}
```

### Промпт для Light AI

```
Ты классификатор B2B-лидов. Отвечай только JSON.

Данные со страницы:
Title: {title}
Description: {meta_description}
H1: {h1}
Текст: {visible_text_snippet}
Контакты найдены: email={email}, phone={phone}

ICP пользователя: {icp_description}
Город поиска: {city}

Задача: определи, стоит ли этот лид глубокого анализа.

Отвечай строго в JSON:
{
  "industry": "...",
  "city": "..." | null,
  "is_commercial": true|false,
  "is_relevant_to_icp": true|false,
  "relevance_score": 0-100,
  "pass_to_deep_ai": true|false
}

Правило: pass_to_deep_ai = true только если relevance_score >= 60 и is_commercial = true.
```

### Промпт для Deep AI Extraction

```
Ты анализируешь сайт компании как B2B-специалист.
Пользователь продаёт: {service_offered}

Данные сайта:
{scraped_pages_combined_text}

Основные контакты (найдены парсером):
email: {email}, phone: {phone}, telegram: {telegram}

Задача: заполни структуру лида. Все данные только из предоставленного текста.
Если данных нет — пиши null. НЕ ВЫДУМЫВАЙ.

Отвечай строго в JSON по схеме LeadSchema. Никакого текста вне JSON.
```

### Промпт для Outreach Generation

```
Ты пишешь первое холодное сообщение от лица специалиста.

Специалист продаёт: {service_offered}
Данные компании:
- Название: {company_name}
- Ниша: {industry}
- Описание: {description}
- Слабые места сайта: {pain_points}
- Повод для контакта: {reason_to_contact}

Правила:
1. Опирайся ТОЛЬКО на факты из данных выше.
2. Не утверждай то, чего не знаешь.
3. Не пиши "Я вижу, что вы теряете клиентов" — только наблюдения.
4. Email: тема + тело, не более 120 слов.
5. Telegram: не более 60 слов.

Отвечай строго в JSON:
{
  "email_subject": "...",
  "email_body": "...",
  "telegram_message": "..."
}
```

---

## РАЗДЕЛ 7 — Тарифная логика, AI Credits и Unit-экономика

> Версия 3.1. Пересобранная тарифная сетка с реальным расчётом маржи.
> Цены моделей актуальны на май 2026.

---

### 7.1 Принцип: почему старые тарифы не работали

Старая ошибка: `ai_analyzed_leads = leads_per_month`.

При себестоимости ~4₽/лид на Sonnet и тарифе 4990₽/1000 лидов — маржа падала до 16%.
Для SaaS нужно минимум 50–60%.

**Правильная модель:**
```
Много лидов → Basic Scraping        (дёшево, все лиды)
                    ↓
              Light AI               (дёшево, все лиды)
                    ↓
              Deep AI                (дорого, только топ)
                    ↓
              Outreach               (дорого, только топ)
```

Вторая ошибка — почти семикратный разрыв между начальным и следующим тарифом.
Пользователь попробовал начальный тариф, хочет больше — и сразу видит слишком высокий скачок. Уходит.

**Новая сетка:**

| Тариф | Цена | Кому |
|-------|------|------|
| Free | 0₽ | попробовать, 20 лидов |
| Starter | 990₽ | фрилансер, первые клиенты |
| Pro | 2990₽ | агентство, регулярная работа |
| Agency | 7990₽ | команда, много ниш |
| Max | 19990₽ | enterprise, по запросу |

Разрывы: 3x, 2.7x, 2.7x — равномерные, психологически комфортные.

---

### 7.2 Таблица моделей и реальные цены (май 2026)

#### Платные модели

| Модель | Input $/1M | Output $/1M | $/1M × 95 ₽ (input) | Для чего в pipeline |
|--------|-----------|-------------|----------------------|---------------------|
| Claude Haiku 4.5 | $1.00 | $5.00 | 95 ₽ | классификация, query gen |
| Claude Sonnet 4.6 | $3.00 | $15.00 | 285 ₽ | deep extraction, outreach |
| GPT-5.4 | $2.50 | $15.00 | 237 ₽ | альтернатива Sonnet |
| GPT-5.4 Mini | $0.75 | $4.50 | 71 ₽ | альтернатива Haiku |
| GPT-5.4 Nano | $0.20 | $1.25 | 19 ₽ | сверхбюджет |
| GLM-4.7 | уточнить у провайдера | уточнить у провайдера | — | основной рабочий конь |
| GLM-5 | уточнить у провайдера | уточнить у провайдера | — | premium-анализ и рассуждение |
| DeepSeek V3 | $0.27 | $1.10 | 25 ₽ | Starter/budget, рус. язык |
| Gemini 2.5 Flash | $0.30 | $2.50 | 28 ₽ | лёгкие задачи |
| Gemini 2.5 Flash-Lite | $0.10 | $0.40 | 9.5 ₽ | самая дешёвая платная |
| Groq Llama 3.3 70B | $0.59 | $0.79 | 56 ₽ | скорость + дёшево |
| Groq Llama 3.1 8B | $0.05 | $0.08 | 4.75 ₽ | микроклассификация |

#### Бесплатные уровни (важная оговорка)

| Провайдер / Модель | Бесплатный лимит | Ограничение | Подходит для |
|--------------------|-----------------|-------------|--------------|
| **Groq — Llama 3.3 70B** | 1000 req/day, 30 RPM | данные могут логироваться | MVP, тест |
| **Groq — Llama 3.1 8B** | 14400 req/day, 30 RPM | данные могут логироваться | MVP, тест |
| **GLM-4.7-Flash** | free tier при наличии ключей | не опираться в платном production-routing | MVP, классификация |
| **Gemini 2.5 Flash** | 1500 req/day, 15 RPM, 1M TPM | данные идут на обучение Google | MVP, тест |
| **Gemini 2.5 Flash-Lite** | 1500 req/day, 15 RPM | данные идут на обучение Google | MVP, тест |

**⚠️ Критично для продакшена:**
- Бесплатные уровни Groq и Gemini **используют твои запросы для обучения моделей**.
- Для Free-тарифа твоего продукта (где пользователи ищут реальных клиентов) — это **приемлемо**: данные не конфиденциальные, это публичные сайты.
- Для платных тарифов — только платные API, без бесплатных уровней.

**Скидки на платных уровнях:**
- **Batch API** (Anthropic, OpenAI, Gemini, Groq): −50%, задачи обрабатываются за 24ч
- **Prompt caching**: −90% на повторяющийся input (системные промпты, схемы)
- Реальная экономия с обоими: −35–45% от базовой цены

---

### 7.3 Себестоимость обработки 1 лида по сценариям

**Базовая декомпозиция токенов на один лид:**

| Этап | Input токенов | Output токенов |
|------|--------------|----------------|
| URL Classifier (border cases) | 300 | 50 |
| Light AI | 1500 | 200 |
| Deep AI Extraction | 4000 | 1000 |
| Lead Scoring | 1500 | 300 |
| Outreach (1 вар.) | 1500 | 500 |
| **Всего Deep pipeline** | **~8800** | **~2050** |
| **Только Light pipeline** | **~1800** | **~250** |

---

#### Сценарий A — Free tier: Groq + Gemini Flash бесплатно

Используется только для Free-тарифа продукта (20 лидов/мес).

| Этап | Модель | Стоимость |
|------|--------|-----------|
| Query Gen | Groq Llama 8B (free) | $0 |
| URL Classifier | Groq Llama 8B (free) | $0 |
| Light AI | Gemini 2.5 Flash (free) | $0 |
| Deep AI | ❌ недоступно | — |
| Outreach | шаблонное | $0 |
| **Итого LLM/лид** | | **$0** |

Ограничение: 1500 req/day у Gemini. На 20 лидов в месяц — хватает с запасом.

**Реальная себестоимость Free-тарифа (20 лидов/мес):**

| Статья | Стоимость |
|--------|-----------|
| LLM | 0 ₽ |
| Search API (10 запросов) | ~10 ₽ |
| Прокси | ~20 ₽ |
| Supabase + Vercel (free tiers инфра) | 0 ₽ |
| **Итого** | **~30 ₽** |

Маржа: **~97%** ✅ (пока пользователь не превысит бесплатные лимиты провайдеров)

---

#### Сценарий B — Starter: DeepSeek + Gemini Flash-Lite

Для Starter-тарифа (990₽/мес, 200 лидов).

| Этап | Модель | Input $/1M | Output $/1M |
|------|--------|-----------|-------------|
| Query Gen | Gemini Flash-Lite | $0.10 | $0.40 |
| URL Classifier | Gemini Flash-Lite | $0.10 | $0.40 |
| Light AI | DeepSeek V3 | $0.27 | $1.10 |
| Deep AI | ❌ нет | — | — |
| Outreach | шаблонное | — | — |

**Расчёт на 1 лид (light pipeline, ~1800 input + 250 output):**
- Input: 1800 × $0.27 / 1M = $0.000486
- Output: 250 × $1.10 / 1M = $0.000275
- **Итого LLM: $0.00076/лид ≈ 0.07 ₽/лид**

**Реальная себестоимость Starter (200 лидов/мес):**

| Статья | Стоимость |
|--------|-----------|
| LLM (200 лидов) | ~14 ₽ |
| Search API (~50 запросов) | ~47 ₽ |
| Прокси (~1 GB) | ~95 ₽ |
| Supabase + Vercel | ~150 ₽ |
| **Итого** | **~306 ₽** |

Маржа: **(990 − 306) / 990 = ~69%** ✅

---

#### Сценарий C — Pro: Haiku + Sonnet (smart routing)

Для Pro-тарифа (2990₽/мес, 500 лидов, 150 deep AI).

| Этап | Модель | $/лид |
|------|--------|-------|
| Query Gen | Haiku 4.5 | $0.0001 |
| URL Classifier | Haiku 4.5 | $0.0003 |
| Light AI (500 лидов) | Haiku 4.5 | $0.0018 |
| Deep AI (150 лидов) | Sonnet 4.6 + caching | $0.034 |
| Outreach (150 лидов) | Sonnet 4.6 + caching | $0.009 |

**Расчёт совокупно на 500 лидов:**
- 500 × light (Haiku): 500 × $0.0022 = $1.10
- 150 × deep + outreach (Sonnet, ~40% caching): 150 × $0.043 = $6.45
- **Итого LLM: $7.55 ≈ 717 ₽**

**Реальная себестоимость Pro (500 лидов/мес):**

| Статья | Стоимость |
|--------|-----------|
| LLM | ~717 ₽ |
| Search API (~100 запросов) | ~95 ₽ |
| Прокси (~3 GB) | ~285 ₽ |
| Supabase + Vercel | ~200 ₽ |
| **Итого** | **~1297 ₽** |

Маржа: **(2990 − 1297) / 2990 = ~57%** ✅

---

#### Сценарий D — Agency: Sonnet основной

Для Agency-тарифа (7990₽/мес, 1500 лидов, 400 deep AI).

**Расчёт совокупно на 1500 лидов:**
- 1500 × light (Haiku): 1500 × $0.0022 = $3.30
- 400 × deep + outreach (Sonnet + caching): 400 × $0.043 = $17.20
- **Итого LLM: $20.50 ≈ 1948 ₽**

**Реальная себестоимость Agency (1500 лидов/мес):**

| Статья | Стоимость |
|--------|-----------|
| LLM | ~1948 ₽ |
| Search API (~300 запросов) | ~285 ₽ |
| Прокси (~8 GB) | ~760 ₽ |
| Supabase + Vercel | ~400 ₽ |
| **Итого** | **~3393 ₽** |

Маржа: **(7990 − 3393) / 7990 = ~57%** ✅

---

#### Сценарий E — Max: Sonnet + premium routing

Для Max-тарифа (19990₽/мес, 3000 лидов, 800 deep AI, 150 premium AI).

**Расчёт совокупно на 3000 лидов:**
- 3000 × light (Haiku): $6.60
- 800 × deep + outreach (Sonnet + caching): $34.40
- 150 × premium (GLM-5 / GPT-5.4 / Sonnet 4.6 по routing): ориентир $37.50
- **Итого LLM: $78.50 ≈ 7458 ₽**

**Реальная себестоимость Max (3000 лидов/мес):**

| Статья | Стоимость |
|--------|-----------|
| LLM | ~7458 ₽ |
| Search API (~500 запросов) | ~475 ₽ |
| Прокси (~15 GB) | ~1425 ₽ |
| Supabase + Vercel | ~600 ₽ |
| **Итого** | **~9958 ₽** |

Маржа: **(19990 − 9958) / 19990 = ~50%** ✅ (до ~60% с оптимизацией batch + caching)

---

### 7.4 Сводная таблица тарифов

| Тариф | Цена/мес | Лидов | Deep AI | Себестоимость | Маржа |
|-------|----------|-------|---------|---------------|-------|
| Free | 0₽ | 20 | 0 | ~30₽ | — |
| Starter | 990₽ | 200 | 0 | ~306₽ | **~69%** |
| Pro | 2990₽ | 500 | 150 | ~1297₽ | **~57%** |
| Agency | 7990₽ | 1500 | 400 | ~3393₽ | **~57%** |
| Max | 19990₽ | 3000 | 800 + 150 premium | ~9958₽ | **~50%** |

---

### 7.5 Финальные конфиги тарифов

#### Free

```yaml
price_per_month: 0₽
leads_per_month: 20
search_queries_per_month: 5
ai_credits: 20

llm_routing:
  query_gen: groq-llama-3.1-8b      # бесплатный уровень
  url_classify: groq-llama-3.1-8b
  light_ai: gemini-2.5-flash         # бесплатный уровень
  deep_ai: disabled
  outreach: template_only

max_pages_per_site: 2
export: [csv]
monitoring: false
message_regenerations: 0
note: "данные на бесплатных LLM могут использоваться для обучения моделей"
```

---

#### Starter — 990₽/мес

```yaml
price_per_month: 990₽
leads_per_month: 200
search_queries_per_month: 50
ai_credits: 200

processing:
  basic_scraping: 200
  light_ai: 200          # 200 credits (DeepSeek V3)
  deep_ai: 0
  premium_ai: 0

llm_routing:
  query_gen: gemini-2.5-flash-lite   # платный, дёшево
  url_classify: gemini-2.5-flash-lite
  light_ai: deepseek-v3
  deep_ai: disabled
  outreach: template_only

personalized_messages: 0
message_regenerations: 0
max_pages_per_site: 3
export: [csv]
monitoring: false
crm_integrations: false
```

---

#### Pro — 2990₽/мес

```yaml
price_per_month: 2990₽
leads_per_month: 500
search_queries_per_month: 100
ai_credits: 800

processing:
  basic_scraping: 500
  light_ai: 500          # 500 credits (Haiku 4.5)
  deep_ai: up_to_150     # 750 credits max (Sonnet 4.6)
  premium_ai: 0

llm_routing:
  query_gen: claude-haiku-4-5
  url_classify: claude-haiku-4-5
  light_ai: claude-haiku-4-5
  deep_ai: claude-sonnet-4-6
  outreach: claude-sonnet-4-6

personalized_messages: 150
message_regenerations: 1
max_pages_per_site: 5
export: [csv, xlsx, google_sheets]
monitoring:
  enabled: true
  tracked_companies: 10
crm_integrations: false
webhook: false
```

---

#### Agency — 7990₽/мес

```yaml
price_per_month: 7990₽
leads_per_month: 1500
search_queries_per_month: 300
ai_credits: 2500

processing:
  basic_scraping: 1500
  light_ai: 1500         # 1500 credits (Haiku 4.5)
  deep_ai: up_to_400     # 2000 credits max (Sonnet 4.6)
  premium_ai: 0

llm_routing:
  query_gen: claude-haiku-4-5
  url_classify: claude-haiku-4-5
  light_ai: claude-haiku-4-5
  deep_ai: claude-sonnet-4-6
  outreach: claude-sonnet-4-6

personalized_messages: 400
message_regenerations: 2
max_pages_per_site: 7

export: [csv, xlsx, google_sheets, webhook]
monitoring:
  enabled: true
  tracked_companies: 50
crm_integrations: limited
```

---

#### Max — 19990₽/мес

```yaml
price_per_month: 19990₽
leads_per_month: 3000
search_queries_per_month: 500
ai_credits: 6000

processing:
  basic_scraping: 3000
  light_ai: 3000         # 3000 credits (Haiku 4.5)
  deep_ai: up_to_800     # 4000 credits max (Sonnet 4.6)
  premium_ai: up_to_150  # 2250 credits max (GLM-5 / Sonnet 4.6 / GPT-5.4)

llm_routing:
  query_gen: claude-haiku-4-5
  url_classify: claude-haiku-4-5
  light_ai: claude-haiku-4-5
  deep_ai: claude-sonnet-4-6
  outreach: claude-sonnet-4-6
  premium_outreach: glm-5 | claude-sonnet-4-6 | gpt-5-4

personalized_messages: 800
premium_messages: 150
message_regenerations: 3
max_pages_per_site: 10

export: [csv, xlsx, google_sheets, webhook, crm]
monitoring:
  enabled: true
  tracked_companies: 100
crm_integrations: true
ai_agent_mode: true
```

---

### 7.6 AI Credits — стоимость операций

```typescript
const AI_CREDIT_COSTS = {
  light_ai_analysis: 1,       // Haiku
  deep_ai_analysis: 5,        // Sonnet
  premium_ai_analysis: 15,    // GLM-5 / Sonnet / GPT-5.4 по routing
  outreach_generation: 3,     // Sonnet
  outreach_regeneration: 3,   // каждая перегенерация = те же кредиты
  monitoring_signal: 2,       // Sonnet
};
```

---

### 7.7 Paid Add-ons

```typescript
const ADD_ONS = {
  extra_ai_credits: {
    pack_500:   490,    // ₽
    pack_2000:  1490,
    pack_6000:  3990,
  },
  extra_leads: {
    pack_200:   490,
    pack_1000:  1990,
    pack_5000:  6990,
  },
  extra_monitoring: {
    companies_50:  990,   // ₽/мес
    companies_200: 2990,
  },
  extra_integrations: {
    webhook:         490,  // ₽/мес
    crm_integration: 1990,
  },
  extra_pages_per_site: {
    plus_5_pages: 490,    // ₽/мес add-on к любому тарифу
  },
};
```

---

### 7.8 Формулировки для лендинга

**Не писать:**
```
Pro — 500 AI-лидов за 2990₽
```

**Писать:**
```
Starter — 200 компаний с контактами. Light AI без глубокого анализа. Для первого теста.
Pro     — 500 компаний, AI оценивает каждую, 150 персональных сообщений.
Agency  — 1500 компаний, 400 глубоких AI-анализов, мониторинг 50 компаний.
Max     — 3000 компаний, полный AI-цикл, Premium-анализ, CRM-интеграции.
```

**Что показывать в интерфейсе (вместо одного "AI analyzed"):**

```
Собрано компаний:           500
Прошло базовую обработку:   500
AI-классифицировано:        500
Глубоко проанализировано:   143 / 150
Сообщений создано:          143 / 150
Осталось AI credits:        218 / 800
```

---

### 7.9 Anti-loss правила (обязательны к реализации)

```typescript
const ANTI_LOSS_RULES = {
  deep_ai_requires_light_ai_pass: true,     // нет deep без light
  light_ai_min_score_for_deep: 60,          // минимальный score для deep AI
  deduplicate_by_domain: true,              // дубли не тратят кредиты
  skip_if_not_commercial: true,             // некоммерческие сайты — пропуск
  outreach_requires_deep_ai: true,          // нет outreach без deep
  outreach_min_score: 50,                   // нет outreach для слабых лидов
  check_credits_before_any_llm_call: true,  // кредиты до вызова
  enforce_max_pages_per_site: true,         // по тарифу
  check_cache_before_crawl: true,           // кэш обязателен
  max_retry_attempts: 3,                    // не бесконечные ретраи
  no_free_provider_for_paid_tiers: true,    // Groq/Gemini/GLM free tiers только для Free/MVP
};
```
## РАЗДЕЛ 8 — Smart Routing моделей

**Правило:** не использовать дорогую модель там, где хватает дешёвой. В разработке и MVP можно использовать free/дешёвые модели, но production-routing платных тарифов не должен опираться на free tiers.

```typescript
type TaskType =
  | "query_generation"
  | "url_classification"
  | "light_ai_extraction"
  | "deep_ai_extraction"
  | "premium_ai_extraction"
  | "lead_scoring_light"
  | "lead_scoring_deep"
  | "outreach_generation"
  | "outreach_premium";

const MODEL_ROUTING_PRODUCTION: Record<TaskType, string[]> = {
  query_generation:        ["glm-4-7", "claude-haiku-4-5", "gpt-5-4"],
  url_classification:      ["gemini-2-5-flash-lite", "glm-4-7-flash", "deepseek-v3"],
  light_ai_extraction:     ["glm-4-7", "claude-haiku-4-5", "deepseek-v3"],
  deep_ai_extraction:      ["claude-sonnet-4-6", "glm-4-7", "gpt-5-4"],
  premium_ai_extraction:   ["glm-5", "claude-sonnet-4-6", "gpt-5-4"],
  lead_scoring_light:      ["glm-4-7-flash", "gemini-2-5-flash-lite"],
  lead_scoring_deep:       ["claude-sonnet-4-6", "glm-4-7"],
  outreach_generation:     ["claude-sonnet-4-6", "gpt-5-4"],
  outreach_premium:        ["glm-5", "claude-sonnet-4-6", "gpt-5-4"],
};

const MODEL_ROUTING_DEVELOPMENT: Partial<Record<TaskType, string[]>> = {
  query_generation:        ["groq-llama-3-3-70b", "available-free-model"],
  url_classification:      ["glm-4-7-flash", "groq-llama-3-1-8b", "gemini-free"],
  light_ai_extraction:     ["deepseek-v3", "glm-4-7-flash", "gemini-free"],
};
```

**Матрица моделей (май 2026):**

| Модель | Роль |
|--------|------|
| GLM-4.7-Flash | free/MVP, классификация и простые задачи |
| GLM-4.7 | основной рабочий конь для paid routing |
| GLM-5 | premium-анализ и сложное рассуждение |
| Gemini 2.5 Flash-Lite | дешёвая классификация |
| DeepSeek V3 | экономный вариант для Starter/budget |
| Claude Haiku 4.5 | быстрая обработка и query/classification |
| Claude Sonnet 4.6 | основной сильный тариф для deep/outreach |
| GPT-5.4 | быстрое обслуживание и premium fallback |
| Groq Llama 3.3 70B | быстрый чат/real-time/MVP |

**Routing defaults по тарифам:**

| Контекст | Routing |
|----------|---------|
| Development / MVP | Chat: Groq Llama 3.3 70B или доступная free-модель. Classification: GLM-4.7-Flash / Groq 8B / Gemini free при наличии ключей. Enrichment preview: дешёвые/free модели без обещаний production-качества. |
| Free product tier | Free tiers допустимы, потому что данные в основном публичные. Deep/premium анализ недоступен, это нужно явно показывать в UI/документации. |
| Starter | Gemini Flash-Lite / DeepSeek V3 / GLM-4.7-Flash. Без deep AI и без premium. |
| Pro | Light AI для всех лидов, Deep AI только для top leads. Основные кандидаты: GLM-4.7, Claude Haiku 4.5, Claude Sonnet 4.6. |
| Agency | Pipeline как Pro, но больше лимиты. Deep AI на большем числе top leads. |
| Max | Light AI для всех, Deep AI для top leads, Premium AI для лучших. Premium-модели: GLM-5, Claude Sonnet 4.6, GPT-5.4. Claude Opus не фиксировать как обязательный, если он дорогой. |

**Скидки:**
- **Batch API:** −50% для scoring и query generation (не real-time задачи)
- **Prompt caching:** −90% на повторяющиеся input части (системные промпты, схемы)
- С caching + batch: реальная экономия 30–40% от базовых цен

---

## РАЗДЕЛ 9 — Cache Layer

```typescript
interface CacheConfig {
  // Search results
  search_results: {
    ttl_days: 7;
    key: (query: string, region: string) => string; // sha256(query+region)
    store: "redis";
  };

  // Raw HTML
  page_html: {
    ttl_days: 30;
    key: (url: string) => string; // sha256(url)
    store: "supabase_storage";    // S3-compatible, дешевле Redis
    invalidate_on: "content_hash_change";
  };

  // Basic extraction result
  basic_extraction: {
    ttl_days: 30;
    key: (domain: string) => string;
    store: "postgres";
  };

  // AI-extracted lead
  ai_lead: {
    ttl_days: 14;
    key: (domain: string, schema_version: string) => string;
    store: "postgres";
    invalidate_on: "content_hash_change";
  };

  // Outreach — НЕ кэшируется (всегда персонально под отправителя)
}
```

**Поля для инвалидации кэша в БД:**

```sql
ALTER TABLE leads ADD COLUMN content_hash TEXT;
ALTER TABLE leads ADD COLUMN last_scraped_at TIMESTAMPTZ;
ALTER TABLE leads ADD COLUMN last_ai_analysis_at TIMESTAMPTZ;
ALTER TABLE leads ADD COLUMN cache_valid BOOLEAN DEFAULT TRUE;
```

---

## РАЗДЕЛ 10 — Rate Limiting и Proxy

### Обязательно с первого дня (не "потом")

```typescript
interface CrawlerSafety {
  // Rotating User-Agent — пул из 20+ реальных UA
  user_agents: string[];

  // Задержки
  delay_between_requests: {
    same_domain_ms: [1000, 3000]; // рандом в диапазоне
    different_domain_ms: [200, 800];
  };

  // Параллелизм
  max_concurrent_per_domain: 1;
  max_concurrent_total: 10;

  // Robots
  respect_robots_txt: true;

  // Прокси
  proxy: {
    datacenter: string[];   // $0.5–1/GB, для большинства сайтов
    residential: string[];  // $5–15/GB, для Cloudflare-защищённых
  };
}

// Бюджет на прокси: ~$30–80/мес на каждые 10k анализируемых сайтов
```

### Что оставить на потом

- JS-challenge solving (Cloudflare Turnstile)
- Playwright stealth mode
- CAPTCHA solvers

---

## РАЗДЕЛ 11 — Observability: логирование каждого лида

**Обязательно реализовать с первого дня.** Без этого не видно, где сжигаются деньги.

```typescript
interface LeadProcessingLog {
  // Идентификация
  log_id: string;
  lead_id: string;
  user_id: string;
  campaign_id: string | null;
  created_at: string;

  // Что искали
  search_query_original: string;
  search_queries_generated: string[];  // сколько вариантов сделал Query Gen
  urls_found: number;
  urls_after_filter: number;
  urls_crawled: number;
  pages_crawled_total: number;

  // Кэш
  cache_hits: number;
  cache_misses: number;

  // LLM вызовы (массив, один элемент на каждый вызов)
  llm_calls: Array<{
    call_id: string;
    model: string;
    stage: "query_gen" | "url_classify" | "light_ai" | "deep_ai" | "premium_ai" | "scoring" | "outreach";
    input_tokens: number;
    output_tokens: number;
    cached_input_tokens: number;
    cost_usd: number;
    duration_ms: number;
    success: boolean;
    error?: string;
  }>;

  // Итог
  total_cost_usd: number;
  ai_credits_used: number;
  lead_score: number | null;
  confidence: number | null;
  outcome: "success" | "partial" | "failed" | "filtered_out";
  failure_reason: string | null;
}
```

**SQL-таблица:**

```sql
CREATE TABLE lead_processing_logs (
  log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id UUID REFERENCES leads(id),
  user_id UUID NOT NULL,
  campaign_id UUID,
  created_at TIMESTAMPTZ DEFAULT now(),
  search_query_original TEXT,
  search_queries_generated JSONB,
  urls_found INT,
  urls_after_filter INT,
  urls_crawled INT,
  pages_crawled_total INT,
  cache_hits INT DEFAULT 0,
  cache_misses INT DEFAULT 0,
  llm_calls JSONB,
  total_cost_usd NUMERIC(10, 6),
  ai_credits_used INT,
  lead_score INT,
  confidence NUMERIC(4, 3),
  outcome TEXT CHECK (outcome IN ('success', 'partial', 'failed', 'filtered_out')),
  failure_reason TEXT
);
```

---

## РАЗДЕЛ 12 — Anti-loss правила (обязательно к реализации)

Эти правила защищают маржу. Реализовать как middleware перед каждым дорогим этапом.

```typescript
const ANTI_LOSS_RULES = {
  // 1. Deep AI запускается только после Light AI
  deep_ai_requires_light_ai_pass: true,

  // 2. Дубли доменов не обрабатываются дважды в одной кампании
  deduplicate_by_domain: true,

  // 3. Агрегаторы не идут в финальный лид
  skip_aggregators_as_leads: true,

  // 4. Сайты без коммерческого смысла пропускаются
  skip_if_not_commercial: true,

  // 5. Outreach только для deep AI лидов
  outreach_requires_deep_ai: true,

  // 6. Outreach не генерируется для низкого score
  outreach_min_score: 50,

  // 7. Регенерации ограничены по тарифу
  message_regen_limits: { basic: 0, pro: 1, max: 3 },

  // 8. Краулинг строго в рамках тарифных лимитов страниц
  enforce_max_pages_per_site: true,

  // 9. Кэш обязательно проверяется до краулинга
  check_cache_before_crawl: true,

  // 10. Retry с лимитом (не бесконечные повторы)
  max_retry_attempts: 3,

  // 11. AI credits проверяются до запуска любого LLM-вызова
  check_credits_before_llm_call: true,
};
```

---

## РАЗДЕЛ 13 — Backend: job types и очередь

```typescript
type JobType =
  | "search_job"           // search_query cost
  | "scrape_job"           // basic_lead cost
  | "light_ai_job"         // 1 credit
  | "deep_ai_job"          // 5 credits
  | "premium_ai_job"       // 15 credits
  | "outreach_job"         // 3 credits
  | "outreach_regen_job"   // 3 credits
  | "monitoring_job";      // 2 credits

interface Job {
  id: string;
  type: JobType;
  user_id: string;
  campaign_id: string;
  payload: Record<string, unknown>;
  status: "pending" | "running" | "done" | "failed" | "cancelled";
  priority: number;
  retry_count: number;
  max_retries: number;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
  cost_usd: number | null;
}
```

**Очередь:** BullMQ (Redis) или pg-boss (Postgres, если хочешь всё в Supabase).

---

## РАЗДЕЛ 14 — Стек технологий

```yaml
frontend:
  framework: Next.js (App Router)
  ui: Tailwind CSS + shadcn/ui
  deploy: Vercel

backend:
  runtime: Node.js / TypeScript
  api: Next.js API Routes или отдельный Fastify-сервер
  queue: BullMQ (Redis) или pg-boss
  deploy: Vercel Functions / Railway

database:
  primary: Supabase (Postgres)
  cache_hot: Redis (Upstash для Vercel)
  cache_cold: Supabase Storage (S3-compatible)

llm:
  primary: GLM-4.7 / Claude Haiku 4.5 / Claude Sonnet 4.6
  alternative: OpenAI (GPT-5.4, Mini, Nano), Gemini 2.5 Flash-Lite
  budget: DeepSeek V3 / GLM-4.7-Flash (для Starter/MVP)
  premium: GLM-5 / Claude Sonnet 4.6 / GPT-5.4
  adapter: собственный LLM adapter factory с routing (см. раздел 8)

search:
  api: SerpAPI / Yandex Search API
  proxy: datacenter + residential pool

crawler:
  library: Cheerio (static) + Playwright (JS-heavy sites, только Max)
  proxy: rotating pool

observability:
  logs: LeadProcessingLog → Supabase
  metrics: Vercel Analytics / собственный дашборд
  spend_tracking: per user, per campaign, per model
```

---

## РАЗДЕЛ 15 — MVP: что реализовать в первую очередь

Строго в таком порядке:

1. **Supabase schema:** таблицы `leads`, `campaigns`, `users`, `ai_credits`, `lead_processing_logs`, `job_queue`
2. **LLM Adapter Factory** с smart routing (раздел 8) — без него нельзя начинать
3. **Query Generator** (Step 1)
4. **URL Filter** детерминированный (Step 3)
5. **Crawler** с rate limiting и UA rotation (Step 6)
6. **Basic HTML Extraction** (Step 7)
7. **Light AI** с Haiku (Step 8)
8. **Deep AI** с Sonnet (Step 9)
9. **Lead Scoring** (Step 11)
10. **Outreach Generation** (Step 12)
11. **CSV Export** (Step 13)
12. **Observability logging** — параллельно с каждым шагом
13. **AI Credits middleware** — перед любым LLM-вызовом

---

## РАЗДЕЛ 16 — Что оставить на потом (не MVP)

```yaml
not_for_mvp:
  - monitoring (отслеживание изменений на сайтах)
  - CRM-интеграции (Bitrix24, AmoCRM)
  - Автоматическая рассылка (только генерация писем)
  - Командные аккаунты и роли
  - Marketplace шаблонов промптов
  - Playwright stealth / JS-challenge
  - CAPTCHA solvers
  - Аналитика кампаний (дашборды, воронки)
  - Multi-agent архитектура с диалоговым агентом
  - Мобильное приложение
```

---

## РАЗДЕЛ 17 — Пример сквозного сценария (E2E)

**Вход пользователя:**
```
Я продаю разработку сайтов и SEO.
Найди стоматологии в Екатеринбурге, у которых слабый сайт или нет онлайн-записи.
```

**Выход системы (финальный лид после всего pipeline):**

```json
{
  "id": "a1b2c3d4-...",
  "domain": "example-dental.ru",
  "website": "https://example-dental.ru",
  "company_name": "Стоматология Улыбка",
  "city": "Екатеринбург",
  "industry": "Стоматология",
  "phone": "+7 (343) 123-45-67",
  "email": null,
  "telegram": "https://t.me/example_dental",
  "services": ["лечение зубов", "имплантация", "ортодонтия", "детская стоматология"],
  "website_quality": {
    "has_modern_design": false,
    "has_mobile_adaptation": true,
    "has_clear_cta": false,
    "has_online_booking": false,
    "seo_visible": false,
    "comments": "Нет заметной онлайн-записи. Слабый первый экран, нет выраженного CTA. Meta-теги не заполнены."
  },
  "lead_fit": {
    "score": 82,
    "reason": "Коммерческий сайт с реальными услугами. Нет онлайн-записи и SEO — прямой повод для предложения.",
    "priority": "high"
  },
  "pain_points": [
    "нет онлайн-записи",
    "слабый CTA на главной",
    "не заполнены meta-теги",
    "нет landing page под рекламу"
  ],
  "reason_to_contact": "Сайт не конвертирует посетителей в заявки: нет онлайн-записи и SEO-оптимизации.",
  "personalized_outreach": {
    "email_subject": "Идея по увеличению заявок с сайта вашей клиники",
    "email_body": "Здравствуйте!\n\nИзучил ваш сайт и заметил, что пользователям сложно быстро записаться онлайн — такой кнопки нет на первом экране. Плюс мета-теги не настроены, что снижает видимость в поиске.\n\nЕсли интересно — могу показать, как небольшие изменения увеличивают количество заявок. Это не потребует переделки всего сайта.",
    "telegram_message": "Добрый день! Посмотрел ваш сайт — нет онлайн-записи и SEO не настроен. Могу показать быстрое решение. Удобно коротко созвониться?",
    "regeneration_count": 0
  },
  "processing": {
    "ai_level": "deep",
    "sources": ["https://example-dental.ru/", "https://example-dental.ru/uslugi", "https://example-dental.ru/kontakty"],
    "confidence": 0.81,
    "cache_hit": false,
    "cost_usd": 0.047
  }
}
```

---

## РАЗДЕЛ 18 — Формулировки для пользователей (UI/marketing)

**Описания тарифов (не писать "X AI-лидов", писать конкретно):**

| Тариф | Правильная формулировка |
|-------|-------------------------|
| Free | До 20 найденных лидов для теста. Бесплатные модели, без deep/premium анализа. |
| Starter | До 200 найденных лидов. Light AI, без deep/premium анализа. |
| Pro | До 500 лидов, Light AI для всех, глубокий анализ до 150 лучших, до 150 персональных сообщений. |
| Agency | До 1500 лидов, Light AI для всех, глубокий анализ до 400 лучших, мониторинг 50 компаний. |
| Max | До 3000 лидов, Light AI для всех, до 800 глубоких анализов, до 150 premium-анализов, CRM-интеграции. |

**Что показывать в интерфейсе вместо одного поля "AI analyzed":**

```
Собрано лидов:               500
Прошло базовую обработку:    500
Light AI обработано:         500
Глубоко проанализировано:    143 / 150
Сгенерировано сообщений:     143 / 150
Осталось AI credits:         218 / 800
```

---

## РАЗДЕЛ 19 — Правило anti-hallucination (критично)

AI-слой обязан следовать этим правилам при любом вызове:

1. Если данных нет на сайте — писать `null`, не придумывать.
2. Не выдумывать email, телефон, имя владельца, оборот компании.
3. Для каждого важного поля хранить `source_url`.
4. Генерированное письмо опирается только на найденные факты.

**Плохо:**
```
Я вижу, что ваша клиника теряет клиентов из-за плохого сайта.
```

**Хорошо:**
```
Заметил, что на сайте нет онлайн-записи на первом экране. Возможно, это снижает конверсию с рекламы.
```

---

## РАЗДЕЛ 20 — Changelog

| Версия | Дата | Изменения |
|--------|------|-----------|
| 1.0 | — | Исходная продуктовая логика (ScrapeGraphAI-style подход) |
| 2.0 | май 2026 | + Query Generator, Cache Layer, Rate Limiting, Unit-экономика |
| 3.0 | май 2026 | + Тарифная экономика, AI Credits система, Smart Routing таблица, Anti-loss правила, Job types, полный backend-стек |
| 3.1 | май 2026 | + Новая сетка Free / Starter / Pro / Agency / Max, production-routing по тарифам, запрет free tiers для платных тарифов |
