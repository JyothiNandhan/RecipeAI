from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_admin_user,
    get_current_user,
    get_password_hash,
    verify_password,
)
from database import create_user, delete_user, get_all_users, get_user_by_email
from models import TokenRefreshRequest, TokenResponse, UserCreate, UserLogin, UserOut

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
admin_user_router = APIRouter(prefix="/admin", tags=["Admin"])


@auth_router.post("/register", response_model=TokenResponse, status_code=201)
async def register(payload: UserCreate) -> TokenResponse:
    if get_user_by_email(payload.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )
    if len(payload.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long.",
        )
    hashed = get_password_hash(payload.password)
    user = create_user(payload.email, hashed)
    access_token = create_access_token({"sub": payload.email})
    refresh_token = create_refresh_token({"sub": payload.email})
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserOut(
            id=user["id"],
            email=user["email"],
            role=user["role"],
            created_at=user["created_at"],
        ),
    )


@auth_router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin) -> TokenResponse:
    user = get_user_by_email(payload.email)
    if not user or not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    access_token = create_access_token({"sub": payload.email})
    refresh_token = create_refresh_token({"sub": payload.email})
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserOut(
            id=user["id"],
            email=user["email"],
            role=user["role"],
            created_at=user["created_at"],
        ),
    )


@auth_router.post("/refresh", response_model=TokenResponse)
async def refresh(body: TokenRefreshRequest) -> TokenResponse:
    payload = decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type. Please log in again.",
        )
    email = payload.get("sub", "")
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found. Please log in again.",
        )
    access_token = create_access_token({"sub": email})
    new_refresh = create_refresh_token({"sub": email})
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        token_type="bearer",
        user=UserOut(
            id=user["id"],
            email=user["email"],
            role=user["role"],
            created_at=user["created_at"],
        ),
    )


@auth_router.get("/me", response_model=UserOut)
async def get_me(current_user: dict = Depends(get_current_user)) -> UserOut:
    return UserOut(
        id=current_user["id"],
        email=current_user["email"],
        role=current_user["role"],
        created_at=current_user["created_at"],
    )


@admin_user_router.get("/users", response_model=list[UserOut])
async def list_users(_: dict = Depends(get_admin_user)) -> list[UserOut]:
    users = get_all_users()
    return [
        UserOut(
            id=u["id"],
            email=u["email"],
            role=u["role"],
            created_at=u["created_at"],
        )
        for u in users
    ]


@admin_user_router.delete("/users/{user_id}", status_code=204)
async def remove_user(user_id: int, _: dict = Depends(get_admin_user)) -> None:
    if not delete_user(user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or cannot delete an admin account.",
        )
