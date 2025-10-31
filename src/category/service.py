from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, func
from src.category.models import Category
from src.category.schema import CategoryCreate, CategoryUpdate
from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException, status
from src.common.response import ResponseHandler
from src.common.exceptions import NotFoundError, ConflictError
import uuid
class CategoryService:
    @staticmethod
    async def get_all_categories(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: str = ""
    ) -> dict:
        try:
            query = select(Category)
            if search:
                query = query.where(Category.name.ilike(f"%{search}%"))
            query = query.offset(skip).limit(limit)
            result = await db.execute(query)
            categories = result.scalars().all()
            
            # Get total count for pagination
            count_query = select(func.count()).select_from(Category)
            if search:
                count_query = count_query.where(Category.name.ilike(f"%{search}%"))
            total = await db.scalar(count_query)
            
            return {
                "message": "Successfully retrieved categories",
                "data": categories,
                "metadata": {
                    "skip": skip,
                    "limit": limit,
                    "total": total
                }
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

    @staticmethod
    async def get_category(db: AsyncSession, category_id: uuid.UUID) -> Category:
        query = select(Category).where(Category.id == category_id)
        result = await db.execute(query)
        category = result.scalar_one_or_none()
        
        if not category:
            raise NotFoundError("Category", category_id)
            
        return ResponseHandler.get_single_success("Category", category_id, category)

    @staticmethod
    async def create_category(db: AsyncSession, category: CategoryCreate) -> Category:
        # Check if category with same name exists
        query = select(Category).where(Category.name == category.name)
        result = await db.execute(query)
        existing_category = result.scalar_one_or_none()
        
        if existing_category:
            raise ConflictError(f"Category with name '{category.name}' already exists")
        
        db_category = Category(**category.model_dump())
        db.add(db_category)
        await db.commit()
        await db.refresh(db_category)
        return ResponseHandler.create_success("Category", db_category.id, db_category)

    @staticmethod
    async def update_category(
        db: AsyncSession,
        category_id: uuid.UUID,
        category_update: CategoryUpdate
    ) -> Category:
        # Get existing category
        query = select(Category).where(Category.id == category_id)
        result = await db.execute(query)
        db_category = result.scalar_one_or_none()
        
        if not db_category:
            raise NotFoundError("Category", category_id)
        
        # If name is being updated, check for uniqueness
        if category_update.name and category_update.name != db_category.name:
            name_query = select(Category).where(Category.name == category_update.name)
            name_result = await db.execute(name_query)
            existing_category = name_result.scalar_one_or_none()
            
            if existing_category:
                raise ConflictError(f"Category with name '{category_update.name}' already exists")
        
        # Update fields
        for key, value in category_update.model_dump(exclude_unset=True).items():
            setattr(db_category, key, value)
        
        db_category.updated_at = datetime.utcnow()
        
        db.add(db_category)
        await db.commit()
        await db.refresh(db_category)
        
        return ResponseHandler.update_success("Category", category_id, db_category)

    @staticmethod
    async def delete_category(db: AsyncSession, category_id: uuid.UUID) -> None:
        query = select(Category).where(Category.id == category_id)
        result = await db.execute(query)
        category = result.scalar_one_or_none()
        
        if not category:
            raise NotFoundError("Category", category_id)
        
        # Check if category has products
        if len(category.products) > 0:
            raise ConflictError(f"Cannot delete category with ID {category_id} as it has associated products")
            
        await db.delete(category)
        await db.commit()
        
        return ResponseHandler.delete_success("Category", category_id, category)