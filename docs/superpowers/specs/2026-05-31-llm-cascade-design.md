# Спецификация: LLM-каскад с роутингом по стадиям + прямой поиск лидов

Дата: 2026-05-31
Статус: утверждён, готов к написанию плана
Ветка: `codex/nemotron-progress`

## 1. Проблема

1. **Нет роутинга моделей.** В dev все LLM-стадии (`query_gen`, `light_ai`, `deep_ai`, `scoring`, `outreach`, `chat`, `letters`, `classify`, `enrich`) бьют в один `nvidia/z-ai/glm-5.1`. Нет привязки дешёвой модели к дешёвой задаче — деньги и латентность не оптимизированы.
2. **LLM-поиск построен на «памяти».** `services/search/llm_search.py` зовёт `get_llm_client("classify")` — обычную модель без веб-доступа, которая «вспоминает» компании из тренировочных данных. Промпт просит «не выдумывай URL», потом HEAD-валидация выкидывает галлюцинации. Источник ненадёжный, устаревший, не ищет по живому вебу.
3. **Нет страховки.** Если провайдер стадии отдаёт 429/500 — стадия падает (частично лечится retry-циклами в `pipeline.py`).

## 2. Цель

- Per-stage роутинг моделей через конфиг, fallback-ready (список `[primary, fallback]`).
- Подключить OpenRouter одним клиентом (OpenAI-совместимый) — открывает дешёвые модели и Perplexity Sonar одним ключом.
- Добавить **прямой поиск лидов LLM через Perplexity Sonar** (живой веб + цитаты) как полноценный источник.
- Сохранить NVIDIA и Groq как есть.
- Привести CLAUDE.md к реальности.

Не-цели (YAGNI): автоэскалация по confidence (только fallback по ошибке/отсутствию ключа); тарифные тиры в роутинге (заложить структуру, но не реализовывать сейчас); биллинг.

## 3. Архитектура

### 3.1 Провайдер OpenRouter
Новый `app/services/llm/openrouter.py`:
```python
class OpenRouterClient(LLMClient):
    base_url = "https://openrouter.ai/api/v1"
    def __init__(self, model: str):
        self.api_key = settings.openrouter_api_key
        self.model = model
```
`openrouter_api_key` уже есть в `config.py:46`. Ключ задаётся **только через env** (`.env`), хардкод запрещён (CLAUDE.md §2/§19). Регистрируется в `factory._OPENAI_PROVIDERS["openrouter"]`.

### 3.2 Таблица роутинга — `app/services/llm/routing.py`
Структура: `STAGE_ROUTING: dict[str, list[tuple[provider, model]]]`. Каждой стадии — упорядоченный список. `get_llm_client(task)` берёт первую запись, чей `*_api_key` непустой. Переопределение через env (`LLM_<STAGE>_PROVIDER` / `_MODEL` остаются как override верхнего приоритета для обратной совместимости).

| Стадия | primary | fallback |
|---|---|---|
| query_gen | openrouter `google/gemini-2.0-flash-001` | nvidia `z-ai/glm-5.1` |
| lead_discovery (новая) | openrouter `perplexity/sonar` | recall-llm_search (старый путь) |
| url_classify | openrouter `google/gemini-2.0-flash-8b` | groq `llama-3.3-70b-versatile` |
| light_ai | openrouter `deepseek/deepseek-chat` | nvidia `z-ai/glm-5.1` |
| deep_ai | openrouter `deepseek/deepseek-chat` | nvidia `z-ai/glm-5.1` |
| scoring | openrouter `openai/gpt-4o-mini` | groq `llama-3.3-70b-versatile` |
| outreach | openrouter `deepseek/deepseek-chat` | nvidia `z-ai/glm-5.1` |
| chat | nvidia `z-ai/glm-5.1` | openrouter `deepseek/deepseek-chat` |
| letters | nvidia `z-ai/glm-5.1` | openrouter `qwen/qwen-2.5-72b-instruct` |
| inbox_classify | openrouter `google/gemini-2.0-flash-8b` | nvidia `z-ai/glm-5.1` |

> Имена моделей и цены **сверить с openrouter.ai/models перед мерджем** (волатильны). Это отдельный шаг плана.

### 3.3 Прямой поиск лидов — `app/services/search/perplexity_search.py`
- Зовёт Sonar-модель (`lead_discovery` через роутинг).
- Промпт: «найди реальные действующие компании ниши {niche} в городе {city}, верни JSON с домом и источником». Sonar грунтуется на живом вебе.
- Возврат: `[{name, website, city, description, source: "perplexity"}]`, прогон через существующую HEAD-валидацию.
- Мёрджится в `search/__init__.py:search_companies` рядом с serp/google.
- Старый `llm_search` остаётся как **fallback** стадии `lead_discovery` (когда нет OpenRouter-ключа).

### 3.4 Поток данных
```
search_companies()
  ├─ serp (SerpAPI)        ─┐
  ├─ google (SerpAPI)      ─┤
  ├─ perplexity_search ←NEW─┤→ merge+dedup → URL filter → crawl → light/deep AI → ...
  └─ llm_search (fallback) ─┘
```

## 4. Дешёвые модели OpenRouter (анализ, май 2026)

| Модель | Цена (≈) | Сильна в | Куда |
|---|---|---|---|
| DeepSeek V3 (`deepseek/deepseek-chat`) | от ~$0.01–0.30/M | JSON/extraction, дёшево | light/deep/outreach |
| Gemini 2.0 Flash / Flash-8B | ~$0.075/M | скорость, дёшево | query_gen, url_classify, inbox |
| GPT-4o-mini | ~$0.15/M | надёжный JSON/tool-use | scoring |
| Qwen 2.5 72B | дёшево | русский язык | letters |
| Llama 3.3 70B (есть free) | free/дёшево | лёгкие задачи | только Free-тариф |
| Perplexity Sonar / sonar-pro | поиск | живой веб + цитаты | lead_discovery |
| Claude 3.5 Haiku / Sonnet | платно | качество | платные тиры (позже) |

Источники: openrouter.ai/pricing, costgoat.com/pricing/openrouter-free-models, promptcost.org/en/blog/openrouter-pricing-guide-2026.

## 5. Правки CLAUDE.md
- §8 Smart Model Routing — таблицу привести к фактическому роутингу + OpenRouter/Perplexity.
- §5 шаги 2/4 — отметить Perplexity lead_discovery как источник поиска.
- §16 — убрать `run_followup`/`run_reminders` из заглушек (реализованы); зафиксировать остаток (reminders/inbox-reply/templates API = 501).

## 6. Тестирование
- `tests/test_llm_factory.py` — роутинг: выбор primary при наличии ключа, переход на fallback при пустом ключе, env-override.
- `tests/test_search.py` — мердж perplexity-источника, дедуп по домену, HEAD-валидация (мок httpx).
- Без сетевых вызовов: LLM-клиенты и httpx мокаются.

## 7. Затрагиваемые файлы
- Новые: `llm/openrouter.py`, `llm/routing.py`, `search/perplexity_search.py`.
- Правки: `llm/factory.py`, `search/__init__.py`, `search/llm_search.py` (понизить в fallback), `core/config.py` (env-override стадий, опц.), `CLAUDE.md`, `.env.example`.
- Тесты: `test_llm_factory.py`, `test_search.py`.

## 8. Риски
- Имена/цены моделей OpenRouter меняются → шаг сверки перед мерджем.
- Sonar может вернуть нерелевантные/платные каталоги → опираемся на URL-filter (§3 пайплайна) + HEAD-валидацию.
- 152-ФЗ: OpenRouter/Perplexity — трансграничка (США). Требует `users.llm_consent_at` (механизм уже есть). Без согласия — стадия не зовётся.
