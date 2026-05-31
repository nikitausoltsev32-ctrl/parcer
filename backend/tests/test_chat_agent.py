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
            "status": "pending",
            "log_id": "11111111-1111-1111-1111-111111111111",
            "query": args["query"],
            "city": args["city"],
        }

    monkeypatch.setattr("app.services.chat.agent.get_llm_client", lambda task, **kwargs: _NoToolClient())
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
    tool_result = next(event for event in events if event["event"] == "tool_result")
    assert tool_result["name"] == "search_companies"
    assert tool_result["result"]["status"] == "pending"
    assert "companies" not in tool_result["result"]


async def test_stream_agent_uses_requested_search_limit(monkeypatch, db_session):
    user = User(id=uuid.uuid4(), email="chat-limit@test.com", password_hash="hash")
    session = ChatSession(id=uuid.uuid4(), user_id=user.id, title=None)
    db_session.add_all([user, session])
    await db_session.commit()

    calls = []

    async def fake_search(args):
        calls.append(args)
        return {
            "status": "pending",
            "log_id": "11111111-1111-1111-1111-111111111111",
            "query": args["query"],
            "city": args["city"],
            "limit": args["limit"],
        }

    monkeypatch.setattr("app.services.chat.agent.get_llm_client", lambda task, **kwargs: _NoToolClient())
    monkeypatch.setitem(agent_module.HANDLERS, "search_companies", fake_search)

    chunks = [
        chunk
        async for chunk in stream_agent(
            db=db_session,
            session=session,
            user=user,
            user_text="найди 10 дизайн-студий в Казани",
            history=[],
        )
    ]

    events = [json.loads(chunk.removeprefix("data: ").strip()) for chunk in chunks]
    tool_result = next(event for event in events if event["event"] == "tool_result")

    assert calls[0]["query"] == "дизайн-студий"
    assert calls[0]["city"] == "Казани"
    assert calls[0]["limit"] == 10
    assert tool_result["result"]["limit"] == 10


async def test_stream_agent_runs_explicit_search_without_calling_llm(monkeypatch, db_session):
    user = User(id=uuid.uuid4(), email="search-no-llm@test.com", password_hash="hash")
    session = ChatSession(id=uuid.uuid4(), user_id=user.id, title=None)
    db_session.add_all([user, session])
    await db_session.commit()

    calls = []

    async def fake_search(args):
        calls.append(args)
        return {"companies": [], "total": 0}

    monkeypatch.setattr("app.services.chat.agent.get_llm_client", lambda task, **kwargs: _ExplodingClient())
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

    monkeypatch.setattr("app.services.chat.agent.get_llm_client", lambda task, **kwargs: _ExplodingClient())

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
