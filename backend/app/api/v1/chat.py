import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.chat import ChatMessage, ChatSession
from app.models.user import User
from app.services.chat.agent import stream_agent

router = APIRouter(prefix="/chat", tags=["chat"])


class SessionCreate(BaseModel):
    title: str | None = None


class MessageRequest(BaseModel):
    content: str


@router.post("/sessions", status_code=201)
async def create_session(
    body: SessionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = ChatSession(
        id=uuid.uuid4(),
        user_id=user.id,
        title=body.title,
        started_at=datetime.now(UTC),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return {"id": str(session.id), "title": session.title, "started_at": session.started_at}


@router.get("/sessions")
async def list_sessions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user.id)
        .order_by(ChatSession.last_message_at.desc().nullslast())
        .limit(50)
    )
    sessions = result.scalars().all()
    return [{"id": str(s.id), "title": s.title, "last_message_at": s.last_message_at} for s in sessions]


@router.get("/sessions/{session_id}/messages")
async def list_messages(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await _get_session(db, session_id, user.id)
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at)
        .limit(200)
    )
    msgs = result.scalars().all()
    return [
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.content,
            "tool_calls": m.tool_calls,
            "tool_results": m.tool_results,
            "created_at": m.created_at,
        }
        for m in msgs
    ]


@router.post("/sessions/{session_id}/message")
async def post_message(
    session_id: str,
    body: MessageRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not body.content.strip():
        raise HTTPException(status_code=422, detail="Empty message")

    session = await _get_session(db, session_id, user.id)

    history_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at)
        .limit(40)
    )
    history = list(history_result.scalars().all())

    # Авто-заголовок по первому сообщению
    if not session.title:
        session.title = body.content[:60]
        await db.commit()

    return StreamingResponse(
        stream_agent(db, session, user, body.content, history),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _get_session(db: AsyncSession, session_id: str, user_id: uuid.UUID) -> ChatSession:
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == uuid.UUID(session_id),
            ChatSession.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
