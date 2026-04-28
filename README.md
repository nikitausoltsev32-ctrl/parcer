# Лида AI

ИИ-агент по продажам для вашего бизнеса: находит компании, пишет персональные письма, ведёт CRM и обрабатывает ответы. Главный интерфейс — чат с Лидой.

## Документация
- **[docs/PROJECT.md](docs/PROJECT.md)** — единый документ: позиционирование, scope, архитектура, БД, API, промпты, roadmap.
- **[CLAUDE.md](CLAUDE.md)** — контекст для AI-ассистентов (Claude Code / Cursor / и т.п.).
- **[docs/adr/](docs/adr/)** — зафиксированные технические решения.
- **[docs/legal/](docs/legal/)** — drafts оферты, политики ПДн, согласий.

## Стек
Python 3.12 · FastAPI · SQLAlchemy async · Procrastinate · React 18 · Vite · TypeScript · Tailwind · shadcn/ui · Supabase (Postgres + Storage) · Groq · Qwen / GLM.

## Быстрый старт (локальная разработка без Docker)

```bash
# один раз
npm i -g supabase
supabase login
supabase link --project-ref <your-ref>

cp .env.example .env
# заполнить SUPABASE_*, OPENROUTER_API_KEY или LLM API keys,
# SECRET_KEY, FERNET_KEY, TRACKING_SECRET

cd backend && pip install -e ".[dev]"
cd frontend && npm install

# применить миграции к cloud-проекту Supabase
supabase db push

# dev (3 терминала — или используйте make)
make dev-api         # uvicorn, порт 8000
make dev-worker      # Procrastinate worker
make dev-web         # vite, порт 5173
```

RAM на ПК: ~200 MB python + ~300 MB node. Docker, Postgres, Redis локально **не нужны**.

## Запуск тестов и линта
```bash
make test            # pytest
make lint            # ruff
```

## Миграции БД
```bash
make migrate-new name=add_something    # создать новую миграцию
make migrate-push                      # применить к Supabase
make migrate-reset                     # сбросить и переприменить все
```

## Структура репо
```
backend/
  app/
    api/v1/       # FastAPI роутеры (тонкие)
    core/         # config, database, security, tokens, email
    services/     # бизнес-логика (auth, llm, chat, crm, inbox, letters)
    workers/      # Procrastinate задачи
    models/       # SQLAlchemy
    schemas/      # Pydantic
  tests/
frontend/
  src/
    pages/
    features/{auth,chat,crm,campaigns,inbox}/
    components/ui/
    lib/
supabase/
  migrations/     # SQL-миграции, версионированные
docs/
  PROJECT.md
  adr/
  legal/
infra/            # будет восстановлено для prod-деплоя
.github/
```

## Как помогать этому проекту
Запросы и баги — через GitHub Issues. PR-шаблон — в `.github/PULL_REQUEST_TEMPLATE.md`.

## Лицензия
Проприетарный (пока; лицензия появится при открытии репо).
