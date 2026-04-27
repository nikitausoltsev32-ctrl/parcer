from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(tags=["contacts"])


@router.get("/contacts", status_code=501)
async def list_contacts(user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="Not implemented yet (Phase 2/4)")


@router.post("/contacts", status_code=501)
async def create_contact(user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="Not implemented yet (Phase 2)")


@router.patch("/contacts/{contact_id}", status_code=501)
async def update_contact(contact_id: str, user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="Not implemented yet (Phase 4)")


@router.delete("/contacts/{contact_id}", status_code=501)
async def delete_contact(contact_id: str, user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="Not implemented yet (Phase 2)")


@router.get("/contacts/{contact_id}/activities", status_code=501)
async def list_activities(contact_id: str, user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="Not implemented yet (Phase 4)")


@router.post("/contacts/{contact_id}/notes", status_code=501)
async def add_note(contact_id: str, user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="Not implemented yet (Phase 4)")
