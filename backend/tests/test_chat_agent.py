import json
import uuid

from app.models.chat import ChatSession
from app.models.user import User
from app.services.chat import agent as agent_module
from app.services.chat.agent import stream_agent
from app.services.llm.base import LLMResult


class _NoToolClient:
    async def chat(self, *args, **kwargs):
        return LLMResult(content="Уточню и вернусь.", tool_calls=[])


class _ExplodingClient:
    async def chat(self, *args, **kwargs):
        raise RuntimeError("llm unavailable")


async def test_stream_agent_forces_search_when_model_does_not_call_tool(monkeypatch, db_session):
    user = User(id=uuid.uuid4(), email="chat@test.com", password_hash="hash")
    session = ChatSession(id=uuid.uuid4(), user_id=user.id, title=None)
    db_session.add_all([user, session])
    await db_session.commit()

    calls = []

    async def fake_search(args):
        calls.append(args)
        return {
            "companies": [
                {
                    "name": "Studio One",
                    "website": "https://example.com",
                    "website_summary": "Design studio",
                }
            ],
            "total": 1,
        }

    monkeypatch.setattr("app.services.chat.agent.get_llm_client", lambda task: _NoToolClient())
    monkeypatch.setitem(agent_module.HANDLERS, "search_companies", fake_search)

    chunks = [
        chunk
        async for chunk in stream_agent(
            db=db_session,
            session=session,
            user=user,
            user_text="найди дизайн-студии в Казани",
            history=[],
        )
    ]

    events = [json.loads(chunk.removeprefix("data: ").strip()) for chunk in chunks]

    assert calls
    assert calls[0]["query"] == "дизайн-студии"
    assert calls[0]["city"] == "Казани"
    assert any(event["event"] == "tool_result" and event["name"] == "search_companies" for event in events)


async def test_stream_agent_runs_explicit_search_without_calling_llm(monkeypatch, db_session):
    user = User(id=uuid.uuid4(), email="search-no-llm@test.com", password_hash="hash")
    session = ChatSession(id=uuid.uuid4(), user_id=user.id, title=None)
    db_session.add_all([user, session])
    await db_session.commit()

    calls = []

    async def fake_search(args):
        calls.append(args)
        return {"companies": [], "total": 0}

    monkeypatch.setattr("app.services.chat.agent.get_llm_client", lambda task: _ExplodingClient())
    monkeypatch.setitem(agent_module.HANDLERS, "search_companies", fake_search)

    chunks = [
        chunk
        async for chunk in stream_agent(
            db=db_session,
            session=session,
            user=user,
            user_text="найди дизайн-студии в Казани",
            history=[],
        )
    ]

    events = [json.loads(chunk.removeprefix("data: ").strip()) for chunk in chunks]

    assert calls
    assert [event["event"] for event in events] == ["tool_calls", "tool_result", "done"]


async def test_stream_agent_returns_sse_error_when_llm_fails(monkeypatch, db_session):
    user = User(id=uuid.uuid4(), email="llm-error@test.com", password_hash="hash")
    session = ChatSession(id=uuid.uuid4(), user_id=user.id, title=None)
    db_session.add_all([user, session])
    await db_session.commit()

    monkeypatch.setattr("app.services.chat.agent.get_llm_client", lambda task: _ExplodingClient())

    chunks = [
        chunk
        async for chunk in stream_agent(
            db=db_session,
            session=session,
            user=user,
            user_text="Расскажи, что ты умеешь",
            history=[],
        )
    ]

    events = [json.loads(chunk.removeprefix("data: ").strip()) for chunk in chunks]

    assert [event["event"] for event in events] == ["error", "done"]
    assert "модели" in events[0]["message"]
