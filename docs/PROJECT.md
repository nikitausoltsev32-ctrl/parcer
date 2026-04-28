# PROJECT.md — единый документ проекта

> Этот файл — единственный источник правды по продукту и архитектуре. Обновляется в одном PR с любым изменением scope / БД / API / промптов / экранов. Остальные MD (ADR, legal drafts) — дополнения, не замена.

---

## 1. Позиционирование

**Продукт:** Лида AI — ИИ-агент по продажам для вашего бизнеса (РФ).

**Публичный бренд:** `Лида AI`. Короткое имя в интерфейсе и сообщениях — `Лида`. Старое кодовое имя `parcer` допустимо только в коде, репозитории и технических следах.

### Что продукт делает
- Помогает найти компании, которым полезен ваш оффер (через импорт CSV, публичные справочники, ручной ввод).
- Пишет персональные первые письма от имени пользователя.
- Ведёт клиентов: кому писали, кто ответил, что обсуждали, когда напомнить.
- Предлагает следующий шаг (follow-up, перенос на звонок, приоритизация лидов).

### Что продукт **НЕ** делает (явно в оферте и копии)
- Не продаёт базы контактов.
- Не парсит закрытые источники и защищённые данные.
- Не помогает отправлять спам.
- Не обходит спам-фильтры, не имитирует поведение.

### Целевая аудитория
- ИП и основатели микро/малого бизнеса (1–20 сотрудников).
- Фрилансеры B2B (маркетологи, дизайнеры, разработчики, юристы, бухгалтеры).
- Небольшие агентства без отдела продаж.
- Общий признак: нет опыта outreach, нет CRM, нет бюджета на западные SalesOS.

### Ценностное предложение
«Расскажите, кого ищете — Лида найдёт компании, напишет персональные письма и будет вести их вплоть до первого ответа. Вы остаётесь главным.»

### Юр-контур
- Все пользовательские данные хранятся в Supabase (РФ-регион, если доступно; иначе — с явным warning). 152-ФЗ.
- Письма, отправляемые через продукт, должны соответствовать ФЗ-38 ст. 18 «О рекламе» — продукт **обязывает** пользователя это соблюдать через UX: принудительный unsubscribe, лимиты отправки, warnings при импорте адресов физлиц.
- Для AI-функций данные о клиентах пользователя уходят в зарубежные LLM (Qwen — Alibaba/Китай, GLM — Zhipu/Китай, Groq — США). Пользователь даёт явное согласие отдельным чекбоксом при онбординге + упоминание в оферте.

---

## 2. Scope MVP

### IN SCOPE

**Чат как главный экран.** Инпут снизу + 3–4 quick actions («Найти клиентов», «Написать письма», «Посмотреть кампании», «Настройки»). Сообщения ассистента содержат интерактивные карточки (таблицы найденных лидов, превью писем, прогресс-бары, кнопки действий). Ассистент работает через tool-calling.

**Классический интерфейс параллельно.** Левое меню: Главная (=чат), Клиенты (CRM), Кампании, Шаблоны, Почтовые ящики, Настройки. Каждая операция доступна и из чата, и из классики.

**Conversational onboarding.** При первом входе ассистент в чате задаёт 3 вопроса про бизнес и сохраняет `business_profile`. Отдельной формы нет.

**Источники лидов:**
- CSV/XLSX импорт (автодетект колонок + превью). Основной путь.
- Ручное добавление одной записи.
- Через чат: «Найди студии дизайна в Казани» — AI предложит CSV или справочник (feature-flag 2ГИС).

**CRM-lite (память ассистента):**
- `companies` и `contacts` (one-to-many, контакт принадлежит компании).
- Статус: `new → contacted → replied → qualified → won / lost / cold`.
- `activities` — автозаполняется email-событиями + ручные заметки.
- Notes (free-text) на компанию и контакт.
- Next step (одно поле: дата + действие).
- `reminders` — email-напоминание в указанный момент.

**Inbox с AI-классификацией:**
- IMAP-чек каждые 15 мин (5 мин для активных кампаний первые 48 ч).
- AI-классификация: `interested` / `rejected` / `autoreply` / `question` / `unsubscribe` / `other`.
- В чате проактивно: «Алексей ответил положительно, что ответить?» + 2–3 варианта.

**AI-генерация писем:**
- 5 встроенных шаблонов: `cold_intro`, `service_pitch`, `followup`, `call_invite`, `partnership`.
- Тональности: formal / friendly / expert. Язык: ru.
- Массовая генерация через очередь; индивидуальная регенерация в чате.

**Рассылка:**
- SMTP пользователя (Яндекс/Gmail через app-password, custom).
- **Принудительный лимит: 30 писем/день на SMTP** (продуктовая защита от репутационного риска).
- Трекинг открытий (HMAC-подписанный tracking_id) и кликов.
- Unsubscribe принудительный, не отключается.
- Глобальные suppressions (отписался → никогда больше).

**AI follow-up engine:**
- Через 3 дня без ответа ассистент предлагает запустить follow-up волну. Только с ручным подтверждением.

**Учётка:**
- Email + пароль, verify через Unisender Go.
- Trial: 50 лидов + 50 отправок.
- ЮKassa подключается **после** Phase 6.

### OUT OF SCOPE (MVP)
- Канбан, кастомные pipeline, роли, команды, теги, сегменты.
- WhatsApp / Telegram / звонки.
- Прогрев ящиков, ротация доменов.
- Sequence из 3+ писем (только один follow-up).
- Парсеры закрытых источников.
- Голосовой ввод (проектируем, не реализуем).
- Мобильное приложение (только адаптив).
- Экспорт в amoCRM/Битрикс24 (только CSV).
- Google Search, Elasticsearch, Kubernetes.

### Критерии готовности MVP
1. Пользователь регистрируется, подтверждает email.
2. В чате рассказывает о бизнесе, ассистент сохраняет профиль.
3. Загружает CSV на 50 строк — видит превью в чате, подтверждает.
4. Просит «напиши письма» — AI генерит 50 за < 3 мин.
5. Подключает SMTP, отправляет. Видит прогресс в чате.
6. Через IMAP приходят ответы, AI классифицирует, предлагает ответы.
7. CRM автоматически обновляется (contact.status = replied), активности видны.
8. Может выгрузить CSV со статусами.

---

## 3. User flows (chat-first)

### Главный путь: от нуля до первого ответа
```
Регистрация (email+пароль) → verify → чат-онбординг (3 вопроса)
  ↓
[Чат]: «Нужны клиенты для дизайн-студии в Казани»
  ↓ AI предлагает: загрузить CSV / ввести вручную / 2ГИС (flag)
[Пользователь]: загружает CSV на 50 строк
  ↓ AI: показывает таблицу-карточку, валидирует email
[Пользователь]: «Напиши им письма»
  ↓ AI: «Какая тональность? Дружелюбная? Покажу шаблоны» → генерит 50
[Пользователь]: ревью, правка 3 писем
  ↓ AI: «Подключите SMTP, отправлю с лимитом 30/день»
[Пользователь]: подключает SMTP → подтверждает
  ↓ AI: отправляет, показывает прогресс в карточке кампании
...через 2 дня...
  ↓ AI: «Алексей ответил заинтересованно, спрашивает сроки. Варианты:»
```

### Вторичные flows
- **Повторная кампания:** в чате «сделай похожую для Москвы» — AI клонирует шаблон, просит новый список.
- **Подключение SMTP:** чат ведёт через выбор провайдера, инструкцию app-password, тестовое письмо.
- **Обработка ответов:** AI классифицирует + проактивно уведомляет в чате.
- **Экспорт:** в чате «выгрузи результаты» или на странице кампании кнопка.
- **Отписка получателя:** принудительная ссылка в каждом письме, глобальный suppression.

### Edge cases
| Сценарий | Поведение |
|---|---|
| CSV без колонки email | AI в чате: «Не вижу email, добавьте колонку или импорт по компаниям» |
| email невалидный | AI подсвечивает, предлагает пропустить |
| LLM 500/timeout | Retry 2x, потом AI пишет: «Задержка у AI-провайдера, попробуем через минуту» |
| SMTP отверг | Лид = failed, кампания продолжается |
| Превышен лимит тарифа | Остановить, AI предлагает апгрейд |
| Bounce | Email → suppressions, не слать повторно |
| >500 писем в CSV при квоте 50 | AI: «У вас квота 50, обработаю первые 50. Остальные — после апгрейда» |
| SMTP-аккаунт заблокирован middle-кампании | Кампания paused, AI в чате: «Ваш ящик заблокирован, проверьте в настройках Gmail» |

---

## 4. Карта экранов

Дизайн: минималистичный, синий + зелёный + белый, shadcn/ui.

### Публичные
- `/` — лендинг (hero, 3 шага, тарифы, FAQ, CTA).
- `/login`, `/register`, `/verify-email?token=...`, `/forgot-password`, `/reset-password?token=...`.
- `/t/u/{tracking_id}` — страница отписки.

### Приложение (общий layout, левое меню)
- `/app` — **чат** (главный).
- `/app/contacts` — таблица контактов (CRM).
- `/app/contacts/:id` — карточка контакта с таймлайном активностей.
- `/app/companies` — таблица компаний.
- `/app/companies/:id` — карточка компании + список контактов.
- `/app/inbox` — входящие с AI-классификацией, фильтры.
- `/app/campaigns` — список кампаний.
- `/app/campaigns/:id` — дашборд кампании (прогресс-бар, статы, таблица сообщений).
- `/app/templates` — встроенные + пользовательские.
- `/app/smtp` — почтовые ящики.
- `/app/settings/{profile,security,billing}` — настройки.

### Глобальные состояния
- Empty state на каждом списке с большим CTA «Спросите ассистента».
- Тосты для async («Генерирую письма, 2 мин»).
- Модалка подтверждения деструктива (удалить список, остановить кампанию).

### Адаптив
- `< 768px` — меню в нижнем баре, таблицы → карточки.
- `≥ 768px` — классический layout.

### НЕ рисуем в MVP
- Dark mode, мультиязычный UI, командные роли, конструктор sequence.

---

## 5. Архитектура

### Стек
- **Backend:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 async, Procrastinate (очередь).
- **Frontend:** React 18 + Vite + TypeScript, Tailwind, shadcn/ui, TanStack Query, React Router, SSE для чата.
- **Хранилища:** Supabase Postgres, Supabase Storage (bucket `parcer-<env>`).
- **LLM:** текущий dev chat — Groq `llama-3.3-70b-versatile`; Qwen/GLM остаются резервными провайдерами для отдельных задач.
- **Email:** SMTP/IMAP пользователя; транзакционные письма (verify, reset) через Unisender Go.
- **Биллинг:** ЮKassa, подключается после MVP.
- **Деплой:** VPS (Selectel/VK) + Caddy (TLS, static) — на prod. Локально: без Docker.

### Схема
```
          Пользователь (web)
                │ HTTPS
                ▼
          Caddy (prod)  /  Vite dev (local)
                │
        ┌───────┼──────────────┐
        ▼       ▼              ▼
   FastAPI API  React SPA      Static
        │
   ┌────┼───────────────────────────┐
   ▼    ▼                           ▼
Supabase                      LLM APIs (Groq, Qwen, GLM)
(PG+Storage)                  SMTP/IMAP (ящик юзера)
   │                          Unisender Go (transact)
   ▼
        Procrastinate workers
        ├─ chat_agent
        ├─ generate_letters
        ├─ send_email
        ├─ poll_inbox
        ├─ classify_inbox
        ├─ run_followup
        └─ run_reminders
```

### Безопасность
- Argon2 для паролей.
- JWT access (15 мин) + httpOnly refresh cookie (7 дней).
- SMTP-пароли юзера — Fernet-шифрование, ключ `FERNET_KEY` в env.
- HMAC-подписанный `tracking_id` (ключ `TRACKING_SECRET`). Пиксель/редирект принимают только валидные подписи.
- Rate-limit: `/auth/*` 10/min/IP, `/campaigns/*/send` 5/min/user, `/chat/*` 30/min/user.
- CSRF для cookie-сессий, SameSite=Lax, HSTS.
- RLS в Supabase: каждая таблица с `user_id` отфильтрована по JWT claim.
- Supabase service_role_key — только в бэкенде, не в браузере.

### Доставляемость email (рекомендации пользователю, обязательные в UI)
- SPF-запись: `v=spf1 include:_spf.<smtp_provider>.ru ~all`.
- DKIM: пользователь включает в настройках своего почтового провайдера.
- DMARC: `v=DMARC1; p=none; rua=mailto:...` как стартовая политика.
- Без этих записей массовая отправка уходит в спам. В UI — пошаговый гайд и проверка через публичные DNS-резолверы (`dns.google`).

### Лимиты SMTP-провайдеров (информационно в UI)
- Gmail (free): ~500 писем/день.
- Яндекс: ~300/день.
- Mail.ru: ~150/день.
- Custom SMTP: зависит.

Продукт ставит дефолт 30/день/ящик и позволяет увеличить до лимита провайдера после явного warning.

### Деплой (prod, будущее)
- VPS 4 vCPU / 8 GB / 80 GB SSD (Selectel/TimeWeb/VK Cloud).
- Docker Compose на VPS: `caddy` + `api` + `worker`. Postgres — Supabase, очереди — Procrastinate в Postgres.
- Образы из GHCR, push в registry через GitHub Actions.
- Бэкапы Postgres — через Supabase (point-in-time recovery на Pro).
- Логи — в Sentry + docker logs.

### Масштабирование (после 500 MAU)
- Разделить воркеры по типам задач.
- Supabase Pro / Postgres queue capacity.
- Supabase Pro.
- Горизонтальный скейл API через N uvicorn инстансов за Caddy.

---

## 6. Схема БД (Supabase Postgres)

Snake_case. PK — `uuid v4` (`gen_random_uuid()` в SQL, `uuid.uuid4()` в Python). Все пользовательские таблицы имеют `user_id` с RLS.

### users
| Поле | Тип | |
|---|---|---|
| id | uuid pk | |
| email | citext unique not null | |
| password_hash | text not null | argon2 |
| email_verified_at | timestamptz | |
| full_name | text | |
| business_profile | jsonb | `{business, offer, city, tone_default}` |
| llm_consent_at | timestamptz | согласие на трансграничную передачу |
| plan | text default 'trial' | |
| leads_quota | int default 50 | |
| sends_quota | int default 50 | |
| created_at / updated_at | timestamptz | |

### companies
| Поле | Тип | |
|---|---|---|
| id | uuid pk | |
| user_id | uuid fk users on delete cascade | |
| name | text not null | |
| website | text | |
| industry | text | |
| city | text | |
| size | text | `1-10 / 11-50 / 50+` |
| notes | text | |
| created_at / updated_at | timestamptz | |

### contacts (было `leads`)
| Поле | Тип | |
|---|---|---|
| id | uuid pk | |
| user_id | uuid fk | |
| company_id | uuid fk companies | nullable (одиночный контакт без компании тоже возможен) |
| list_id | uuid fk contact_lists | nullable |
| contact_name | text | |
| email | citext | |
| phone | text | |
| position | text | |
| status | text default 'new' | `new\|contacted\|replied\|qualified\|won\|lost\|cold` |
| next_step | text | |
| next_step_at | timestamptz | |
| email_valid | bool | |
| enrichment | jsonb | `{website_summary, fetched_at}` |
| raw | jsonb | исходная строка CSV |
| created_at | timestamptz | |

Индексы: `(user_id, status)`, `(company_id)`, `(email) where email is not null`.

### contact_lists (было `lead_lists`)
| Поле | Тип | |
|---|---|---|
| id | uuid pk | |
| user_id | uuid fk | |
| name | text | |
| source | text | `csv\|manual\|2gis` |
| source_meta | jsonb | |
| total_count | int | |
| created_at | timestamptz | |

### activities
| Поле | Тип | |
|---|---|---|
| id | uuid pk | |
| user_id | uuid fk | |
| contact_id | uuid fk | nullable |
| company_id | uuid fk | nullable |
| type | text | `email_sent\|email_opened\|email_clicked\|email_replied\|note\|call\|meeting\|status_change` |
| body | text | |
| meta | jsonb | |
| created_at | timestamptz | |

Индекс: `(contact_id, created_at desc)`, `(user_id, created_at desc)`.

### smtp_accounts
| Поле | Тип | |
|---|---|---|
| id | uuid pk | |
| user_id | uuid fk | |
| provider | text | `yandex\|gmail\|custom` |
| from_email | citext | |
| from_name | text | |
| host, port, username | text/int/text | |
| password_encrypted | bytea | Fernet |
| imap_host, imap_port | text/int | nullable |
| last_verified_at | timestamptz | |
| daily_limit | int default 30 | |
| is_active | bool default true | |

### suppressions
| Поле | Тип | |
|---|---|---|
| id | uuid pk | |
| user_id | uuid fk | |
| email | citext | |
| reason | text | `unsubscribe\|bounce\|manual` |
| created_at | timestamptz | |

Unique: `(user_id, email)`.

### templates
| Поле | Тип | |
|---|---|---|
| id | uuid pk | |
| user_id | uuid fk users (null = встроенный) | |
| name | text | |
| template_id | text | `cold_intro\|service_pitch\|...` |
| tone | text | |
| language | text default 'ru' | |
| custom_instruction | text | |

### campaigns
| Поле | Тип | |
|---|---|---|
| id | uuid pk | |
| user_id | uuid fk | |
| list_id | uuid fk contact_lists | |
| template_id | uuid fk templates | |
| smtp_account_id | uuid fk smtp_accounts | |
| llm_provider | text | `qwen\|glm\|groq` |
| llm_model | text | |
| send_rate_per_hour | int default 30 | |
| scheduled_at | timestamptz | |
| status | text | `draft\|generating\|ready\|sending\|paused\|done\|failed` |
| stats | jsonb | `{generated, sent, delivered, opened, clicked, replied, failed, unsub}` |
| created_at | timestamptz | |

### campaign_messages
| Поле | Тип | |
|---|---|---|
| id | uuid pk | |
| campaign_id | uuid fk | |
| contact_id | uuid fk | |
| subject | text | |
| body | text | |
| body_edited | bool default false | |
| status | text | `pending\|generated\|queued\|sent\|delivered\|opened\|clicked\|replied\|bounced\|failed\|skipped` |
| tracking_id | uuid unique | HMAC-подписанный (подпись = HMAC(tracking_secret, tracking_id)) |
| sent_at / opened_at / clicked_at / replied_at | timestamptz | |
| error | text | |

Индексы: `(campaign_id, status)`, `(tracking_id)` unique.

### inbox_messages
| Поле | Тип | |
|---|---|---|
| id | uuid pk | |
| user_id | uuid fk | |
| smtp_account_id | uuid fk | |
| campaign_id | uuid fk | nullable |
| contact_id | uuid fk | nullable |
| message_id | text | IMAP Message-ID |
| from_email | citext | |
| subject | text | |
| body_text | text | |
| received_at | timestamptz | |
| classification | text | `interested\|rejected\|autoreply\|question\|unsubscribe\|other` |
| classification_confidence | float | |
| raw | jsonb | сырое письмо |
| created_at | timestamptz | |

Индекс: `(user_id, received_at desc)`, `(campaign_id)`.

### chat_sessions
| Поле | Тип | |
|---|---|---|
| id | uuid pk | |
| user_id | uuid fk | |
| title | text | автогенерится из первого сообщения |
| started_at | timestamptz | |
| last_message_at | timestamptz | |

### chat_messages
| Поле | Тип | |
|---|---|---|
| id | uuid pk | |
| session_id | uuid fk | |
| role | text | `user\|assistant\|tool` |
| content | text | |
| tool_calls | jsonb | `[{name, args}]` |
| tool_results | jsonb | `[{name, result}]` |
| created_at | timestamptz | |

Индекс: `(session_id, created_at)`.

### reminders
| Поле | Тип | |
|---|---|---|
| id | uuid pk | |
| user_id | uuid fk | |
| contact_id | uuid fk | |
| remind_at | timestamptz | |
| action | text | |
| status | text | `pending\|sent\|dismissed` |
| created_at | timestamptz | |

Индекс: `(remind_at) where status='pending'`.

### events
| Поле | Тип | |
|---|---|---|
| id | bigserial pk | |
| message_id | uuid fk campaign_messages | nullable |
| campaign_id | uuid fk | nullable |
| user_id | uuid fk | nullable |
| type | text | `open\|click\|bounce\|reply\|unsub\|send_fail` |
| meta | jsonb | `{ua, ip_hash, link}` |
| created_at | timestamptz | |

### llm_cache
| Поле | Тип | |
|---|---|---|
| key | text pk | sha256(provider+model+system+user) |
| output | jsonb | |
| created_at | timestamptz | TTL 7 дней |

### token_store
| Поле | Тип | |
|---|---|---|
| token | text pk | verify/reset token |
| prefix | text | `verify_email\|reset_password` |
| value | text | user id |
| expires_at | timestamptz | |

### RLS-политики
Каждая таблица с `user_id`: `policy user_isolation for all using (user_id = auth.uid())`.

### Миграции
Ведутся через Supabase CLI. Файлы: `supabase/migrations/<ts>_<name>.sql`. Применение: `supabase db push`.

### Инварианты
- Контакты в `suppressions` исключаются при генерации и отправке.
- Отправлять можно только `campaigns.status = ready`.
- `campaigns.send_rate_per_hour` ≤ лимита тарифа.
- Квоты (`leads_quota`, `sends_quota`) декрементируются **атомарно**: `UPDATE users SET sends_quota = sends_quota - $1 WHERE id=$2 AND sends_quota >= $1 RETURNING *`. Если ничего не вернулось — квота исчерпана.

---

## 7. Структура API

REST + JSON, префикс `/api/v1`. Auth: `Authorization: Bearer <access>`, refresh — httpOnly cookie. Ошибки: `{"error": {"code", "message"}}`.

Текущий статус реализации: Auth и Chat частично рабочие; большинство CRM/Campaigns/Inbox/SMTP/Templates endpoints пока объявлены, но возвращают 501.

### Auth
- `POST /auth/register`
- `POST /auth/verify-email`
- `POST /auth/login`
- `POST /auth/refresh`
- `POST /auth/logout`
- `POST /auth/forgot-password`
- `POST /auth/reset-password`

### Me
- `GET /me` — профиль + квоты.
- `PATCH /me` — `full_name`, `business_profile`, `llm_consent_at`.

### Chat (SSE-стрим)
- `POST /chat/sessions` — создать сессию.
- `GET /chat/sessions` — список.
- `GET /chat/sessions/{id}/messages` — пагинация.
- `POST /chat/sessions/{id}/message` — отправить; ответ — SSE-стрим с токенами, tool-calls, tool-results.

### CRM
- `GET|POST /companies`, `PATCH|DELETE /companies/{id}`.
- `GET|POST /contacts`, `PATCH|DELETE /contacts/{id}`.
- `GET /contacts/{id}/activities`.
- `POST /contacts/{id}/notes`.
- `GET|POST /reminders`, `PATCH /reminders/{id}`.

### Списки
- `GET|POST /contact-lists`, `DELETE /contact-lists/{id}`.
- `POST /contact-lists/{id}/import-csv`.
- `POST /contact-lists/{id}/contacts` — ручное добавление.
- `GET /contact-lists/{id}/contacts`.
- `POST /contact-lists/{id}/validate-emails`.

### Источники
- `GET /sources` — enabled/disabled флаги.
- `POST /sources/2gis/search` (feature-flag).

### SMTP
- `GET|POST /smtp-accounts`, `PATCH|DELETE /smtp-accounts/{id}`.
- `POST /smtp-accounts/{id}/verify`.

### Templates
- `GET|POST /templates`, `PATCH|DELETE /templates/{id}`.

### Campaigns
- `GET|POST /campaigns`, `GET /campaigns/{id}`.
- `POST /campaigns/{id}/generate` — массовая генерация.
- `GET /campaigns/{id}/messages`, `PATCH /campaigns/{id}/messages/{mid}`.
- `POST /campaigns/{id}/messages/{mid}/regenerate`.
- `POST /campaigns/{id}/send`, `/pause`, `/resume`.
- `POST /campaigns/{id}/followup`.
- `GET /campaigns/{id}/stats`.
- `GET /campaigns/{id}/export.csv`.

### Inbox
- `GET /inbox` — фильтры по `classification`, `campaign_id`, `contact_id`.
- `POST /inbox/{id}/reply` — отправить ответ через тот же SMTP.
- `PATCH /inbox/{id}` — перезаписать классификацию вручную.

### Suppressions
- `GET|POST /suppressions`, `DELETE /suppressions/{email}`.

### Tracking (публично, без auth, HMAC-подписано)
- `GET /t/o/{tracking_id}.gif?sig=<hmac>` — 1×1 пиксель → `event open`.
- `GET /t/c/{tracking_id}?sig=<hmac>&url=<encoded>` — 302 redirect → `event click`.
- `GET /t/u/{tracking_id}?sig=<hmac>` — страница отписки → `event unsub`.

### Webhooks (prod)
- `POST /webhooks/yookassa` — биллинг.

### Пагинация
`?limit=50&cursor=<opaque>` → `{items, next_cursor}`.

### Rate-limits
- `/auth/*` 10/min/IP.
- `/campaigns/*/send` 5/min/user.
- `/chat/*` 30/min/user.
- Публичные `/t/*` без лимита.

### OpenAPI
`/api/docs`, типы на фронт через `openapi-typescript`.

---

## 8. Prompt specs

### 8.1. Chat-агент (Groq / Llama 3.3 70B, tool-calling)

**Системный промпт:**
```
Ты — Лида, ИИ-агент по продажам для бизнеса пользователя в России.
Помогаешь пользователю: искать компании-клиенты, писать персональные письма,
вести CRM, отвечать на входящие. Работаешь через вызов функций (tools).

Говоришь по-русски, кратко, без канцелярита и без штампов.
Когда у тебя достаточно данных — сразу действуй через tool. Не переспрашивай лишнего.
Когда не хватает данных — задай один точный вопрос.
Никогда не выдумывай факты о клиентах пользователя. Если данных нет — скажи.
Не упоминай, что ты AI или языковая модель.
В ответах предлагай следующий шаг кнопками/действиями, когда уместно.

Профиль пользователя:
- Бизнес: {business}
- Оффер: {offer}
- Город: {city}
- Тон по умолчанию: {tone_default}
```

**Tools (function calling):**
- `search_companies(query, city, limit)` → возвращает массив компаний из доступных источников.
- `import_csv_file(file_id)` → создаёт contact_list, возвращает превью.
- `list_contacts(filter)` → фильтры по статусу, кампании, дате последнего касания.
- `create_campaign(list_id, template, tone, smtp_account_id)` → campaign_id.
- `generate_letters(campaign_id)` → запускает async job, возвращает job_id + ETA.
- `send_campaign(campaign_id)` → стартует отправку.
- `pause_campaign(campaign_id)`, `resume_campaign(campaign_id)`.
- `check_inbox(filter)` → новые ответы с классификацией.
- `suggest_reply(inbox_message_id)` → 2–3 варианта ответа.
- `update_contact(contact_id, fields)` → статус, next_step, заметка.
- `add_note(contact_id, text)`.
- `set_reminder(contact_id, remind_at, action)`.
- `suggest_followups(campaign_id)` → список контактов для follow-up.

**Параметры:** temperature 0.4 (ниже для tool-use), max_tokens 1500, top_p 0.9, timeout 30s, retry 2x.

### 8.2. Генератор писем (Qwen 2.5 72B)

Короткое (80–140 слов) персонализированное email на русском.

**System:**
```
Ты — редактор холодных B2B-писем для малого бизнеса в России.
Пишешь по-русски, кратко, без канцелярита и штампов.
Не используешь эмодзи, восклицательных знаков не более одного.
Структура: 1 тема + приветствие + краткая причина контакта + ценностное предложение + мягкий вопрос-CTA.
Длина: {max_words} слов. Тема: до 60 знаков.
Тональность: {tone_ru}.
Если данных о лиде мало — пиши нейтрально, не выдумывай.
Никогда не упоминай, что письмо сгенерировано AI.
Отвечай ТОЛЬКО JSON вида {"subject": "...", "body": "..."} без Markdown.
```

Подстановки `tone_ru`:
- formal → «вежливый деловой»
- friendly → «дружелюбный, на «вы», но неформальный»
- expert → «экспертный, по делу, с конкретикой»

**User-промпт:**
```
Отправитель:
- Имя: {sender.name}
- Бизнес: {sender.business}
- Оффер: {sender.offer}
- Город: {sender.city}

Получатель:
- Компания: {contact.company_name}
- Контакт: {contact.contact_name or "—"}
- Сайт: {contact.website or "—"}
- Отрасль: {contact.industry or "—"}
- Город: {contact.city or "—"}
- Краткое о сайте (если спарсили): {contact.website_summary or "—"}

Задача: напиши письмо по шаблону "{template_name}".
{template_instruction}
```

**Шаблоны:**
| id | Название | template_instruction |
|---|---|---|
| cold_intro | Холодное знакомство | Познакомиться и предложить обсудить, как оффер может помочь. |
| service_pitch | Предложение услуги | Какую конкретную задачу решаешь, предложи бесплатный первый шаг. |
| followup | Follow-up | Мягко напомни, предложи созвон на 15 минут. |
| call_invite | Приглашение на звонок | Попроси 15 минут, укажи 2 слота. |
| partnership | Партнёрство | Предложи взаимовыгодное по аудитории. |

**Параметры:** temperature 0.7, max_tokens 450, top_p 0.9, stop `\n\n\n`, timeout 20s, retry 2x.

**Кэширование:** sha256(provider+model+system+user) → `llm_cache` на 7 дней.

**Валидация:**
1. Парсится JSON (иначе retry с «отвечай только JSON»).
2. `subject ≤ 80`, `body ≤ 1500`.
3. Не содержит: `как AI`, `как искусственный интеллект`, `я — языковая модель`.
4. Нет placeholder'ов `{{...}}`.

### 8.3. Классификатор inbox (Groq / Llama 3.1 8B Instant)

**System:**
```
Классифицируй входящее B2B-письмо на русском в одну из категорий:
- interested — человек заинтересован, хочет продолжить общение
- rejected — отказ, не нужно, не актуально
- autoreply — автоответ (отпуск, out of office)
- question — уточняющий вопрос (цена, сроки, условия)
- unsubscribe — просьба отписать
- other — ничего из вышеперечисленного

Ответь JSON: {"classification": "...", "confidence": 0.0-1.0}
```

**User:** тело полученного письма (обрезается до 1500 символов).

**Параметры:** temperature 0.1, max_tokens 50, timeout 10s.

### 8.4. Безопасность и приватность
- Данные контактов уходят в Qwen/Groq/GLM. Согласие пользователя обязательно (`users.llm_consent_at`).
- Без согласия — AI-функции заблокированы.
- В UI — явное упоминание: «при использовании AI данные обрабатываются зарубежными провайдерами».

---

## 9. LLM-провайдеры

| Задача | Провайдер | Модель | Почему |
|---|---|---|---|
| Chat-агент | Groq | `llama-3.3-70b-versatile` | Скорость (~500 tok/s), стабильный tool-use |
| Генерация писем | Qwen (DashScope) | `qwen2.5-72b-instruct` | Лучший русский, сильное instruction-following |
| Классификация inbox | Groq | `llama-3.1-8b-instant` | Лёгкая и быстрая |
| Fallback (все) | GLM (Zhipu) | `glm-4` | Backup при недоступности |

Все три провайдера имеют OpenAI-совместимый API → единый SDK `openai` с разными `base_url`/`api_key`.

**Config:**
```
LLM_CHAT_PROVIDER=groq
LLM_CHAT_MODEL=llama-3.3-70b-versatile
LLM_LETTERS_PROVIDER=qwen
LLM_LETTERS_MODEL=qwen2.5-72b-instruct
LLM_CLASSIFY_PROVIDER=groq
LLM_CLASSIFY_MODEL=llama-3.1-8b-instant
```

**Endpoints:**
- Groq: `https://api.groq.com/openai/v1`
- Qwen: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- GLM: `https://open.bigmodel.cn/api/paas/v4`

---

## 10. Roadmap

Горизонт: ~20 недель до платящих.

**Фаза 0 — Подготовка (1 нед):** бренд/домен, юр-форма, оферта/политика, репо+CI, Supabase+подписка на LLM-провайдеров, дизайнер на пол-ставки.

**Фаза 1 — Каркас и auth (2 нед):** миграции (users/companies/contacts/smtp/...), регистрация/логин/verify/reset, chat-layout, левое меню. **Веха:** логин работает.

**Фаза 2 — Импорт контактов (1.5 нед):** CSV, ручной ввод, валидация email (regex+MX), suppressions, unsubscribe. **Веха:** чистый список получается.

**Фаза 3 — Chat-агент + генерация (3 нед):** `LLMClient` Qwen/Groq/GLM, tool-calling, chat UI со streaming + интерактивные карточки, массовая генерация писем, превью/правка/регенерация. **Веха:** из 50 контактов — 50 писем за ~3 мин через разговор.

**Фаза 4 — Отправка + CRM + tracking (2.5 нед):** SMTP подключение, очередь send, HMAC-tracking, дашборд кампании, CRM-lite (статусы/activities/notes/next step). **Веха:** E2E отправка + статусы обновляются.

**Фаза 5 — Inbox + follow-up (1.5 нед):** IMAP-poll, AI-классификация, AI-suggest ответов, follow-up engine, reminders. **Веха:** ответы автоматически обрабатываются.

**Фаза 6 — Закрытая бета (2 нед):** 10–20 пилотов, итерации UX, лендинг. **Веха:** люди пользуются без поддержки.

**Фаза 7 — Платный запуск (2 нед):** ЮKassa, тарификация, история, public launch на VC/Habr. **Веха:** 5 платящих.

**Фаза 8+:** 2ГИС (когда ключ), Telegram как канал, amoCRM webhook, sequence, Yandex Search, Авито, AI-deep-analysis.

**Анти-задачи:** Google Search, WhatsApp, прогрев, мобильные нативы, Kubernetes.

---

## 11. Ближайшие шаги (1–2 недели)

**Продукт/право:**
- [ ] Финализировать бренд + купить домен.
- [ ] Юр-форма (самозанятый/ИП/ООО) для ЮKassa.
- [ ] Оферта, политика ПДн, согласие на обработку, согласие на трансграничную передачу в LLM — заполнить drafts в `docs/legal/`.

**Техника:**
- [ ] Прогнать Qwen/Groq/GLM на 10 тестах (письма на русском, классификация) → зафиксировать выбор.
- [ ] Supabase проект создан, `supabase link`, applying первой миграции.
- [ ] Procrastinate миграции применены и worker запускается.
- [ ] `make dev-api`, `make dev-worker`, `make dev-web` — работают локально.

**Дизайн:**
- [ ] Figma first-pass: лендинг + чат + классические экраны (CRM, Campaigns, Inbox) + SMTP-подключение.

**Решения, которые нельзя откладывать:**
1. LLM-провайдер №1 для писем (Qwen vs GLM) — прогнать на 10 тестах.
2. Бренд/домен/юр-форма — без них не запустить биллинг.
3. Политика ПДн + согласие на LLM-трансграничку — без них нельзя собирать юзеров.

---

## 12. Правила для AI-ассистента (Claude, Cursor, и т.п.)

- Отвечать по-русски, если вопрос по-русски.
- НЕ использовать слова «парсер», «скрапер», «база email», «массовая холодная рассылка» в копии продукта.
- НЕ предлагать Google Search, WhatsApp Business API, Kubernetes, Elasticsearch, прогрев доменов — вне scope.
- НЕ считать 2ГИС/Яндекс/Авито доступными по умолчанию — только под feature-flag.
- CSV-импорт — рабочий fallback при любых сомнениях о источнике.
- Не менять схему БД без новой миграции в `supabase/migrations/`.
- Не использовать Alembic — миграции через Supabase CLI.
- Не запускать локально Docker/Postgres/Redis — стек cloud-first.
- Бизнес-логика — в `backend/app/services/`, не в роутерах.
- Все внешние вызовы (LLM, SMTP, IMAP) — с таймаутом и retry.
- Секреты — только через env.
- При добавлении эндпоинта — обновить раздел 7 в этом файле.
- При изменении промптов — обновить раздел 8.
- При изменении БД — обновить раздел 6 + новую миграцию.
- При изменении flow — обновить разделы 3 и 4.
- Тесты: бизнес-логика сервисов (pytest). UI-тесты — только критический путь (опционально).
- Frontend: типы API — через `openapi-typescript`, не руками. Server state — только TanStack Query.

---

## 13. Как запустить локально

```bash
# один раз
npm i -g supabase
supabase login
supabase link --project-ref <ref>

# .env
cp .env.example .env
# заполнить SUPABASE_*, OPENROUTER_API_KEY или LLM API keys, SECRET_KEY, FERNET_KEY, TRACKING_SECRET

# миграции
supabase db push

# dev (3 терминала или make parallel)
make dev-api         # uvicorn app.main:app --reload
make dev-worker      # python -m procrastinate --app app.workers.main.app worker
make dev-web         # cd frontend && npm run dev
```

Память ПК: ~200 MB Python + ~300 MB Node. Никакого Docker-daemon.
