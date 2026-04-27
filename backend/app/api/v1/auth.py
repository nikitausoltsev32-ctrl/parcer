from fastapi import APIRouter, Cookie, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from app.schemas.user import UserRead
from app.services.auth_service import (
    REFRESH_MAX_AGE,
    authenticate_user,
    refresh_access,
    register_user,
    request_password_reset,
    reset_user_password,
    verify_user_email,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    return await register_user(db, body.email, body.password, body.full_name, body.llm_consent)


@router.post("/verify-email")
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    await verify_user_email(db, token)
    return {"detail": "Email verified"}


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    access, refresh = await authenticate_user(db, body.email, body.password)
    response.set_cookie("refresh_token", refresh, httponly=True, samesite="lax", max_age=REFRESH_MAX_AGE, secure=False)
    return TokenResponse(access_token=access)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(response: Response, refresh_token: str | None = Cookie(default=None)):
    access, new_refresh = refresh_access(refresh_token)
    response.set_cookie("refresh_token", new_refresh, httponly=True, samesite="lax", max_age=REFRESH_MAX_AGE, secure=False)
    return TokenResponse(access_token=access)


@router.post("/logout", status_code=204)
async def logout(response: Response):
    response.delete_cookie("refresh_token")


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    await request_password_reset(db, body.email)
    return {"detail": "If the email exists, a reset link was sent"}


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    await reset_user_password(db, body.token, body.new_password)
    return {"detail": "Password updated"}
