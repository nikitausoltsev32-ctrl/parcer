# LLM-каскад: роутинг по стадиям + прямой поиск лидов — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Отмечай `[x]` после каждого выполненного шага — это защита от двойной работы. Перед началом задачи проверь, не отмечена ли она уже.**

**Goal:** Развести LLM-стадии пайплайна по дешёвым моделям через таблицу роутинга (fallback-ready), подключить OpenRouter одним клиентом и добавить прямой поиск лидов через Perplexity Sonar.

**Architecture:** Новый OpenAI-совместимый клиент `OpenRouterClient`. Таблица `STAGE_ROUTING` (стадия → `[(provider, model), ...]`), резолвер берёт первую запись с заданным ключом. `get_llm_client` для новых имён стадий ходит в роутинг, для легаси-тасков (`chat/letters/classify/enrich`) — без изменений. Поиск получает источник `perplexity_search` (живой веб), старый `llm_search` — fallback при отсутствии OpenRouter-ключа.

**Tech Stack:** Python 3.12, FastAPI, openai-python (AsyncOpenAI), httpx, pytest + pytest-asyncio. Ruff line 120.

**Спека:** `docs/superpowers/specs/2026-05-31-llm-cascade-design.md`

**Глобальные правила (CLAUDE.md):** секреты только через env (хардкод ключей запрещён); внешние вызовы с таймаутом; роутеры тонкие; не выдумывать данные. Отвечать по-русски.

**Отклонение от спеки:** стадия `scoring` детерминированная (`leads/scoring.py:score_candidate`, без LLM) — в роутинг НЕ заводим. Запись `scoring/gpt-4o-mini` из спеки опускаем как future-work.

---

## Файловая структура

- Create: `backend/app/services/llm/openrouter.py` — клиент OpenRouter (1 ответственность: транспорт).
- Create: `backend/app/services/llm/routing.py` — таблица стадий + резолвер (1 отв.: выбор модели).
- Create: `backend/app/services/search/perplexity_search.py` — поиск лидов через Sonar.
- Modify: `backend/app/services/llm/factory.py` — регистрация openrouter + ветка роутинга.
- Modify: `backend/app/services/leads/query_gen.py`, `url_classifier.py`, `light_ai.py`, `deep_ai.py`, `outreach.py` — реальные имена стадий.
- Modify: `backend/app/services/inbox/classifier.py` — стадия `inbox_classify`.
- Modify: `backend/app/services/search/__init__.py` — мердж perplexity / fallback на llm_search.
- Modify: `backend/.env.example`, `CLAUDE.md`.
- Test: `backend/tests/test_llm_routing.py` (новый), `backend/tests/test_llm_factory.py`, `backend/tests/test_search.py`.

---

## Phase 0 — OpenRouter-клиент + env

### Task 0.1: OpenRouter client

**Files:**
- Create: `backend/app/services/llm/openrouter.py`
- Test: `backend/tests/test_llm_factory.py`

- [ ] **Step 1: Написать падающий тест**

В `backend/tests/test_llm_factory.py` добавить:

```python
def test_openrouter_client_uses_openrouter_base_and_key(monkeypatch):
    from app.services.llm.openrouter import OpenRouterClient
    monkeypatch.setattr(settings, "openrouter_api_key", "or-test-key")
    client = OpenRouterClient(model="deepseek/deepseek-chat")
    assert client.base_url == "https://openrouter.ai/api/v1"
    assert client.api_key == "or-test-key"
    assert client.model == "deepseek/deepseek-chat"
```

- [ ] **Step 2: Запустить — убедиться, что падает**

Run: `pytest tests/test_llm_factory.py::test_openrouter_client_uses_openrouter_base_and_key -v`
Expected: FAIL — `ModuleNotFoundError: app.services.llm.openrouter`

- [ ] **Step 3: Реализация**

Создать `backend/app/services/llm/openrouter.py`:

```python
from app.core.config import settings
from app.services.llm.base import LLMClient


class OpenRouterClient(LLMClient):
    base_url = "https://openrouter.ai/api/v1"

    def __init__(self, model: str):
        self.api_key = settings.openrouter_api_key
        self.model = model
```

- [ ] **Step 4: Запустить — PASS**

Run: `pytest tests/test_llm_factory.py::test_openrouter_client_uses_openrouter_base_and_key -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/llm/openrouter.py backend/tests/test_llm_factory.py
git commit -m "feat(llm): add OpenRouter client"
```

### Task 0.2: .env.example

**Files:**
- Modify: `backend/.env.example`

- [ ] **Step 1: Добавить переменную**

Найти блок LLM-ключей в `backend/.env.example` (рядом с `NVIDIA_API_KEY`) и добавить строку, если её нет:

```
# OpenRouter — даёт дешёвые модели + Perplexity Sonar одним ключом
OPENROUTER_API_KEY=
```

- [ ] **Step 2: Commit**

```bash
git add backend/.env.example
git commit -m "chore(env): document OPENROUTER_API_KEY"
```

---

## Phase 1 — Таблица роутинга + резолвер

### Task 1.1: routing.py с резолвером

**Files:**
- Create: `backend/app/services/llm/routing.py`
- Test: `backend/tests/test_llm_routing.py`

- [ ] **Step 1: Написать падающие тесты**

Создать `backend/tests/test_llm_routing.py`:

```python
from app.core.config import settings
from app.services.llm.routing import STAGE_ROUTING, provider_has_key, resolve_stage


def test_resolve_uses_primary_when_its_key_present(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", "or-key")
    monkeypatch.setattr(settings, "nvidia_api_key", "nv-key")
    assert resolve_stage("light_ai") == ("openrouter", "deepseek/deepseek-chat")


def test_resolve_falls_back_when_primary_key_missing(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", "")
    monkeypatch.setattr(settings, "nvidia_api_key", "nv-key")
    assert resolve_stage("light_ai") == ("nvidia", "z-ai/glm-5.1")


def test_resolve_returns_last_when_nothing_configured(monkeypatch):
    for attr in ("openrouter_api_key", "nvidia_api_key", "groq_api_key"):
        monkeypatch.setattr(settings, attr, "")
    provider, model = resolve_stage("url_classify")
    assert (provider, model) == STAGE_ROUTING["url_classify"][-1]


def test_provider_has_key_reads_settings(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "")
    assert provider_has_key("groq") is False
    monkeypatch.setattr(settings, "groq_api_key", "g")
    assert provider_has_key("groq") is True
```

- [ ] **Step 2: Запустить — FAIL**

Run: `pytest tests/test_llm_routing.py -v`
Expected: FAIL — `ModuleNotFoundError: app.services.llm.routing`

- [ ] **Step 3: Реализация**

Создать `backend/app/services/llm/routing.py`:

```python
from app.core.config import settings

# provider -> атрибут settings с API-ключом
_PROVIDER_KEY_ATTR = {
    "openrouter": "openrouter_api_key",
    "nvidia": "nvidia_api_key",
    "groq": "groq_api_key",
    "qwen": "qwen_api_key",
    "glm": "glm_api_key",
    "claude": "anthropic_api_key",
}

# Стадия -> упорядоченный список [(provider, model)].
# Резолвер берёт первую запись, чей ключ задан. Имена/цены моделей OpenRouter
# СВЕРИТЬ на openrouter.ai/models перед мерджем (волатильны).
STAGE_ROUTING: dict[str, list[tuple[str, str]]] = {
    "query_gen":      [("openrouter", "google/gemini-2.0-flash-001"), ("nvidia", "z-ai/glm-5.1")],
    "lead_discovery": [("openrouter", "perplexity/sonar"), ("nvidia", "z-ai/glm-5.1")],
    "url_classify":   [("openrouter", "google/gemini-2.0-flash-8b"), ("groq", "llama-3.3-70b-versatile"), ("nvidia", "z-ai/glm-5.1")],
    "light_ai":       [("openrouter", "deepseek/deepseek-chat"), ("nvidia", "z-ai/glm-5.1")],
    "deep_ai":        [("openrouter", "deepseek/deepseek-chat"), ("nvidia", "z-ai/glm-5.1")],
    "outreach":       [("openrouter", "deepseek/deepseek-chat"), ("nvidia", "z-ai/glm-5.1")],
    "inbox_classify": [("openrouter", "google/gemini-2.0-flash-8b"), ("nvidia", "z-ai/glm-5.1")],
}


def provider_has_key(provider: str) -> bool:
    attr = _PROVIDER_KEY_ATTR.get(provider)
    return bool(attr and getattr(settings, attr, ""))


def resolve_stage(stage: str) -> tuple[str, str]:
    chain = STAGE_ROUTING[stage]
    for provider, model in chain:
        if provider_has_key(provider):
            return provider, model
    return chain[-1]
```

- [ ] **Step 4: Запустить — PASS**

Run: `pytest tests/test_llm_routing.py -v`
Expected: PASS (4 теста)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/llm/routing.py backend/tests/test_llm_routing.py
git commit -m "feat(llm): add per-stage model routing table with fallback"
```

### Task 1.2: factory ходит в роутинг

**Files:**
- Modify: `backend/app/services/llm/factory.py`
- Test: `backend/tests/test_llm_factory.py`

- [ ] **Step 1: Написать падающие тесты**

В `backend/tests/test_llm_factory.py` добавить:

```python
def test_stage_routing_picks_openrouter_for_light_ai(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", "or-key")
    monkeypatch.setattr(settings, "nvidia_api_key", "nv-key")
    client = get_llm_client("light_ai")
    assert client.base_url == "https://openrouter.ai/api/v1"
    assert client.model == "deepseek/deepseek-chat"


def test_stage_routing_falls_back_to_nvidia_without_openrouter(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", "")
    monkeypatch.setattr(settings, "nvidia_api_key", "nv-key")
    client = get_llm_client("light_ai")
    assert client.model == "z-ai/glm-5.1"


def test_legacy_task_classify_unchanged(monkeypatch):
    # Легаси-таски не входят в STAGE_ROUTING и читают settings.llm_classify_*
    client = get_llm_client("classify")
    assert client.model == "z-ai/glm-5.1"
```

- [ ] **Step 2: Запустить — FAIL**

Run: `pytest tests/test_llm_factory.py::test_stage_routing_picks_openrouter_for_light_ai -v`
Expected: FAIL — `ValueError: Unknown LLM provider` или `AttributeError: llm_light_ai_provider` (стадии нет в settings).

- [ ] **Step 3: Реализация**

Заменить содержимое `backend/app/services/llm/factory.py` на:

```python
from app.core.config import settings
from app.services.llm.base import LLMClient
from app.services.llm.glm import GLMClient
from app.services.llm.glm_nvidia import GLMNvidiaClient
from app.services.llm.groq import GroqClient
from app.services.llm.openrouter import OpenRouterClient
from app.services.llm.qwen import QwenClient
from app.services.llm.routing import STAGE_ROUTING, resolve_stage

_OPENAI_PROVIDERS = {
    "groq": GroqClient,
    "qwen": QwenClient,
    "glm": GLMClient,
    "nvidia": GLMNvidiaClient,
    "openrouter": OpenRouterClient,
}

CHAT_MODEL_OPTIONS = [
    {
        "id": "nvidia/z-ai/glm-5.1",
        "label": "GLM 5.1",
        "sub": "NVIDIA",
        "provider": "nvidia",
        "model": "z-ai/glm-5.1",
        "api_key_setting": "nvidia_api_key",
    },
    {
        "id": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
        "label": "Nemotron 3 Nano Omni 30B",
        "sub": "NVIDIA reasoning",
        "provider": "nvidia",
        "model": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
        "api_key_setting": "nvidia_api_key",
        "thinking": True,
    },
]

_CHAT_MODEL_BY_ID = {option["id"]: option for option in CHAT_MODEL_OPTIONS}


def get_available_chat_models() -> list[dict[str, str]]:
    return [
        {"id": option["id"], "label": option["label"], "sub": option["sub"]}
        for option in CHAT_MODEL_OPTIONS
        if getattr(settings, option["api_key_setting"], "")
    ]


def is_available_model_override(model_id: str | None) -> bool:
    if not model_id:
        return True
    option = _CHAT_MODEL_BY_ID.get(model_id)
    return bool(option and getattr(settings, option["api_key_setting"], ""))


def get_llm_client(task: str, *, model_override: str | None = None) -> LLMClient:
    """task: legacy 'chat'|'letters'|'classify'|'enrich' или стадия из STAGE_ROUTING."""
    thinking = None

    if model_override:
        option = _CHAT_MODEL_BY_ID.get(model_override)
        if not option:
            raise ValueError(f"Unsupported LLM model override: {model_override}")
        if not getattr(settings, option["api_key_setting"], ""):
            raise ValueError(f"LLM model override is not configured: {model_override}")
        provider = option["provider"]
        model = option["model"]
        thinking = option.get("thinking")
    elif task in STAGE_ROUTING:
        provider, model = resolve_stage(task)
    else:
        provider = getattr(settings, f"llm_{task}_provider")
        model = getattr(settings, f"llm_{task}_model")

    if provider == "claude":
        from app.services.llm.claude import ClaudeClient
        return ClaudeClient(model=model)

    cls = _OPENAI_PROVIDERS.get(provider)
    if not cls:
        raise ValueError(f"Unknown LLM provider: {provider}")
    kwargs = {}
    if provider == "nvidia" and thinking is not None:
        kwargs["thinking"] = thinking
    return cls(model=model, **kwargs)
```

> Примечание: ветка `thinking` сохранена для nemotron-override (см. существующий `test_nemotron_override_uses_nvidia_reasoning_client`). Поведение легаси-тасков и override не изменилось.

- [ ] **Step 4: Запустить весь файл тестов — PASS**

Run: `pytest tests/test_llm_factory.py -v`
Expected: PASS (включая старые тесты про nemotron/доступные модели).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/llm/factory.py backend/tests/test_llm_factory.py
git commit -m "feat(llm): route stage names through STAGE_ROUTING in factory"
```

---

## Phase 2 — Развести стадии пайплайна по реальным именам

> Каждый шаг — точечная замена строки `get_llm_client(...)`. Поведение при отсутствии OpenRouter-ключа не меняется (fallback на nvidia GLM-5.1).

### Task 2.1: query_gen → "query_gen"

**Files:**
- Modify: `backend/app/services/leads/query_gen.py:64`

- [ ] **Step 1: Заменить**

Было:
```python
    client = get_llm_client("classify", model_override=model_override)
```
Стало:
```python
    client = get_llm_client("query_gen", model_override=model_override)
```

- [ ] **Step 2: Прогон относящихся тестов**

Run: `pytest tests/test_query_gen.py -v`
Expected: PASS (тесты мокают LLM-вызов; имя стадии резолвится в nvidia GLM без OR-ключа).

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/leads/query_gen.py
git commit -m "refactor(leads): query_gen uses query_gen routing stage"
```

### Task 2.2: url_classifier → "url_classify"

**Files:**
- Modify: `backend/app/services/leads/url_classifier.py:41`

- [ ] **Step 1: Заменить**

Было: `client = get_llm_client("classify", model_override=model_override)`
Стало: `client = get_llm_client("url_classify", model_override=model_override)`

- [ ] **Step 2: Прогон**

Run: `pytest tests/ -k "url" -v`
Expected: PASS (или no tests collected — тогда `pytest tests/test_search.py tests/test_lead_pipeline.py -v`).

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/leads/url_classifier.py
git commit -m "refactor(leads): url_classifier uses url_classify routing stage"
```

### Task 2.3: light_ai → "light_ai"

**Files:**
- Modify: `backend/app/services/leads/light_ai.py:91`

- [ ] **Step 1: Заменить**

Было: `client = get_llm_client("classify", model_override=model_override)`
Стало: `client = get_llm_client("light_ai", model_override=model_override)`

- [ ] **Step 2: Прогон**

Run: `pytest tests/test_light_ai.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/leads/light_ai.py
git commit -m "refactor(leads): light_ai uses light_ai routing stage"
```

### Task 2.4: deep_ai → "deep_ai"

**Files:**
- Modify: `backend/app/services/leads/deep_ai.py:73`

- [ ] **Step 1: Заменить**

Было: `client = get_llm_client("letters")`
Стало: `client = get_llm_client("deep_ai")`

- [ ] **Step 2: Прогон**

Run: `pytest tests/test_lead_pipeline.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/leads/deep_ai.py
git commit -m "refactor(leads): deep_ai uses deep_ai routing stage"
```

### Task 2.5: outreach → "outreach"

**Files:**
- Modify: `backend/app/services/leads/outreach.py:40`

- [ ] **Step 1: Заменить**

Было: `client = get_llm_client("letters")`
Стало: `client = get_llm_client("outreach")`

- [ ] **Step 2: Прогон**

Run: `pytest tests/test_lead_pipeline.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/leads/outreach.py
git commit -m "refactor(leads): outreach uses outreach routing stage"
```

### Task 2.6: inbox classifier → "inbox_classify"

**Files:**
- Modify: `backend/app/services/inbox/classifier.py:21`

- [ ] **Step 1: Заменить**

Было: `client = get_llm_client("classify")`
Стало: `client = get_llm_client("inbox_classify")`

- [ ] **Step 2: Прогон**

Run: `pytest tests/ -k "inbox or worker" -v`
Expected: PASS (или no tests collected — тогда `pytest tests/test_workers.py -v`).

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/inbox/classifier.py
git commit -m "refactor(inbox): classifier uses inbox_classify routing stage"
```

---

## Phase 3 — Прямой поиск лидов через Perplexity Sonar

### Task 3.1: perplexity_search.py

**Files:**
- Create: `backend/app/services/search/perplexity_search.py`
- Test: `backend/tests/test_search.py`

- [ ] **Step 1: Написать падающий тест**

В `backend/tests/test_search.py` добавить (мокаем LLM-вызов и HEAD-валидацию — без сети):

```python
import pytest
from app.services.llm.base import LLMResult


@pytest.mark.asyncio
async def test_perplexity_search_parses_and_tags_source(monkeypatch):
    from app.services.search import perplexity_search as ps

    async def fake_logged_chat(*args, **kwargs):
        return LLMResult(
            content='{"companies":[{"name":"ООО Тест","website":"https://test.ru","city":"Москва","description":"d"}]}'
        )

    async def fake_head_validate(companies):
        return companies  # пропускаем сетевую проверку

    monkeypatch.setattr(ps, "logged_chat", fake_logged_chat)
    monkeypatch.setattr(ps, "_head_validate", fake_head_validate)

    out = await ps.perplexity_search_companies("стоматологии", "Москва", count=5)
    assert out == [
        {"name": "ООО Тест", "website": "https://test.ru", "city": "Москва",
         "description": "d", "source": "perplexity"}
    ]
```

- [ ] **Step 2: Запустить — FAIL**

Run: `pytest tests/test_search.py::test_perplexity_search_parses_and_tags_source -v`
Expected: FAIL — `ModuleNotFoundError: app.services.search.perplexity_search`

- [ ] **Step 3: Реализация**

Создать `backend/app/services/search/perplexity_search.py`:

```python
"""Прямой поиск лидов через Perplexity Sonar (живой веб + цитаты).

В отличие от llm_search (модель «вспоминает» компании из памяти), Sonar
ищет по актуальному вебу. URL всё равно HEAD-валидируются перед краулом.
"""
from __future__ import annotations

import json
import logging

from app.services.llm.base import LLMMessage
from app.services.llm.factory import get_llm_client
from app.services.llm.logged import LoggedLLMCall, logged_chat
from app.services.search.llm_search import _head_validate

logger = logging.getLogger(__name__)

_PROMPT = """\
Найди {count} реальных действующих компаний из ниши "{niche}" в городе "{city}".
Ищи по актуальному вебу. Только официальные сайты компаний — не агрегаторы,
не каталоги, не статьи. Для каждой компании укажи рабочий домен.

Отвечай строго JSON без markdown:
{{"companies":[{{"name":"...","website":"https://...","city":"...","description":"..."}}]}}"""


async def perplexity_search_companies(
    niche: str,
    city: str | None,
    count: int = 15,
    log: LoggedLLMCall | None = None,
) -> list[dict]:
    client = get_llm_client("lead_discovery")
    prompt = _PROMPT.format(count=count, niche=niche, city=city or "России")
    dummy_log = log or LoggedLLMCall()
    try:
        result = await logged_chat(
            client,
            [LLMMessage(role="user", content=prompt)],
            stage="lead_discovery",
            log=dummy_log,
            temperature=0.2,
            max_tokens=1024,
            timeout=30.0,
        )
    except Exception as exc:
        logger.warning("perplexity_search: LLM call failed: %r", exc)
        return []

    text = (result.content or "").strip()
    if text.startswith("```"):
        text = text.split("```")[1].lstrip("json").strip()
    try:
        companies = json.loads(text).get("companies", [])
        if not isinstance(companies, list):
            return []
    except Exception:
        logger.warning("perplexity_search: bad JSON: %r", text[:200])
        return []

    candidates = [
        {**c, "source": "perplexity"}
        for c in companies
        if isinstance(c, dict) and isinstance(c.get("website"), str) and c["website"].startswith("http")
    ]
    if not candidates:
        return []
    return await _head_validate(candidates)
```

> Примечание: `response_format={"type":"json_object"}` НЕ передаём — Sonar-модели его не поддерживают; парсинг JSON делается вручную (с защитой от markdown-обёртки).

- [ ] **Step 4: Запустить — PASS**

Run: `pytest tests/test_search.py::test_perplexity_search_parses_and_tags_source -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/search/perplexity_search.py backend/tests/test_search.py
git commit -m "feat(search): add Perplexity Sonar lead discovery source"
```

### Task 3.2: Мердж в search_companies + fallback на llm_search

**Files:**
- Modify: `backend/app/services/search/__init__.py`
- Test: `backend/tests/test_search.py`

- [ ] **Step 1: Написать падающий тест**

В `backend/tests/test_search.py` добавить:

```python
@pytest.mark.asyncio
async def test_search_uses_perplexity_when_openrouter_key_present(monkeypatch):
    from app.services import search as search_pkg
    from app.core.config import settings

    monkeypatch.setattr(settings, "openrouter_api_key", "or-key")

    async def fake_serp(*a, **k): return []
    async def fake_google(*a, **k): return []
    async def fake_perplexity(niche, city, count):
        return [{"name": "P", "website": "https://p.ru", "source": "perplexity"}]
    async def fake_llm(niche, city, count):
        raise AssertionError("llm_search must not be used when OpenRouter key is set")

    monkeypatch.setattr(search_pkg, "search_serp", fake_serp)
    monkeypatch.setattr(search_pkg, "search_google", fake_google)
    monkeypatch.setattr(search_pkg, "perplexity_search_companies", fake_perplexity)
    monkeypatch.setattr(search_pkg, "llm_search_companies", fake_llm)

    out = await search_pkg.search_companies("ниша", "Москва", limit=10, enrich=False, hunter=False)
    assert any(r.get("source") == "perplexity" for r in out)
```

- [ ] **Step 2: Запустить — FAIL**

Run: `pytest tests/test_search.py::test_search_uses_perplexity_when_openrouter_key_present -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'perplexity_search_companies'` (импорт ещё не добавлен).

- [ ] **Step 3: Реализация**

В `backend/app/services/search/__init__.py`:

(а) Добавить импорты вверху (рядом с существующими):
```python
from app.services.llm.routing import provider_has_key
from app.services.search.perplexity_search import perplexity_search_companies
```

(б) Заменить блок `asyncio.gather(...)` (строки ~26-30) на:
```python
    discovery = (
        _safe_perplexity(niche or query, city, min(fetch, 20))
        if provider_has_key("openrouter")
        else _safe_llm_search(niche or query, city, min(fetch, 20))
    )
    maps_results, google_results, llm_results = await asyncio.gather(
        _safe_serp(query, city, fetch),
        _safe_google(query, city, fetch),
        discovery,
    )
```

(в) Добавить хелпер рядом с `_safe_llm_search`:
```python
async def _safe_perplexity(niche: str, city: str | None, count: int) -> list[dict]:
    try:
        return await perplexity_search_companies(niche, city, count)
    except Exception as exc:
        logger.warning("search_companies: perplexity failed: %r", exc)
        return []
```

- [ ] **Step 4: Запустить — PASS**

Run: `pytest tests/test_search.py -v`
Expected: PASS (новый тест + существующие).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/search/__init__.py backend/tests/test_search.py
git commit -m "feat(search): prefer Perplexity discovery, llm_search as fallback"
```

---

## Phase 4 — Документация

### Task 4.1: Обновить CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: §8 Smart Model Routing**

Заменить таблицу «Dev/MVP» так, чтобы отражать фактический роутинг по стадиям через `STAGE_ROUTING` (query_gen→gemini-flash, light/deep/outreach→deepseek, url_classify/inbox→gemini-flash-8b, lead_discovery→perplexity/sonar), с примечанием: «Источник правды — `backend/app/services/llm/routing.py`. Без OpenRouter-ключа всё падает в fallback nvidia GLM-5.1». Добавить OpenRouter в список endpoints провайдеров: `OpenRouter: https://openrouter.ai/api/v1`.

- [ ] **Step 2: §5 шаги 2 и 4**

В STEP 2 (Search Module) добавить источник: «+ Perplexity Sonar (LLM live web discovery)». Уточнить, что LLM теперь ищет лиды напрямую, а не только генерирует запросы.

- [ ] **Step 3: §16 статус**

Убрать `run_followup` и `run_reminders` из «Заглушки / не реализовано» (они реализованы в `workers/main.py`). Оставить реальные 501: Reminders CRUD API, Inbox reply, Templates create.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update model routing, LLM lead discovery, impl status"
```

---

## Phase 5 — Финальная верификация

### Task 5.1: Линт + полный прогон

- [ ] **Step 1: Ruff**

Run (из `backend/`): `ruff check .`
Expected: без ошибок в новых/изменённых файлах. Исправить, если есть.

- [ ] **Step 2: Полный прогон тестов**

Run (из `backend/`): `pytest tests/ -v`
Expected: PASS. Сетевых вызовов нет (LLM/httpx замоканы). Если падает тест, требующий БД/сети — зафиксировать как pre-existing, не «чинить» моками вслепую.

- [ ] **Step 3: Дымовая проверка резолвинга без ключей**

Run (из `backend/`):
```bash
python -c "from app.services.llm.factory import get_llm_client; print(get_llm_client('light_ai').model)"
```
Expected: `z-ai/glm-5.1` (fallback на nvidia при пустом OpenRouter-ключе) — подтверждает обратную совместимость.

- [ ] **Step 4: Финальный commit (если линт правил что-то)**

```bash
git add -A
git commit -m "chore: lint pass for llm-cascade"
```

---

## Self-Review (выполнено автором плана)

- **Покрытие спеки:** §3.1 OpenRouter → Task 0.1; §3.2 routing → Task 1.1/1.2 + Phase 2; §3.3 Perplexity → Task 3.1/3.2; §5 CLAUDE.md → Task 4.1; §6 тесты → встроены в каждую фазу. ✔
- **Отклонение:** `scoring` (§4 спеки) — детерминированный, не заводится в роутинг; зафиксировано в шапке. ✔
- **Плейсхолдеры:** нет TODO/«handle errors» — весь код приведён. ✔
- **Консистентность имён:** `STAGE_ROUTING`, `resolve_stage`, `provider_has_key`, `OpenRouterClient`, `perplexity_search_companies`, `_safe_perplexity`, `_head_validate` — совпадают между задачами. ✔
- **Зависимости стадий:** имена стадий в Phase 2 (`query_gen`, `url_classify`, `light_ai`, `deep_ai`, `outreach`, `inbox_classify`, `lead_discovery`) ⊆ ключей `STAGE_ROUTING` из Task 1.1. ✔
