# Phase 0 — Project Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bootstrap the parcer monorepo with a working FastAPI backend, React frontend, Docker Compose stack, and GitHub Actions CI — all runnable locally with one command.

**Architecture:** Monorepo (`/backend`, `/frontend`, `/infra`, `/docs`) on one VPS. FastAPI serves `/api/*`, Caddy reverse-proxies and serves the React SPA static build. ARQ worker handles async tasks via Redis queue. Postgres is the main store.

**Tech Stack:** Python 3.12 + FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic + ARQ | React 18 + Vite + TypeScript + Tailwind CSS + shadcn/ui + TanStack Query + React Router | Docker Compose | Caddy | GitHub Actions

---

## File Map

```
parcer/                              ← repo root
├── .github/
│   └── workflows/
│       └── ci.yml                   ← lint + test + docker build
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  ← FastAPI app factory
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py            ← pydantic-settings Settings
│   │   │   └── database.py          ← async engine + session factory
│   │   └── api/
│   │       ├── __init__.py
│   │       └── v1/
│   │           ├── __init__.py
│   │           └── router.py        ← health-check endpoint
│   ├── worker/
│   │   ├── __init__.py
│   │   └── main.py                  ← ARQ WorkerSettings
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/                ← empty, migrations added in Phase 1
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_health.py           ← smoke test for /api/v1/health
│   ├── alembic.ini
│   ├── pyproject.toml               ← deps + ruff + pytest config
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx                  ← root component with router
│   │   └── lib/
│   │       └── api.ts               ← axios base instance
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── postcss.config.js
│   └── Dockerfile
├── infra/
│   ├── caddy/
│   │   └── Caddyfile
│   └── docker-compose.yml
├── .env.example
├── .gitignore
└── docs/
    └── superpowers/
        └── plans/
            └── 2026-04-23-phase-0-setup.md   ← this file
```

---

## Task 1: Root scaffold — .gitignore, .env.example, folder skeleton

**Files:**
- Create: `.gitignore`
- Create: `.env.example`
- Create: `backend/` (empty tree)
- Create: `frontend/` (empty tree)
- Create: `infra/caddy/` (empty tree)

- [ ] **Step 1: Create directory tree**

```bash
cd "C:\Users\HomePc\parcer V2"
mkdir -p backend/app/core backend/app/api/v1 backend/worker backend/alembic/versions backend/tests
mkdir -p frontend/src/lib
mkdir -p infra/caddy
```

- [ ] **Step 2: Create .gitignore**

Create file `C:\Users\HomePc\parcer V2\.gitignore`:

```gitignore
# Python
__pycache__/
*.py[cod]
.venv/
dist/
*.egg-info/
.pytest_cache/
.ruff_cache/
.mypy_cache/

# Node
node_modules/
frontend/dist/
frontend/.vite/

# Env
.env
.env.local
.env.*.local

# Docker
*.log

# OS
.DS_Store
Thumbs.db

# IDE
.idea/
.vscode/
```

- [ ] **Step 3: Create .env.example**

Create file `C:\Users\HomePc\parcer V2\.env.example`:

```env
# Postgres
POSTGRES_USER=parcer
POSTGRES_PASSWORD=changeme
POSTGRES_DB=parcer
DATABASE_URL=postgresql+asyncpg://parcer:changeme@postgres:5432/parcer

# Redis
REDIS_URL=redis://redis:6379/0

# Security
SECRET_KEY=change-me-32-chars-minimum-random
FERNET_KEY=change-me-fernet-base64-key

# LLM (один из двух)
YANDEX_GPT_API_KEY=
YANDEX_GPT_FOLDER_ID=
GIGACHAT_CLIENT_ID=
GIGACHAT_CLIENT_SECRET=

# SMTP транзакционные письма (Unisender Go или Postmark)
TRANSACTIONAL_SMTP_HOST=smtp.unisender.com
TRANSACTIONAL_SMTP_PORT=465
TRANSACTIONAL_SMTP_USER=
TRANSACTIONAL_SMTP_PASS=
TRANSACTIONAL_FROM_EMAIL=noreply@parcer.ru

# App
APP_ENV=development
BASE_URL=http://localhost:8000
FRONTEND_URL=http://localhost:5173

# S3-совместимое (Selectel)
S3_ENDPOINT_URL=
S3_ACCESS_KEY=
S3_SECRET_KEY=
S3_BUCKET=parcer-dev
```

- [ ] **Step 4: Commit**

```bash
cd "C:\Users\HomePc\parcer V2"
git init
git add .gitignore .env.example
git commit -m "chore: init repo, add .gitignore and .env.example"
```

---

## Task 2: Docker Compose + Caddyfile

**Files:**
- Create: `infra/docker-compose.yml`
- Create: `infra/caddy/Caddyfile`

- [ ] **Step 1: Create docker-compose.yml**

Create file `C:\Users\HomePc\parcer V2\infra\docker-compose.yml`:

```yaml
version: "3.9"

services:
  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./caddy/Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
      - ../frontend/dist:/srv/frontend:ro
    depends_on:
      - api

  api:
    build:
      context: ../backend
      dockerfile: Dockerfile
    restart: unless-stopped
    env_file: ../.env
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    ports:
      - "8000:8000"

  worker:
    build:
      context: ../backend
      dockerfile: Dockerfile
    restart: unless-stopped
    command: python -m arq worker.main.WorkerSettings
    env_file: ../.env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  postgres:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 10

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 10

volumes:
  pg_data:
  redis_data:
  caddy_data:
  caddy_config:
```

- [ ] **Step 2: Create Caddyfile**

Create file `C:\Users\HomePc\parcer V2\infra\caddy\Caddyfile`:

```caddyfile
{
    admin off
}

:80 {
    # API
    handle /api/* {
        reverse_proxy api:8000
    }

    # Tracking pixel (public, no auth)
    handle /t/* {
        reverse_proxy api:8000
    }

    # SPA — все остальные пути
    handle {
        root * /srv/frontend
        try_files {path} /index.html
        file_server
    }
}
```

- [ ] **Step 3: Commit**

```bash
cd "C:\Users\HomePc\parcer V2"
git add infra/
git commit -m "chore: add docker-compose and Caddyfile"
```

---

## Task 3: Backend — pyproject.toml + Dockerfile

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/Dockerfile`
- Create: `backend/alembic.ini`

- [ ] **Step 1: Create pyproject.toml**

Create file `C:\Users\HomePc\parcer V2\backend\pyproject.toml`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "parcer-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "pydantic>=2.7.0",
    "pydantic-settings>=2.3.0",
    "sqlalchemy[asyncio]>=2.0.30",
    "asyncpg>=0.29.0",
    "alembic>=1.13.0",
    "redis>=5.0.0",
    "arq>=0.26.0",
    "httpx>=0.27.0",
    "python-multipart>=0.0.9",
    "passlib[argon2]>=1.7.4",
    "python-jose[cryptography]>=3.3.0",
    "cryptography>=42.0.0",
    "boto3>=1.34.0",
    "aiofiles>=23.0.0",
    "email-validator>=2.1.0",
    "dnspython>=2.6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.27.0",
    "ruff>=0.4.0",
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Create Dockerfile**

Create file `C:\Users\HomePc\parcer V2\backend\Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml .
RUN uv pip install --system --no-cache -e .

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Create alembic.ini**

Create file `C:\Users\HomePc\parcer V2\backend\alembic.ini`:

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 4: Commit**

```bash
cd "C:\Users\HomePc\parcer V2"
git add backend/pyproject.toml backend/Dockerfile backend/alembic.ini
git commit -m "chore: add backend pyproject.toml and Dockerfile"
```

---

## Task 4: Backend — core config + database + FastAPI app

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/database.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/v1/__init__.py`
- Create: `backend/app/api/v1/router.py`
- Create: `backend/app/main.py`
- Test: `backend/tests/test_health.py`

- [ ] **Step 1: Write failing test**

Create file `C:\Users\HomePc\parcer V2\backend\tests\__init__.py`: *(empty)*

Create file `C:\Users\HomePc\parcer V2\backend\tests\test_health.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def client():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_health_returns_ok(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd "C:\Users\HomePc\parcer V2\backend"
python -m pytest tests/test_health.py -v
```

Expected: `ModuleNotFoundError: No module named 'app'` or `ImportError`

- [ ] **Step 3: Create `__init__.py` files**

Create `C:\Users\HomePc\parcer V2\backend\app\__init__.py`: *(empty)*
Create `C:\Users\HomePc\parcer V2\backend\app\core\__init__.py`: *(empty)*
Create `C:\Users\HomePc\parcer V2\backend\app\api\__init__.py`: *(empty)*
Create `C:\Users\HomePc\parcer V2\backend\app\api\v1\__init__.py`: *(empty)*

- [ ] **Step 4: Create config.py**

Create file `C:\Users\HomePc\parcer V2\backend\app\core\config.py`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    secret_key: str = "dev-secret-change-me"
    fernet_key: str = ""

    database_url: str = "postgresql+asyncpg://parcer:changeme@localhost:5432/parcer"
    redis_url: str = "redis://localhost:6379/0"

    base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"

    s3_endpoint_url: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = "parcer-dev"

    yandex_gpt_api_key: str = ""
    yandex_gpt_folder_id: str = ""
    gigachat_client_id: str = ""
    gigachat_client_secret: str = ""

    transactional_smtp_host: str = ""
    transactional_smtp_port: int = 465
    transactional_smtp_user: str = ""
    transactional_smtp_pass: str = ""
    transactional_from_email: str = "noreply@parcer.ru"


settings = Settings()
```

- [ ] **Step 5: Create database.py**

Create file `C:\Users\HomePc\parcer V2\backend\app\core\database.py`:

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

- [ ] **Step 6: Create v1 router with health endpoint**

Create file `C:\Users\HomePc\parcer V2\backend\app\api\v1\router.py`:

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 7: Create main.py**

Create file `C:\Users\HomePc\parcer V2\backend\app\main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.core.config import settings

app = FastAPI(title="parcer API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix="/api/v1")
```

- [ ] **Step 8: Run test to verify it passes**

```bash
cd "C:\Users\HomePc\parcer V2\backend"
python -m pytest tests/test_health.py -v
```

Expected:
```
PASSED tests/test_health.py::test_health_returns_ok
1 passed in ...
```

- [ ] **Step 9: Commit**

```bash
cd "C:\Users\HomePc\parcer V2"
git add backend/app/ backend/tests/
git commit -m "feat: add FastAPI skeleton with health endpoint"
```

---

## Task 5: Backend — Alembic init + ARQ worker skeleton

**Files:**
- Create: `backend/alembic/env.py`
- Create: `backend/worker/__init__.py`
- Create: `backend/worker/main.py`

- [ ] **Step 1: Create alembic/env.py**

Create file `C:\Users\HomePc\parcer V2\backend\alembic\env.py`:

```python
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.core.config import settings
from app.core.database import Base

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 2: Create worker files**

Create `C:\Users\HomePc\parcer V2\backend\worker\__init__.py`: *(empty)*

Create file `C:\Users\HomePc\parcer V2\backend\worker\main.py`:

```python
from arq import cron
from arq.connections import RedisSettings

from app.core.config import settings


async def startup(ctx):
    pass


async def shutdown(ctx):
    pass


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    on_startup = startup
    on_shutdown = shutdown
    functions = []
    cron_jobs = []
```

- [ ] **Step 3: Commit**

```bash
cd "C:\Users\HomePc\parcer V2"
git add backend/alembic/ backend/worker/
git commit -m "chore: add alembic env and arq worker skeleton"
```

---

## Task 6: Frontend — Vite + React + TypeScript + Tailwind + shadcn/ui

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/postcss.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/Dockerfile`

- [ ] **Step 1: Create package.json**

Create file `C:\Users\HomePc\parcer V2\frontend\package.json`:

```json
{
  "name": "parcer-frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "lint": "eslint src --ext ts,tsx --report-unused-disable-directives --max-warnings 0"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.23.1",
    "@tanstack/react-query": "^5.45.0",
    "axios": "^1.7.2",
    "clsx": "^2.1.1",
    "tailwind-merge": "^2.3.0",
    "class-variance-authority": "^0.7.0",
    "lucide-react": "^0.395.0",
    "@radix-ui/react-slot": "^1.1.0",
    "@radix-ui/react-dialog": "^1.1.1",
    "@radix-ui/react-dropdown-menu": "^2.1.1",
    "@radix-ui/react-label": "^2.1.0",
    "@radix-ui/react-toast": "^1.2.1"
  },
  "devDependencies": {
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "autoprefixer": "^10.4.19",
    "eslint": "^9.5.0",
    "postcss": "^8.4.39",
    "tailwindcss": "^3.4.4",
    "typescript": "^5.4.5",
    "vite": "^5.3.2"
  }
}
```

- [ ] **Step 2: Create tsconfig.json**

Create file `C:\Users\HomePc\parcer V2\frontend\tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src"]
}
```

- [ ] **Step 3: Create vite.config.ts**

Create file `C:\Users\HomePc\parcer V2\frontend\vite.config.ts`:

```ts
import path from "path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/api": "http://localhost:8000",
      "/t": "http://localhost:8000",
    },
  },
});
```

- [ ] **Step 4: Create Tailwind config**

Create file `C:\Users\HomePc\parcer V2\frontend\tailwind.config.ts`:

```ts
import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [],
};

export default config;
```

- [ ] **Step 5: Create postcss.config.js**

Create file `C:\Users\HomePc\parcer V2\frontend\postcss.config.js`:

```js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

- [ ] **Step 6: Create index.html**

Create file `C:\Users\HomePc\parcer V2\frontend\index.html`:

```html
<!doctype html>
<html lang="ru">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>parcer</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 7: Create src/main.tsx**

Create file `C:\Users\HomePc\parcer V2\frontend\src\main.tsx`:

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./index.css";

const queryClient = new QueryClient();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>
);
```

- [ ] **Step 8: Create src/index.css**

Create file `C:\Users\HomePc\parcer V2\frontend\src\index.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    --popover: 0 0% 100%;
    --popover-foreground: 222.2 84% 4.9%;
    --primary: 221.2 83.2% 53.3%;
    --primary-foreground: 210 40% 98%;
    --secondary: 210 40% 96.1%;
    --secondary-foreground: 222.2 47.4% 11.2%;
    --muted: 210 40% 96.1%;
    --muted-foreground: 215.4 16.3% 46.9%;
    --accent: 210 40% 96.1%;
    --accent-foreground: 222.2 47.4% 11.2%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 210 40% 98%;
    --border: 214.3 31.8% 91.4%;
    --input: 214.3 31.8% 91.4%;
    --ring: 221.2 83.2% 53.3%;
    --radius: 0.5rem;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
  }
}
```

- [ ] **Step 9: Create src/App.tsx**

Create file `C:\Users\HomePc\parcer V2\frontend\src\App.tsx`:

```tsx
import { Routes, Route } from "react-router-dom";

function HomePage() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-primary">parcer</h1>
        <p className="mt-2 text-muted-foreground">AI-платформа для лидогенерации</p>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
    </Routes>
  );
}
```

- [ ] **Step 10: Create src/lib/api.ts**

Create file `C:\Users\HomePc\parcer V2\frontend\src\lib\api.ts`:

```ts
import axios from "axios";

export const api = axios.create({
  baseURL: "/api/v1",
  withCredentials: true,
});

api.interceptors.response.use(
  (res) => res,
  async (err) => {
    if (err.response?.status === 401) {
      try {
        await axios.post("/api/v1/auth/refresh", {}, { withCredentials: true });
        return api.request(err.config);
      } catch {
        window.location.href = "/login";
      }
    }
    return Promise.reject(err);
  }
);
```

- [ ] **Step 11: Create frontend Dockerfile**

Create file `C:\Users\HomePc\parcer V2\frontend\Dockerfile`:

```dockerfile
FROM node:20-alpine AS build

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
```

- [ ] **Step 12: Install deps and verify dev server starts**

```bash
cd "C:\Users\HomePc\parcer V2\frontend"
npm install
npm run build
```

Expected: `dist/` folder created, no TypeScript errors.

- [ ] **Step 13: Commit**

```bash
cd "C:\Users\HomePc\parcer V2"
git add frontend/
git commit -m "feat: add React+Vite+Tailwind frontend skeleton"
```

---

## Task 7: GitHub Actions CI

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create directory**

```bash
mkdir -p "C:\Users\HomePc\parcer V2\.github\workflows"
```

- [ ] **Step 2: Create ci.yml**

Create file `C:\Users\HomePc\parcer V2\.github\workflows\ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  backend-lint:
    name: Backend lint
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install ruff
      - run: ruff check .

  backend-test:
    name: Backend tests
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install uv && uv pip install --system -e ".[dev]"
      - run: pytest tests/ -v

  frontend-build:
    name: Frontend build
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm run build

  docker-build:
    name: Docker build check
    runs-on: ubuntu-latest
    needs: [backend-test, frontend-build]
    steps:
      - uses: actions/checkout@v4
      - name: Build backend image
        run: docker build -t parcer-api:ci ./backend
      - name: Build frontend image
        run: docker build -t parcer-frontend:ci ./frontend
```

- [ ] **Step 3: Commit**

```bash
cd "C:\Users\HomePc\parcer V2"
git add .github/
git commit -m "ci: add GitHub Actions workflow for lint, test, docker build"
```

---

## Task 8: Smoke test — full local stack

- [ ] **Step 1: Copy .env.example to .env**

```bash
cp "C:\Users\HomePc\parcer V2\.env.example" "C:\Users\HomePc\parcer V2\.env"
```

Edit `.env` — set `POSTGRES_PASSWORD`, `SECRET_KEY` to any non-empty values for local dev.

- [ ] **Step 2: Build and start Docker Compose**

```bash
cd "C:\Users\HomePc\parcer V2\infra"
docker compose up --build -d
```

- [ ] **Step 3: Verify API health endpoint**

```bash
curl http://localhost:8000/api/v1/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 4: Verify Caddy routes API**

```bash
curl http://localhost/api/v1/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 5: Verify frontend served through Caddy**

Open `http://localhost` in browser. Should show the parcer homepage with "AI-платформа для лидогенерации".

- [ ] **Step 6: Final commit**

```bash
cd "C:\Users\HomePc\parcer V2"
git add .
git commit -m "chore: phase 0 complete — full scaffold verified"
```

---

## Checklist: Spec Coverage

| Requirement (from 05_ARCHITECTURE.md + 09_ROADMAP.md) | Task |
|---|---|
| Monorepo `/backend`, `/frontend`, `/infra`, `/docs` | Task 1 |
| Docker Compose: caddy, api, worker, postgres, redis | Task 2 |
| Caddy reverse-proxy + static SPA | Task 2 |
| FastAPI + Python 3.12 skeleton | Task 4 |
| Pydantic-settings config | Task 4 |
| SQLAlchemy 2 async engine | Task 4 |
| Alembic setup (no migrations yet — Phase 1) | Task 5 |
| ARQ worker skeleton | Task 5 |
| React 18 + Vite + TypeScript | Task 6 |
| Tailwind + shadcn/ui CSS variables | Task 6 |
| TanStack Query + React Router | Task 6 |
| Axios base instance with refresh interceptor | Task 6 |
| GitHub Actions: lint + test + docker build | Task 7 |
| `.env.example` with all required variables | Task 1 |
