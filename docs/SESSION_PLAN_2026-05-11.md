# SESSION PLAN 2026-05-11

Дата: 2026-05-11 13:10:58 +05:00

## Что делал

1. Проверил `CLAUDE.md` и текущее состояние lead-search pipeline перед изменениями.
2. Выделил отдельный policy-слой для тарифных правил pipeline в `backend/app/services/leads/policy.py`.
3. Подключил этот policy в:
   - `backend/app/services/leads/crawler.py` для лимитов страниц по тарифу;
   - `backend/app/services/leads/async_search.py` для корректного `target_limit` уже на этапе постановки job;
   - `backend/app/services/leads/pipeline.py` для фактического cap по `leads_quota` и запрета deep AI на тарифах без deep.
4. Добавил тесты на:
   - ограничение поискового лимита квотой пользователя;
   - отключение deep AI на `trial`;
   - корректный `target` в async lead-search API.

## Что именно изменено

- Поиск больше не живёт только на локальном хардкоде внутри pipeline.
- `requested limit` теперь режется не только общим верхним порогом, но и `user.leads_quota`.
- Для `trial/free/starter` deep AI больше не должен запускаться, даже если light AI вернул `pass_to_deep_ai=true`.
- В `lead_processing_logs.meta` теперь сохраняется `deep_ai_allowed`, чтобы было проще дебажить реальное поведение тарифа.

## Что проверено

- Синтаксическая компиляция прошла:
  - `backend/app/services/leads/policy.py`
  - `backend/app/services/leads/crawler.py`
  - `backend/app/services/leads/async_search.py`
  - `backend/app/services/leads/pipeline.py`
  - `backend/tests/test_lead_pipeline.py`
  - `backend/tests/test_lead_search_api.py`

## Что нужно чекнуть

1. Запустить целевые тесты в рабочем Python 3.12 окружении:
   - `cd backend`
   - `uv run --python 3.12 --extra dev pytest tests/test_lead_pipeline.py -v`
   - `uv run --python 3.12 --extra dev pytest tests/test_lead_search_api.py -v`
2. Проверить живой сценарий `POST /api/v1/lead-search` для:
   - `trial/free/starter` — deep AI не должен уходить в `llm_calls`;
   - `pro/agency/max` — deep AI должен оставаться доступным.
3. Проверить кейс исчерпанной квоты `leads_quota = 0`.
   Сейчас это отдельно не закрыто и требует явного продуктового решения: блокировать поиск полностью или разрешать job без сохранения лидов нельзя.
4. Если этот policy подтверждается продуктово, следующий шаг — вынести оставшиеся anti-loss/tariff числа из `pipeline.py` в тот же слой, чтобы не плодить вторую точку правды.

## Ограничения этого прохода

- Полноценный `pytest` не смог запустить из текущей среды:
  - системный `python` без `pytest`;
  - `backend/.venv` привязан к недоступному `Python312`;
  - `uv run` упирается в сломанный cache/permission state на этой машине.
- Поэтому в этом проходе есть только статическая проверка и кодовые тест-кейсы, но нет честного зелёного runtime-прогона.
