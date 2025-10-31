from fastapi import APIRouter, Depends, Query, Path, status, HTTPException
from src.db.main import get_db
from src.auth.user.schema import (
    UserCreate, UserUpdate, UserResponse, UserListResponse, 
    UserLogin, Token, PasswordChange
)
from src.auth.user.service import UserService
from src.auth.user.models import User, UserRole
from src.auth.utils import (
    get_current_active_user, require_admin, require_seller_or_admin
)
from src.common.exceptions import NotFoundError, ConflictError, ValidationError
from typing import Dict, Any, Optional
from sqlmodel.ext.asyncio.session import AsyncSession
import uuid

router = APIRouter()

@router.get("/")
async def get_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: str = Query("", max_length=100),
    role: Optional[UserRole] = Query(None),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all users (Admin only).
    """
    try:
        return await UserService.get_all_users(db, skip, limit, search, role)
    except Exception as e:
        raise e

@router.get("/me")
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user's profile.
    """
    return current_user

@router.get("/{user_id}")
async def get_user(
    user_id: uuid.UUID = Path(..., description="The UUID of the user"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific user by ID.
    Users can only view their own profile unless they are admin.
    """
    try:
        # Check permissions
        if current_user.role != UserRole.ADMIN and current_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own profile"
            )
        
        return await UserService.get_user(db, user_id)
    except (NotFoundError, HTTPException):
        raise
    except Exception as e:
        raise e

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(
    user: UserCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new user (Admin only).
    """
    try:
        return await UserService.create_user(db, user)
    except (ConflictError, ValidationError):
        raise
    except Exception as e:
        raise e

@router.put("/{user_id}")
async def update_user(
    user_id: uuid.UUID = Path(..., description="The UUID of the user"),
    user_update: UserUpdate = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a user.
    Users can only update their own profile unless they are admin.
    """
    try:
        return await UserService.update_user(db, user_id, user_update, current_user)
    except (NotFoundError, ConflictError, ValidationError, HTTPException):
        raise
    except Exception as e:
        raise e

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID = Path(..., description="The UUID of the user"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a user.
    Users can only delete their own account unless they are admin.
    """
    try:
        return await UserService.delete_user(db, user_id, current_user)
    except (NotFoundError, HTTPException):
        raise
    except Exception as e:
        raise e

@router.post("/change-password", response_model=Dict[str, Any])
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Change user password.
    """
    try:
        return await UserService.change_password(db, current_user.id, password_data, current_user)
    except (NotFoundError, HTTPException):
        raise
    except Exception as e:
        raise e

@router.get("/sellers/list")
async def get_sellers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: str = Query("", max_length=100),
    current_user: User = Depends(require_seller_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all sellers (Seller/Admin only).
    """
    try:
        return await UserService.get_all_users(db, skip, limit, search, UserRole.SELLER)
    except Exception as e:
        raise e
