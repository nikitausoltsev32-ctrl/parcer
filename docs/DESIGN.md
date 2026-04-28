# Product Design Brief

## Project

**Лида AI** is positioned as: `ИИ-агент по продажам для вашего бизнеса`. `parcer` is only an old repository/codename and must not appear as the product brand in the UI, marketing copy, or design direction.

The product must not be positioned as a scraper, email database, or mass cold-email tool. The user-facing promise is simple: Лида AI helps find relevant companies, understand them, prepare personal outreach, keep lightweight CRM memory, and handle replies.

The main product surface is **chat with Лида**, not a classic CRM dashboard. Classic CRM screens exist, but they are secondary and should support the chat workflow.

Language of the UI and generated outreach is Russian.

## Product Feel

The interface should feel like a serious operating tool for repeated daily work:

- quiet, precise, and business-like;
- dense enough for scanning lists and comparing companies;
- clear about what the assistant is doing;
- practical, not decorative;
- trustworthy with data and actions.

Avoid a generic AI startup look. No glowing gradients, giant hero sections inside the app, dark cyber style, decorative blobs, or vague "magic" visuals.

Good references:

- **Attio**: clean CRM structure, records, lists, side panels.
- **Linear**: restrained interface, compact layout, statuses, keyboard-friendly feel.
- **Intercom / ChatGPT Team**: chat as an operational workspace.
- **Folk CRM / Clay**: company lists, enriched company data, table-first workflows.

## Design Principle

Design around the core loop:

```text
User asks in chat
→ assistant runs a tool
→ UI shows progress
→ UI shows structured results
→ user confirms next action
→ data is saved to CRM/campaigns
```

The product should not show raw JSON or technical tool output to the user. Tool results should become cards, tables, badges, progress rows, and action buttons.

Brand voice examples:

- `Лида ищет компании`
- `Лида читает сайты`
- `Лида подготовила список`
- `Лида не получила ответ от 2ГИС и продолжила через SerpAPI`

Avoid using `AI assistant`, `AI sales manager`, or generic AI startup wording as visible product copy. Use `Лида AI` for the product name and `Лида` when the UI speaks about actions naturally.

## Visual Direction

Use a light operational SaaS interface:

- background: white / near-white;
- surfaces: subtle gray bands and bordered panels;
- accent: one restrained primary color, preferably blue or cold green;
- typography: compact, readable, no oversized marketing headings in app screens;
- borders: subtle, mostly 1px;
- radius: 6-8px for cards and controls;
- icons: lucide icons, small and functional;
- spacing: compact, consistent, built for repeated use.

The app should feel like a workbench, not a landing page.

## Layout

### App Shell

Persistent left navigation:

- Chat
- Clients
- Companies
- Inbox
- Campaigns
- Settings

The sidebar should be calm and compact. The product name `Лида AI` should be visible but should not dominate the screen.

Main content changes by route, but the first and most important screen is Chat.

### Chat Screen

Chat is the command center.

Expected structure:

- message timeline in the center;
- input fixed at bottom;
- assistant messages can contain rich blocks;
- tool progress is visible;
- result cards have direct next actions.

For example, after:

```text
найди дизайн-студии в Казани
```

the assistant should not only answer text. It should show:

- progress state: searching sources, reading websites, preparing results;
- a results card with a compact company table;
- source badges: `SerpAPI`, `2GIS`, `Firecrawl`;
- per-row data: name, website, source, summary, email/phone if available;
- actions: save list, enrich more, create campaign.

### Right Panel

Later, add a contextual right panel for details:

- selected company;
- selected contact;
- current contact list;
- current campaign;
- enrichment details.

Do not build it as a permanent empty panel before it has useful content.

## Core Components

Build a small design system on top of Tailwind + shadcn/ui/Radix + lucide.

Primary components:

- `ToolRunStatus`  
  Shows what the assistant is doing: searching, scraping, saving, generating.

- `LeadResultsCard`  
  Structured card for company search results.

- `CompanyRow`  
  One company in a search result or CRM table.

- `SourceBadge`  
  Shows source: `2GIS`, `SerpAPI`, `Firecrawl`, `CSV`, `manual`.

- `ConfidenceBadge`  
  Shows whether data is verified, inferred, missing, or failed.

- `ActionBar`  
  Compact row of next actions.

- `DataTable`  
  Reusable table for CRM lists, campaigns, inbox.

- `SidePanel`  
  Details panel for selected records.

- `EmptyState`  
  Calm empty state with one useful action, not marketing copy.

- `ErrorInline`  
  Shows recoverable tool/API errors clearly.

## Data States

Every important block must handle:

- loading;
- partial results;
- empty result;
- error;
- retry available;
- completed state.

Лида should be honest when something fails:

Good:

```text
2GIS не ответил за 10 секунд. Я продолжил через SerpAPI и прочитал сайты через Firecrawl.
```

Bad:

```text
Готово!
```

when data is partial or failed.

## Main MVP Screens

### Chat

Priority screen. Must support:

- free-form user request;
- tool progress;
- structured search result card;
- save result list;
- visible errors and fallbacks.

### Contacts / Clients

Table-first CRM-lite view:

- name;
- company;
- status;
- email;
- last activity;
- next step;
- source.

No heavy CRM complexity. This is assistant memory, not Salesforce.

### Companies

Company table and detail panel:

- name;
- website;
- city;
- industry;
- source;
- enrichment summary;
- related contacts.

### Campaigns

Should eventually show:

- campaign status;
- contact list;
- generated letters;
- send progress;
- reply/open/click stats.

For now, do not over-design it before the search/contact flow is real.

### Inbox

Operational reply queue:

- classification badge;
- sender/contact;
- campaign;
- suggested reply;
- next action.

## Current Technical Context

Frontend:

- React 18
- Vite
- TypeScript
- Tailwind
- lucide-react
- React Router
- Axios
- SSE helper for chat streaming

Backend:

- FastAPI
- SQLAlchemy async
- Supabase Postgres
- Procrastinate worker
- Groq `llama-3.3-70b-versatile` currently used for chat
- Search path: 2GIS first, SerpAPI fallback, Firecrawl website scrape

Current important behavior:

- explicit search requests like "найди ..." should trigger company search even if the model does not return tool calls;
- SerpAPI fallback works when 2GIS times out;
- Firecrawl scrape currently works after removing unsupported `maxLength` payload field;
- deep `enrich_contacts` is queued through Procrastinate and requires a running worker.

## UX Rules

- Do not expose raw JSON to users.
- Do not hide tool failures.
- Do not imply data is verified if it is only scraped or inferred.
- Do not use decorative AI visuals.
- Do not create dashboard cards just to fill space.
- Do not build marketing copy inside the logged-in app.
- Keep controls close to the data they affect.
- Make primary next actions obvious but not loud.

## Copy Tone

Russian UI copy should be short and direct.

Good:

- `Ищу компании`
- `Читаю сайты`
- `Сохранить список`
- `Создать кампанию`
- `2ГИС не ответил, продолжаю через SerpAPI`

Bad:

- `Используйте мощь искусственного интеллекта`
- `Раскройте потенциал ваших продаж`
- `Мгновенно масштабируйте холодные рассылки`

## First Design Target

The first high-quality design target should be:

```text
Chat search result experience
```

Scope:

- user sends a search request;
- assistant shows progress;
- result card displays companies;
- failed sources are visible;
- user can save the list;
- UI looks like a real work tool.

Do not start with a full dashboard redesign. The product will feel right only when the chat result experience feels real.

## Suggested First Implementation Slice

1. Parse `tool_result` in `ChatPage`.
2. Detect `search_companies` results.
3. Render `LeadResultsCard` instead of raw text.
4. Show source badges and website summaries.
5. Add actions: `Сохранить список`, `Обогатить`, `Создать кампанию`.
6. Keep raw fallback only for unknown tool results.

This is the shortest path to making the product look and feel like the intended ИИ-агент по продажам.
