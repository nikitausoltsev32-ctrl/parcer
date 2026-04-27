.PHONY: help dev-api dev-worker dev-web test lint format migrate-new migrate-push migrate-pull migrate-reset seed types install

help:
	@echo "Targets:"
	@echo "  install          Install backend (editable) and frontend deps"
	@echo "  dev-api          Run FastAPI with --reload"
	@echo "  dev-worker       Run ARQ worker"
	@echo "  dev-web          Run Vite dev server"
	@echo "  test             Run backend pytest"
	@echo "  lint             Run ruff check"
	@echo "  format           Run ruff format"
	@echo "  migrate-new name=<name>  Create a new Supabase migration"
	@echo "  migrate-push     Apply migrations to linked Supabase project"
	@echo "  migrate-pull     Pull schema changes from Supabase dashboard"
	@echo "  migrate-reset    Drop and reapply all migrations"
	@echo "  seed             Re-run seed migration"
	@echo "  types            Generate TS types from FastAPI OpenAPI"

install:
	cd backend && pip install -e ".[dev]"
	npm install

dev:
	npm run dev

dev-api:
	cd backend && python -m uvicorn app.main:app --reload --port 8000


dev-worker:
	cd backend && python -m procrastinate --app app.workers.main.app worker

dev-web:
	cd frontend && npm run dev

test:
	cd backend && pytest tests/ -v

lint:
	cd backend && ruff check .

format:
	cd backend && ruff format .

migrate-new:
	supabase migration new $(name)

migrate-push:
	supabase db push

migrate-pull:
	supabase db pull

migrate-reset:
	supabase db reset

seed:
	supabase db push --include-all

types:
	cd frontend && npx openapi-typescript http://localhost:8000/api/v1/openapi.json -o src/lib/api-types.ts
