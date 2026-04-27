from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/inbox", tags=["inbox"])


@router.get("", status_code=501)
async def list_inbox(user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="Not implemented yet (Phase 5)")


@router.post("/{message_id}/reply", status_code=501)
async def reply(message_id: str, user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="Not implemented yet (Phase 5)")


@router.patch("/{message_id}", status_code=501)
async def update_classification(message_id: str, user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="Not implemented yet (Phase 5)")
