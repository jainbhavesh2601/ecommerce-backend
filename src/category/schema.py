from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from src.product.schema import Product
import uuid

class CategoryBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=500)

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

class CategoryResponse(CategoryBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime]
    products: List[Product] = []

    class Config:
        from_attributes = True