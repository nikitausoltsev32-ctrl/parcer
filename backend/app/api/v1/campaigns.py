from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("", status_code=501)
async def list_campaigns(user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="Not implemented yet (Phase 3/4)")


@router.post("", status_code=501)
async def create_campaign(user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="Not implemented yet (Phase 3)")


@router.get("/{campaign_id}", status_code=501)
async def get_campaign(campaign_id: str, user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="Not implemented yet (Phase 3)")


@router.post("/{campaign_id}/generate", status_code=501)
async def generate(campaign_id: str, user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="Not implemented yet (Phase 3)")


@router.post("/{campaign_id}/send", status_code=501)
async def send(campaign_id: str, user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="Not implemented yet (Phase 4)")


@router.post("/{campaign_id}/pause", status_code=501)
async def pause(campaign_id: str, user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="Not implemented yet (Phase 4)")


@router.post("/{campaign_id}/resume", status_code=501)
async def resume(campaign_id: str, user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="Not implemented yet (Phase 4)")


@router.post("/{campaign_id}/followup", status_code=501)
async def followup(campaign_id: str, user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="Not implemented yet (Phase 5)")


@router.get("/{campaign_id}/stats", status_code=501)
async def stats(campaign_id: str, user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="Not implemented yet (Phase 4)")
