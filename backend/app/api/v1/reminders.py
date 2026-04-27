from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.get("", status_code=501)
async def list_reminders(user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="Not implemented yet (Phase 5)")


@router.post("", status_code=501)
async def create_reminder(user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="Not implemented yet (Phase 5)")


@router.patch("/{reminder_id}", status_code=501)
async def update_reminder(reminder_id: str, user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="Not implemented yet (Phase 5)")
