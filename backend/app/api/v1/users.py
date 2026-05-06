from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserRead, UserUpdate

router = APIRouter(prefix="/me", tags=["users"])


@router.get("", response_model=UserRead)
async def get_me(user: User = Depends(get_current_user)):
    return user


@router.patch("", response_model=UserRead)
async def update_me(body: UserUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.business_profile is not None:
        user.business_profile = body.business_profile.model_dump()
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
