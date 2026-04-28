# Progress log

Последнее обновление: 2026-04-28

---

## Что работает прямо сейчас

### Инфраструктура
- Supabase (PostgreSQL) подключён и работает через SQLAlchemy asyncpg + SSL
- Миграции применены: 0001–0005 (включая token_store)
- Бэкенд: `uvicorn` запускается из `backend/`, конфиг читает `.env` из корня проекта
- Фронтенд: Vite на `http://127.0.0.1:5174`
- GitHub: `https://github.com/nikitausoltsev32-ctrl/parcer`

### Auth
- Регистрация работает (email отправка gracefully падает если SMTP не настроен)
- Логин работает без верификации email (верификация не требуется для входа)
- Refresh token через httpOnly cookie
- JWT access token в localStorage

### Chat
- ChatPage реализует базовый рабочий сценарий: создание сессии, отправка сообщения, SSE-стриминг, вывод tool results
- Бэкенд agent loop: до 5 итераций tool-calling
- Явные запросы "найди ..." теперь форсируют `search_companies`, даже если модель не вернула tool-call
- LLM: MiniMax M2.5 Free через OpenRouter (`minimax/minimax-m2.5:free`)

### Тестовый пользователь
- Email: `testuser5@example.com` / Password: `test1234`
- Кнопка `[DEV] Войти как тестовый пользователь` на `/login` (только в dev-режиме)

---

## Ключевые технические решения (принятые в последних сессиях)

1. **Redis удалён полностью** — заменён на PostgreSQL-таблицу `token_store` для email/reset-токенов
2. **Supabase connection**: `asyncpg` требует `ssl=SSLContext` + URL без `?pgbouncer=true` + `statement_cache_size=0`
3. **`.env` в корне проекта** — `config.py` ищет его через `Path(__file__).parent.parent.parent.parent / ".env"`
4. **LLM**: единственный рабочий ключ — `OPENROUTER_API_KEY`. Groq/Qwen ключи не заданы
5. **Procrastinate** подключён как job queue (миграция 0004), worker пока не запускается в dev

---

## Команды для запуска

```bash
# Бэкенд (из корня проекта)
cd backend && python -m uvicorn app.main:app --reload

# Фронтенд (из корня проекта)
cd frontend && npm run dev

# Применить миграции
supabase link --project-ref dhesdxkzacylwtojnjpj
supabase db push

# Тесты
cd backend && python -m pytest tests/ -v
```

---

## Структура .env (заполненные поля)

```
DATABASE_URL=postgresql+asyncpg://postgres.dhesdxkzacylwtojnjpj:...@aws-1-eu-north-1.pooler.supabase.com:5432/postgres?pgbouncer=true
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
OPENROUTER_API_KEY=sk-or-v1-...   # единственный рабочий LLM ключ
TWOGIS_API_KEY=...
SERPAPI_KEY=...
FIRECRAWL_API_KEY=...
LLM_CHAT_PROVIDER=minimax
LLM_CHAT_MODEL=minimax/minimax-m2.5:free
LLM_ENRICH_PROVIDER=minimax
LLM_ENRICH_MODEL=minimax/minimax-m2.5:free
# GROQ_API_KEY — не заполнен
# QWEN_API_KEY — не заполнен
# TRANSACTIONAL_SMTP_* — не заполнен (email отправки падают gracefully)
```

---

## Что реализовано в коде (но не протестировано E2E)

| Модуль | Статус |
|--------|--------|
| Auth (register/login/refresh/logout/reset) | Работает |
| Chat + SSE стриминг | Базово работает, E2E с MiniMax ещё не проверен |
| Chat tools | Частично: search/save/enrich есть, campaign/inbox/reminder tools пока `not_implemented` |
| Search + Firecrawl | Smoke-test пройден: SerpAPI вернул результаты, Firecrawl добавил `website_summary`; 2ГИС сейчас падает по timeout и не блокирует fallback |
| CRM (companies/contacts) | Роуты и UI пока заглушки, многие endpoints возвращают 501 |
| Campaigns | Роуты и UI пока заглушки, endpoints возвращают 501 |
| Inbox (IMAP poll) | Worker/роуты в коде, продуктовый сценарий не готов |
| Letters generation | Сервис в коде, нужен LLM ключ |
| Enrichment (Firecrawl→LLM) | Сервис в коде, нужен Firecrawl ключ |
| Reminders | Роуты пока 501 |
| SMTP accounts | Роуты пока 501 |
| Templates | Seed данные есть, API пока 501 |
| Procrastinate worker | Миграция применена, worker не запускался |

---

## Следующие шаги (приоритет)

1. **Протестировать чат E2E** — отправить сообщение, убедиться что MiniMax отвечает и tool-calling поддерживается
2. **Реализовать минимальные CRM endpoints** — list/create companies и contacts вместо 501
3. **Реализовать UI для CRM** — ContactsPage, CompaniesPage на реальных endpoints
4. **Реализовать Campaigns MVP** — черновик кампании, генерация писем, просмотр сообщений
5. **Настроить SMTP** для отправки email (нужен Яндекс/Gmail app-password)
6. **Запустить Procrastinate worker** для фоновых задач
7. **Онбординг** — первый вход должен запускать диалог для заполнения `business_profile`

---

## Известные баги / ограничения

- `minimax/minimax-m2.5:free` — не проверено поддерживает ли tool-calling. Если нет — нужна другая модель через OpenRouter
- Поиск больше не зависит только от tool-calling модели для явных запросов "найди ..."
- SMTP не настроен — письма только логируются в консоль
- Procrastinate worker нужно запускать отдельно (команда в CLAUDE.md)
- Python 3.14 на Windows — могут быть проблемы с некоторыми пакетами
- `supabase/.temp/*` сейчас отслеживается git, но это локальная metadata Supabase CLI; добавлен ignore на будущее, tracked-файлы нужно отдельно убрать из индекса перед коммитом
