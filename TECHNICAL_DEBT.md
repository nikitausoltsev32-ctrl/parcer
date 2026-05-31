# Technical Debt

Last updated: 2026-05-31
Source: аудит ветки `codex/nemotron-progress` (uncommitted diff + новые файлы).

## Summary
**Всего находок**: 10 | Critical: 1 | High: 2 | Medium: 3 | Low: 4
**Исправлено в этом проходе**: 6 | **Осталось (решение/риск)**: 4

---

## ✅ Исправлено

### [CRITICAL] Вебхуки без аутентификации
- **Файл**: `backend/app/api/v1/webhooks.py`
- **Было**: `POST /webhooks/amocrm/{user_id}` без подписи → любой создаёт контакты и запускает `enrich_contact_task` (LLM-расход) без проверки кредитов.
- **Фикс**: обязательный `?token=` (HMAC через `core/tracking.verify_webhook_token`), единый 404 для неверного user/token (нет перебора), rate-limit `60/minute`, enrich только при `balance > 0`, общий `_ingest_lead`.
- **TODO**: выдавать ссылку вебхука с токеном в UI настроек интеграций; завести отдельную статью кредитов под enrichment.

### [HIGH] Квота `sends_quota` сгорала на неудачных отправках
- **Файл**: `backend/app/workers/main.py` (`send_email`)
- **Было**: декремент до SMTP-отправки; при ошибке не возвращался.
- **Фикс**: refund `sends_quota + 1` в `except`.
- **Осталось (см. ниже)**: `RetryStrategy(max_attempts=3)` неэффективен из-за guard `status != "pending"`.

### [HIGH] Отправка из чата сломана рассинхроном статусов
- **Файл**: `backend/app/services/chat/tools.py:583`
- **Было**: проверка `status != "generated"`, но новый флоу даёт `pending_approval → approved`.
- **Фикс**: проверка на `"approved"`.

### [MEDIUM] Silent failure через `print`
- **Файлы**: `backend/app/api/v1/contacts.py`, `backend/app/workers/main.py`
- **Фикс**: `logger.exception(...)` вместо `print(...)`.

### [MEDIUM] Мёртвый дубль `events` в pre-log
- **Файл**: `backend/app/services/leads/async_search.py`
- **Фикс**: убран `events` из конструктора `LeadProcessingLog` (сразу перезатирался).

### [LOW] Рассинхрон статуса в `update_message`
- **Файл**: `backend/app/api/v1/campaigns.py:134`
- **Фикс**: `("pending_approval", "generated")` → `"pending_approval"`.

---

## ⬜ Осталось — требует решения или несёт риск

### [HIGH] `send_email` retry неэффективен
- **Файл**: `backend/app/workers/main.py:178`
- Guard `if msg.status != "pending": return` на повторе видит `"failed"` и выходит — транзиентные SMTP-ошибки не переотправляются (предсуществующее поведение, не введено этим diff).
- **Варианты**: для транзиентных ошибок не ставить terminal `"failed"`, а пробрасывать исключение (статус остаётся `pending`); либо отдельный статус `retrying`. Требует решения по классификации ошибок.

### [MEDIUM] `effective_search_limit`: `fast_mode` стал мёртвым параметром
- **Файл**: `backend/app/services/leads/policy.py:44`
- `capped = capped_requested` — кап fast-режима (5) убран, fast-поиск тянет до 50.
- **Решение**: подтвердить намеренность (рост стоимости/времени). Если да — убрать параметр `fast_mode` из сигнатуры и вызовов; если нет — вернуть кап.

### [MEDIUM] Hunter отключён по умолчанию
- **Файл**: `backend/app/services/search/__init__.py:18` (`hunter: True → False`)
- Поиск email через Hunter выключен во всём пайплайне → меньше email у лидов.
- **Решение**: подтвердить, что это осознанная экономия, иначе включить выборочно по тарифу.

### [LOW] `backend/test_search.py` — scratch-скрипт в корне
- Хардкод "IT компании"/Москва, бьёт по реальной БД, имя не `test_*` (pytest не подберёт), дублирует `tests/test_search.py`.
- **Решение**: удалить или перенести в dev-скрипты (требует подтверждения на удаление).

### [LOW] `GET /companies` без `total` для пагинации
- **Файл**: `backend/app/api/v1/companies.py`
- Фронт не знает, есть ли следующая страница. Менять формат ответа рискованно (ломает `CompaniesPage`).
- **Решение**: вернуть `X-Total-Count` заголовком, либо `{items, total}` синхронно с фронтом.
