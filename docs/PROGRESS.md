# Progress log

Дата: 2026-04-26

## Что уже сделано

- Проект переведен на cloud-first архитектуру из `CLAUDE.md` и `docs/PROJECT.md`: Supabase migrations вместо Alembic, без локального Docker/Postgres/Redis как обязательного dev-стека.
- Удалены устаревшие Alembic/infra файлы старого Phase 0: `backend/alembic*`, `backend/worker/*`, `infra/docker-compose.yml`, `infra/caddy/Caddyfile`.
- Добавлены базовые документы проекта: `README.md`, `CLAUDE.md`, `Makefile`, `.github/PULL_REQUEST_TEMPLATE.md`, ADR и legal drafts в `docs/`.
- Backend:
  - FastAPI приложение и v1 router.
  - Конфиг env-переменных под Supabase, Upstash Redis, LLM-провайдеров, SMTP и Sentry.
  - SQLAlchemy модели для auth, CRM, кампаний, inbox, chat, reminders, events.
  - Supabase SQL migrations: initial schema, seed templates, RLS.
  - Auth API: register, verify email, login, refresh, logout, forgot/reset password, `/me`.
  - Каркасы API для chat, companies, contacts, campaigns, inbox, reminders, SMTP accounts, templates.
  - Сервисы auth, CRM, LLM, letters, inbox classifier, search adapters.
  - ARQ worker перемещен в `backend/app/workers/`.
  - Backend tests для health, security и базового auth flow.
- Frontend:
  - React/Vite app routing.
  - API client, auth state helpers, SSE helper.
  - Login/register/verify pages.
  - Protected app layout.
  - Базовые страницы: chat, contacts, companies, inbox, campaigns, settings.

## Важные решения

- Старые планы `docs/superpowers/plans/2026-04-23-phase-0-setup.md` и `2026-04-23-phase-1-auth.md` частично устарели: в них есть Alembic/Docker/local Redis, а актуальные правила проекта требуют Supabase migrations и cloud-first dev.
- Продолжать нужно от `CLAUDE.md` и `docs/PROJECT.md`, не возвращая Alembic и Docker Compose.

## Текущие проверки

- Backend tests: `python -m pytest tests/ -v` -> 12 passed, 1 warning от `passlib/argon2`.
- Backend lint: `python -m ruff check .` -> passed.
- Frontend build: `cmd /c npm run build` -> passed.
- Frontend lint: `cmd /c npm run lint` -> passed.

## Сделано в этой сессии

- Добавлен этот progress log: `docs/PROGRESS.md`.
- Исправлена сборка editable backend package: в `backend/pyproject.toml` явно указан пакет `app` для Hatch wheel.
- Исправлены ruff-ошибки:
  - убран неиспользуемый импорт `select`;
  - убраны/разбиты длинные строки в `backend/app/services/chat/tools.py`;
  - убрана неиспользуемая переменная в `backend/app/services/search/twogis.py`.
- Починен frontend lint под ESLint 9:
  - добавлен `frontend/eslint.config.js`;
  - добавлена dev-зависимость `typescript-eslint`;
  - убран `any` из `frontend/src/pages/RegisterPage.tsx`.
- Поправлены ссылки verify/reset email: теперь письма ведут на `FRONTEND_URL`, а не на backend host.
- Добавлен ручной чеклист тестирования: `docs/TESTING.md`.

## Ограничения окружения

- На машине используется Python 3.14, хотя проект заявлен как Python 3.12+.
- `python -m pip install -e .[dev]` теперь проходит стадию сборки `parcer-backend`, но полная установка упирается в `pyiceberg` из зависимости `supabase`: под Python 3.14 на Windows пакет требует Microsoft C++ Build Tools. Текущие тесты и ruff после этого запускаются успешно в уже установленном user-site окружении.

## Следующее

- Не откладывать решение по Python версии: лучше поставить Python 3.12 для backend dev, чтобы не ловить несовместимости Python 3.14.
- Следующий продуктовый слой: довести реальные сценарии `/app` до рабочих действий, а не только каркаса страниц.
- Для ручного E2E сначала заполнить `.env`, применить Supabase migrations и подключить Redis. Детали в `docs/TESTING.md`.
