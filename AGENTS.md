# Repository Guidelines

## Project Structure & Module Organization

- `backend/app/`: FastAPI code; routers in `api/v1/`, models in `models/`, schemas in `schemas/`, services in `services/`, jobs in `workers/`.
- `backend/tests/`: pytest tests named `test_*.py`.
- `frontend/src/`: React pages in `pages/`, shared UI in `components/`, hooks in `features/`, API/auth helpers in `lib/`.
- `supabase/migrations/`: database migrations. Put all schema changes here.
- `docs/`: ADRs, testing notes, project notes, and legal documents.

## Build, Test, and Development Commands

- `make install`: install backend dev dependencies and frontend packages.
- `npm run dev`: run backend and frontend together.
- `make dev-api`, `make dev-web`, `make dev-worker`: run API, Vite UI, or worker separately.
- `make test`: run backend pytest.
- `make lint` / `make format`: run Ruff check or formatting.
- `cd frontend && npm run build`: type-check and build frontend.
- `cd frontend && npm run lint`: run frontend ESLint.
- `make migrate-new name=<name>` / `make migrate-push`: create or apply Supabase migrations.

## Coding Style & Naming Conventions

Backend targets Python 3.12. Use Ruff; line length is 120. Prefer typed Pydantic schemas, and keep route handlers thin by moving domain logic into `services/`.

Frontend uses TypeScript, React function components, Vite, and Tailwind. Use `PascalCase` for components/pages and `camelCase` for functions/variables.

## Testing Guidelines

Backend tests use pytest and `pytest-asyncio`. Add tests under `backend/tests/` as `test_<feature>.py`. Cover API behavior, service edge cases, and security-sensitive flows.

No frontend test runner is configured. For frontend changes, run `npm run lint` and `npm run build` from `frontend/`, then manually verify the affected flow.

## Commit & Pull Request Guidelines

Git history uses concise Conventional Commit-style prefixes: `feat:`, `fix:`, and `chore:`. Keep commits focused.

Pull requests should include a short summary, test results, linked issue/task when available, migration notes, and screenshots or recordings for UI changes.

## Security & Configuration Tips

Keep secrets in `.env`. Never commit provider keys, Supabase service role keys, SMTP credentials, or generated tokens. Full manual E2E checks may require external integrations.

## Agent-Specific Instructions

Be direct, factual, and sober when giving technical advice. Prefer repository patterns over broad rewrites, and call out uncertain assumptions instead of hiding them.

## Product & Tariff Source of Truth

- Main product source: `CLAUDE_ADDITIONAL.md`.
- Current tariff economics: section 7, version 3.1.
- Development and MVP may use free or cheap LLM models, but code must support production-routing by tariff.
- Do not hardcode tariff numbers inside business logic; keep limits and model routing in config/services.
- Do not promise 100% email or phone discovery. AI may improve confidence, but must not invent missing contact data.
