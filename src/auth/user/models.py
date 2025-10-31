from sqlmodel import SQLModel, Field, Column
import uuid
from typing import Optional, List, TYPE_CHECKING
import sqlalchemy.dialects.postgresql as pg
from datetime import datetime
from sqlmodel import Relationship
from enum import Enum

if TYPE_CHECKING:
    from src.orders.models import Order
    from src.cart.models import Cart
    from src.product.models import Product

class UserRole(str, Enum):
    NORMAL_USER = "normal_user"
    SELLER = "seller"
    ADMIN = "admin"

class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
            unique=True,
            nullable=False
        )
    )
    email: str = Field(index=True, nullable=False, unique=True, max_length=255)
    username: str = Field(index=True, nullable=False, unique=True, max_length=50)
    hashed_password: str = Field(nullable=False)
    full_name: str = Field(nullable=False, max_length=100)
    phone_number: Optional[str] = Field(default=None, max_length=20)
    address: Optional[str] = Field(default=None, max_length=500)
    
    # Location fields for proximity-based features
    latitude: Optional[float] = Field(default=None)
    longitude: Optional[float] = Field(default=None)
    city: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default=None, max_length=100)
    
    is_active: bool = Field(default=True, nullable=False)
    is_verified: bool = Field(default=False, nullable=False)
    role: UserRole = Field(default=UserRole.NORMAL_USER, nullable=False)
    
    # Email notification preferences
    email_notifications_enabled: bool = Field(default=True, nullable=False)
    order_notifications_enabled: bool = Field(default=True, nullable=False)
    marketing_emails_enabled: bool = Field(default=False, nullable=False)
    
    # Timestamps
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
    last_login: Optional[datetime] = Field(
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            default=None
        ),
        default=None
    )

    # Relationships
    # Each user has exactly ONE cart (one-to-one)
    cart: Optional["Cart"] = Relationship(back_populates="user", sa_relationship_kwargs={"uselist": False})
    
    # Each user can have MANY orders (one-to-many)
    orders: List["Order"] = Relationship(back_populates="user")
    
    # Each seller can have MANY products (one-to-many) - only if user is a seller
    products: List["Product"] = Relationship(back_populates="seller")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"
