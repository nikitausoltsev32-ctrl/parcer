from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", status_code=501)
async def list_companies(user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="Not implemented yet (Phase 4)")


@router.post("", status_code=501)
async def create_company(user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="Not implemented yet (Phase 4)")


@router.patch("/{company_id}", status_code=501)
async def update_company(company_id: str, user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="Not implemented yet (Phase 4)")


@router.delete("/{company_id}", status_code=501)
async def delete_company(company_id: str, user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="Not implemented yet (Phase 4)")
