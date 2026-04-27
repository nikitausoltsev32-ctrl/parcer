# Как тестить проект локально

## Что уже можно тестить без внешних сервисов

- Frontend build/lint.
- Backend unit tests.
- Страницы интерфейса в браузере, но без реальной регистрации/логина.

Команды:

```powershell
cd "C:\Users\HomePc\parcer V2\backend"
python -m pytest tests/ -v
python -m ruff check .

cd "C:\Users\HomePc\parcer V2\frontend"
cmd /c npm run build
cmd /c npm run lint
cmd /c npm run dev -- --host 127.0.0.1
```

Открыть UI: `http://127.0.0.1:5173`.

## Что нужно добавить для нормального ручного E2E

Нужен файл `.env` в корне проекта. Его можно скопировать из `.env.example`, но для теста важно заполнить минимум:

```env
APP_ENV=development
BASE_URL=http://localhost:8000
FRONTEND_URL=http://127.0.0.1:5173

DATABASE_URL=postgresql+asyncpg://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_ANON_KEY=<anon-key>
SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
SUPABASE_STORAGE_BUCKET=parcer-dev

REDIS_URL=rediss://default:<password>@<host>.upstash.io:6379

SECRET_KEY=<random-32-plus-chars>
FERNET_KEY=<fernet-key>
TRACKING_SECRET=<random-32-plus-chars>

TRANSACTIONAL_SMTP_HOST=
TRANSACTIONAL_SMTP_PORT=465
TRANSACTIONAL_SMTP_USER=
TRANSACTIONAL_SMTP_PASS=
TRANSACTIONAL_FROM_EMAIL=noreply@example.local
```

Почему `TRANSACTIONAL_SMTP_HOST=` пустой: тогда письма подтверждения печатаются в консоль backend, и можно вручную открыть ссылку. Если оставить `smtp.unisender.com` без логина/пароля, регистрация упадет на отправке письма.

## Что нужно подготовить во внешних сервисах

- Supabase project.
- Примененные SQL migrations из `supabase/migrations/`.
- Upstash Redis или другой доступный Redis по `REDIS_URL`.

Команды Supabase:

```powershell
supabase link --project-ref <ref>
supabase db push
```

## Как запускать для ручного теста

Терминал 1:

```powershell
cd "C:\Users\HomePc\parcer V2\backend"
python -m uvicorn app.main:app --reload --port 8000
```

Терминал 2:

```powershell
cd "C:\Users\HomePc\parcer V2\frontend"
cmd /c npm run dev -- --host 127.0.0.1
```

Открыть: `http://127.0.0.1:5173`.

## Первый сценарий для проверки

1. Открыть `/register`.
2. Зарегистрировать тестовый email.
3. В консоли backend найти напечатанную ссылку подтверждения.
4. Открыть ссылку.
5. Войти через `/login`.
6. Проверить, что после логина открывается `/app`.

## Что пока честно не готово как полноценный продуктовый E2E

- Без Supabase и Redis регистрация/логин вручную не заработают.
- AI/search/SMTP/inbox требуют ключи внешних провайдеров.
- Ссылка "Забыли пароль?" есть в UI, но отдельный frontend route/page для reset flow еще нужно довести.
