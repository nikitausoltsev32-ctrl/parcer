# PLAN.md — навигация для AI-агентов

> Где мы сейчас и что делаем. Читать ПЕРВЫМ, до CLAUDE.md.
> CLAUDE.md = правила и канон. PLAN.md = текущее состояние и задачи.

## Продукт (1 строка)
**Лида AI** — ИИ-агент поиска и квалификации B2B-лидов. SerpAPI/Yandex → краулер → Light/Deep AI → скоринг → outreach → CRM. Полный канон: CLAUDE.md.

## Карта кода (куда смотреть)
| Хочешь поменять | Файл |
|---|---|
| Pipeline поиска лидов (13 шагов) | `backend/app/services/leads/pipeline.py` |
| Понимание промта / ICP | `backend/app/services/leads/icp.py`, `icp_parser.py` |
| Генерация поисковых запросов | `backend/app/services/leads/query_gen.py` |
| Фильтр ICP (отсев кандидатов) | `backend/app/services/leads/icp_filter.py` |
| Чат-агент (tool-calling) | `backend/app/services/chat/agent.py`, `chat/tools.py` |
| LLM-роутинг по стадиям | `backend/app/services/llm/routing.py`, `factory.py` |
| Поиск (SerpAPI + Yandex) | `backend/app/services/search/` |
| Диагностика воронки | `backend/scripts/run_funnel_diagnostic.py`, `services/leads/funnel.py` |
| Фронт-чат | `frontend/src/pages/ChatPage.tsx`, `frontend/src/index.css` |

## Текущее состояние (обновлять при каждом мёрдже)
- LLM-роутинг: dev/MVP на иностранных моделях, Yandex первым приоритетом при наличии ключа. РФ-миграция (GigaChat, Sonar→флаг) — высокий приоритет до платного запуска.
- Воронка-диагностика готова (`funnel.py` + раннер). Базовые замеры: `backend/funnel.csv`, `funnel_50.csv`.

## АКТИВНЫЕ ЗАДАЧИ (ветка codex/settings-outreach-cleanup)
Статус: `[ ]` todo · `[~]` в работе · `[x]` готово

- [x] **T1. Плавные анимации фронта.** GPU-слой для свечений `body::before/::after` (`translateZ`+`will-change`+`contain:strict`), `prefers-reduced-motion`, убран `transition:all`. Файлы: `index.css`, `ChatPage/InboxPage/SetupWizard/OnboardingModal`. build+lint ✓.
- [x] **T2. Понимание промта в pipeline (главное).** Удалён хардкод `_MARBLE_*` из `icp.py`; добавлен общий LLM-разбор промта `icp_parser.py` (Шаг 0), подключён в `pipeline.py`, тесты `test_icp_parser.py`. ⚠️ Живой замер воронки НЕ запускался — нет `.env`/ключей. Оператор должен запустить funnel-раннер (см. ниже) для подтверждения «было/стало».
- [x] **T3. Сократить CLAUDE.md** — 791→300 строк, все правила/схема/промпты сохранены, статус переехал сюда.
- [x] **T4. PLAN.md для агентов** — этот файл.
- [x] **T5. Итоговый отчёт пользователю** — `docs/SESSION-REPORT.md`.

## Сделано в loop (после T1–T5)
- [x] **Агрегаторы.** `url_filter.BLOCKED_DOMAINS` стал единым каноном (medical + catalogs + соцсети/поисковики); `serp.py` импортирует его (`_AGGREGATOR_DOMAINS is BLOCKED_DOMAINS`) — два списка больше не расходятся. Тест `test_url_filter.py` (6 кейсов) ✓.

## Бэклог (выбирать по приоритету)
- Проверить, не режет ли `icp_filter.reject_by_icp` хорошие сайты при обобщённом (LLM) ICP — следующий пик.
- РФ-провайдеры: GigaChat, Yandex как дефолт, Sonar за флаг (CLAUDE.md §8).
- Карточки контакта/компании/кампании на фронте.
- Тарифные лимиты/квоты полностью в config/service.

## Как проверять лидов (обязательный замер перед/после изменений pipeline)
Из `backend/` (нужен `.env`: DATABASE_URL, SERPAPI_KEY, LLM-ключи):
```bash
python scripts/run_funnel_diagnostic.py --niche "<ниша>" --city "<город>" --limit 20 --csv funnel_after.csv
```
Смотреть: `saved`, `with_personal_email`, `score_70_plus`, распределение `serp`/`llm`.

## Команды
Backend (`backend/`): `pytest tests/ -v` · `ruff check .` · `uvicorn app.main:app --reload`
Frontend (`frontend/`): `npm run dev` · `npm run build` · `npm run lint`
