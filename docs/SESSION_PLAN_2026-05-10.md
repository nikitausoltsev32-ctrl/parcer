# SESSION PLAN 2026-05-10

## Статус

| ID | Задача | Исполнитель | Статус |
| --- | --- | --- | --- |
| A1 | run_followup | Codex | готово |
| A2 | run_reminders | Codex | готово |
| B1-B3 | Procrastinate jobs | Codex | готово* |
| B4 | API async mode | Claude | готово |
| C1-C2 | Rate limiting | Codex | готово |
| D1 | ContactPage | Claude | готово |
| D2 | CompanyPage | Claude | готово |
| E1 | E2E smoke test | Claude | не начато |
| F1-F4 | UI Rework | Claude | в работе |
| G1 | SERP pre-screening | Codex | готово |
| G2 | Email extraction улучшение | Codex | готово |
| G3 | Hook prompt Light AI | Codex | готово |
| H1-H2 | GLM 5.1 A/B анализ | Claude | не начато |

## GLM routing update

- `chat`, `letters`, `classify`, `enrich` переведены на `provider=nvidia`, `model=z-ai/glm-5.1`.
- Ключ используется из `NVIDIA_API_KEY`; отдельный `GLM_API_KEY` для этого маршрута не нужен.
- MiniMax/OpenRouter убран из списка доступных chat-моделей, потому что этот вариант больше не рабочий.

\* `light_ai_job`, `deep_ai_job`, `outreach_job` реализованы в `workers/main.py`. Контракт payload теперь поддерживает оба формата: вложенный `payload.data` и плоские поля верхнего уровня. Это закрывает риск, если jobs будут ставиться из pipeline/API по форме из старого трекера.

## Что уже не надо разбирать заново

- `run_followup`, `run_reminders`, `light_ai_job`, `deep_ai_job`, `outreach_job` уже есть.
- SlowAPI уже подключен, лимиты навешаны.
- `ContactPage` и `CompanyPage` уже созданы и зарегистрированы в роутинге.
- `/lead-search` уже async: `POST` возвращает `202 + log_id/status`, `GET /lead-search/{log_id}` читает статус из `lead_processing_logs`.
- `GET /lead-search/{log_id}` теперь отдает реальное `saved` из `meta.saved_leads`, а не число списанных AI credits.

## Что Codex закрыл в этом проходе

1. B1-B3 payload contract: jobs принимают и `payload.data`, и плоский payload.
2. G1: SERP pre-screening отсекает рейтинги/списки до crawler.
3. G2: HTML extraction понимает кириллическую obfuscation email вида `sales [собака] studio [точка] test`.
4. G3: Light AI prompt запрещает общий hook без конкретного факта из текста.

## Следующий порядок

1. Довести F1-F4 UI Rework по конкретному UI-спеку или текущим замечаниям пользователя.
2. Сделать E1 smoke: API + worker, `POST /api/v1/lead-search` для `стоматологии / Екатеринбург / limit=5`, проверить `lead_processing_logs`, `leads`, списание credits.
3. H1-H2 GLM 5.1 A/B анализ делать только после появления достаточного числа новых логов после GLM-5.1.

## Test Plan

- Backend после любых правок: `cd backend && uv run --python 3.12 --extra dev pytest tests/ -v`.
- Backend lint: `cd backend && uv run --python 3.12 --extra dev ruff check .`.
- Frontend после F-задач: `cd frontend && npm run build`.
- E2E smoke: запустить API + worker, сделать `POST /api/v1/lead-search` с `стоматологии / Екатеринбург / limit=5`, проверить `lead_processing_logs`, `leads`, списание credits.

## Проверено в этом проходе

- `uv run --python 3.12 --extra dev pytest tests/test_workers.py::test_lead_job_payload_data_supports_nested_and_flat_contracts tests/test_lead_extraction.py::test_extract_from_html_finds_cyrillic_obfuscated_email tests/test_lead_pipeline.py::test_run_lead_search_prescreens_serp_listicles_before_crawler tests/test_light_ai.py::test_run_light_ai_returns_company_description_from_json -v` -> `4 passed`.

## Ограничения

- Секреты не переносились в документ.
- Полный E2E smoke не выполнен: для него нужен запущенный API, worker и рабочие env-ключи.
- H1-H2 не стартуют без свежих логов после GLM-5.1.
