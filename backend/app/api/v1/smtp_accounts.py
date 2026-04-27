from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/smtp-accounts", tags=["smtp"])


@router.get("", status_code=501)
async def list_smtp(user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="Not implemented yet (Phase 4)")


@router.post("", status_code=501)
async def create_smtp(user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="Not implemented yet (Phase 4)")


@router.post("/{smtp_id}/verify", status_code=501)
async def verify_smtp(smtp_id: str, user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="Not implemented yet (Phase 4)")


@router.delete("/{smtp_id}", status_code=501)
async def delete_smtp(smtp_id: str, user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="Not implemented yet (Phase 4)")
