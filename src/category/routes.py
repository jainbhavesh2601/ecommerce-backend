from fastapi import APIRouter, Depends, Query, Path, status
from src.db.main import get_db
from src.category.schema import CategoryCreate, CategoryUpdate, CategoryResponse
from src.category.service import CategoryService
from src.common.exceptions import NotFoundError, ConflictError
from src.auth.utils import require_admin
from src.auth.user.models import User
from typing import Dict, Any
from sqlmodel.ext.asyncio.session import AsyncSession
import uuid

router = APIRouter()

@router.get("/", response_model=Dict[str, Any])
async def get_all_categories(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: str = Query("", max_length=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all categories with optional pagination and search.
    """
    try:
        return await CategoryService.get_all_categories(db, skip, limit, search)
    except Exception as e:
        raise e

@router.get("/{category_id}")
async def get_category(
    category_id: uuid.UUID = Path(..., description="The UUID of the category"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific category by its ID.
    """
    try:
        return await CategoryService.get_category(db, category_id)
    except NotFoundError:
        raise
    except Exception as e:
        raise e

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_category(
    category: CategoryCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new category (Admin only).
    """
    try:
        return await CategoryService.create_category(db, category)
    except ConflictError:
        raise
    except Exception as e:
        raise e

@router.put("/{category_id}")
async def update_category(
    category_id: uuid.UUID = Path(..., description="The UUID of the category"),
    category_update: CategoryUpdate = None,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a specific category (Admin only).
    """
    try:
        return await CategoryService.update_category(db, category_id, category_update)
    except (NotFoundError, ConflictError):
        raise
    except Exception as e:
        raise e

@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: uuid.UUID = Path(..., description="The UUID of the category"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a specific category (Admin only).
    """
    try:
        return await CategoryService.delete_category(db, category_id)
    except (NotFoundError, ConflictError):
        raise
    except Exception as e:
        raise e