from sqlmodel import SQLModel, Field, Column, Relationship
import uuid
from typing import Optional, List, TYPE_CHECKING
import sqlalchemy.dialects.postgresql as pg
from datetime import datetime

if TYPE_CHECKING:
    from src.product.models import Product

class Category(SQLModel, table=True):
    __tablename__ = 'categories'

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
            unique=True,
            nullable=False
        )
    )
    name: str = Field(index=True, nullable=False, unique=True)
    description: Optional[str] = Field(default=None, nullable=True)
    created_at: datetime = Field(
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            default=datetime.utcnow,
            nullable=False
        )
    )
    updated_at: Optional[datetime] = Field(
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            default=None,
            onupdate=datetime.utcnow,
        ),
        default=None
    )
    
    # Relationship to products
    products: List["Product"] = Relationship(
        back_populates="category",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
