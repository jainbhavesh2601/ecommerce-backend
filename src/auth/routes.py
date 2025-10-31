from fastapi import APIRouter, Depends, status, HTTPException
from src.db.main import get_db
from src.auth.user.schema import (
    UserCreate, UserLogin, Token, UserResponse, 
    EmailVerificationRequest, ResendVerificationRequest
)
from src.auth.user.service import UserService
from src.auth.utils import get_current_active_user
from src.auth.user.models import User
from src.common.exceptions import ConflictError, ValidationError
from typing import Dict, Any
from sqlmodel.ext.asyncio.session import AsyncSession

router = APIRouter()

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    user: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user.
    """
    try:
        return await UserService.create_user(db, user)
    except (ConflictError, ValidationError):
        raise
    except Exception as e:
        raise e

@router.post("/login", response_model=Token)
async def login(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user and return access token.
    """
    try:
        return await UserService.authenticate_user(db, login_data)
    except HTTPException:
        raise
    except Exception as e:
        raise e

@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current authenticated user's information.
    """
    return current_user

@router.post("/logout", response_model=Dict[str, Any])
async def logout(
    current_user: User = Depends(get_current_active_user)
):
    """
    Logout user (client should discard the token).
    """
    return {
        "message": "Successfully logged out",
        "data": {"user_id": str(current_user.id)}
    }

@router.post("/verify-email", response_model=Dict[str, Any])
async def verify_email(
    verification_data: EmailVerificationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify user's email address with the provided token.
    """
    try:
        return await UserService.verify_email(db, verification_data.token)
    except HTTPException:
        raise
    except Exception as e:
        raise e

@router.post("/resend-verification", response_model=Dict[str, Any])
async def resend_verification(
    resend_data: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Resend email verification link to user.
    """
    try:
        return await UserService.resend_verification_email(db, resend_data.email)
    except HTTPException:
        raise
    except Exception as e:
        raise e
