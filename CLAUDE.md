rf# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**Лида AI** — ИИ-агент по продажам для вашего бизнеса в РФ. Старое кодовое имя: `parcer`, только для репозитория и технического контекста. Главный экран — чат с Лидой (tool-calling); параллельно есть классические экраны (CRM, Campaigns, Inbox). Язык UI и писем — русский.

**НЕ** называть продукт парсером/скрапером. НЕ позиционировать как инструмент массовой холодной рассылки.

Подробности — в `docs/PROJECT.md` (единый источник правды).

## Commands

### Backend (run from `backend/`)
```bash
pip install -e ".[dev]"
uvicorn app.main:app --reload         # dev API
python -m procrastinate --app app.workers.main.app worker   # dev worker
ruff check .
ruff format .
pytest tests/ -v
pytest tests/test_auth.py::test_login_success -v   # single test
```

### Frontend (run from `frontend/`)
```bash
npm install
npm run dev       # Vite :5173
npm run build
npm run lint
```

### Миграции БД (Supabase CLI, не Alembic)
```bash
supabase migration new <name>
supabase db push
supabase db reset
```

### Makefile ярлыки
`make dev` — запустить API + Vite одновременно через concurrently (из корня).
`make dev-api`, `make dev-worker`, `make dev-web`, `make test`, `make lint`, `make migrate-new name=...`, `make migrate-push`, `make migrate-reset`, `make seed`, `make types`.

## Architecture

**Cloud-first dev, без локального Docker:**
- Postgres + Storage — Supabase (облако).
- Очереди — Procrastinate в Supabase Postgres.
- Локально крутятся только uvicorn, Procrastinate worker, Vite dev-server.

**Стек:** FastAPI + SQLAlchemy async + Procrastinate → Supabase Postgres; React + Vite + TypeScript + Tailwind + shadcn/ui; текущий dev chat LLM — Groq `llama-3.3-70b-versatile`, Qwen/GLM остаются резервными провайдерами для отдельных задач.

**Главный интерфейс** — чат с Лидой через SSE-стрим. ИИ-агент вызывает инструменты (search_companies, create_campaign, generate_letters, send_campaign, check_inbox, add_note, set_reminder и т.д.). Классические экраны (CRM, Campaigns, Inbox, Templates, SMTP) — параллельно.

```
backend/
  app/
    api/v1/       # тонкие роутеры; бизнес-логика вызывается из services/
    core/         # config, database, security, tokens, email
    services/     # auth_service, llm/ (base, qwen, glm, groq, factory), chat/ (agent, tools), crm/, inbox/, letters/
    workers/      # Procrastinate задачи: generate_letters, send_email, poll_inbox, classify_inbox, run_followup, run_reminders
    models/       # SQLAlchemy ORM — User, Company, Contact, ContactList, Activity, SmtpAccount, Suppression, Template, Campaign, CampaignMessage, InboxMessage, ChatSession, ChatMessage, Reminder, Event
    schemas/      # Pydantic
frontend/
  src/
    pages/        # ChatPage, Login/Register/Verify, Contacts/Companies/Inbox/Campaigns/Settings
    features/     # chat, auth, crm, campaigns, inbox — фичевые слайсы
    components/ui/ # shadcn компоненты
    lib/          # api client, sse helper
supabase/
  migrations/     # *.sql — версионированная схема
docs/
  PROJECT.md      # единый документ
  adr/ legal/
```

## Rules for the AI assistant

- Отвечать по-русски, если вопрос по-русски.
- **НЕ** использовать слова «парсер», «скрапер», «база email», «массовая рассылка» в копии продукта.
- **НЕ** предлагать Google Search, WhatsApp Business API, Kubernetes, Elasticsearch, Alembic, локальный Docker/Postgres/Redis — вне scope.
- **Миграции — только через Supabase CLI** (файлы в `supabase/migrations/*.sql`). Не создавать Alembic-миграции.
- Бизнес-логика — в `backend/app/services/`, роутеры — тонкие.
- Все внешние вызовы (LLM, SMTP, IMAP) — с таймаутом и retry.
- Секреты — только через env.
- При изменении БД — новая миграция + обновить раздел 6 в `docs/PROJECT.md`.
- При добавлении эндпоинта — обновить раздел 7 в `docs/PROJECT.md`.
- При изменении промпта — обновить раздел 8 в `docs/PROJECT.md`.
- При изменении flow/экранов — обновить разделы 3–4 в `docs/PROJECT.md`.
- 2ГИС/Яндекс/Авито — под feature-flag, не считать доступными.
- CSV-импорт — рабочий fallback при сомнениях об источнике.
- Frontend: типы API — через `openapi-typescript`, не руками. Server state — только TanStack Query.

## 152-ФЗ и трансграничная передача
- Данные пользователя и его контактов хранятся в Supabase.
- AI-функции используют Qwen (Китай), Groq (США), GLM (Китай). Требуется явное согласие (`users.llm_consent_at`).
- В письмах — принудительный unsubscribe, реквизиты отправителя, суппрессии по отпискам.
- SMTP-пароли — шифрование Fernet, ключ в env.

## Quickstart
```
cp .env.example .env    # заполнить SUPABASE_*, LLM keys, SECRET_KEY, FERNET_KEY, TRACKING_SECRET
supabase link --project-ref <ref>
supabase db push
make install            # pip install + npm install
make dev                # запускает API + Vite через concurrently
```
