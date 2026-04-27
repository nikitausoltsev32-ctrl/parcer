# ADR 0001 — Supabase + Upstash + без локального Docker

> Status: accepted
> Date: 2026-04-24

## Контекст
Первая итерация архитектуры предполагала локальный Postgres и Redis в Docker Compose и S3-совместимое хранилище (Selectel). У единственного разработчика ограниченная RAM и нежелание держать Docker-daemon локально. Supabase уже привычный инструмент и закрывает Postgres + Storage одним аккаунтом. Redis не хочется ставить отдельно.

## Решение
- Postgres и Storage — на Supabase (cloud).
- Redis — на Upstash (serverless, OpenAI-совместимый `rediss://` URL).
- Миграции — через Supabase CLI (`supabase/migrations/*.sql`), Alembic удалён.
- Локально Docker/Postgres/Redis **не** запускаются. Разработчик работает с cloud-ресурсами напрямую.
- `backend/Dockerfile`, `frontend/Dockerfile` остаются для будущего prod-деплоя на VPS, локально не используются.

## Последствия
- ➕ Локальная RAM < 1 GB, нет docker-daemon.
- ➕ Одна точка правды для схемы БД (файлы миграций + Supabase dashboard).
- ➕ MCP Supabase позволяет править БД из Claude Code.
- ➖ Требуется интернет для разработки.
- ➖ Все данные идут через TLS к cloud-провайдерам — warmup/latency не нулевые.
- ➖ Upstash free tier: 10 000 команд/день. На soft-launch может упереться, переход на Pay-as-you-go — ~$0.2/100k команд.
- ➖ Для прод-деплоя всё равно вернётся Docker Compose (api + worker + caddy на VPS); Postgres и Redis остаются cloud.

## Альтернативы отклонены
- **Локальный Docker:** загружает ПК, разработчик явно против.
- **Postgres в Supabase + Redis локально (WSL/brew):** меньше облачных зависимостей, но всё равно требует локальной настройки. Upstash выигрывает по простоте.
- **Полностью pg-очередь вместо Redis (pgmq):** уберёт Upstash, но требует миграции с ARQ на другую библиотеку и усложняет воркер.
