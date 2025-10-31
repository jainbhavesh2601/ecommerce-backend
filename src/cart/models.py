from sqlmodel import SQLModel, Field, Column
import uuid
from typing import Optional, List, TYPE_CHECKING
import sqlalchemy.dialects.postgresql as pg
from datetime import datetime
from sqlmodel import Relationship
from decimal import Decimal

if TYPE_CHECKING:
    from src.product.models import Product
    from src.auth.user.models import User

class Cart(SQLModel, table=True):
    """
    Shopping Cart - Each user has exactly ONE cart (one-to-one relationship)
    The cart persists across sessions and contains CartItems
    """
    __tablename__ = 'carts'

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
            unique=True,
            nullable=False
        )
    )
    
    # ONE-to-ONE relationship with User (each user has exactly one cart)
    user_id: uuid.UUID = Field(
        nullable=False, 
        foreign_key="users.id", 
        unique=True,  # This enforces one cart per user
        index=True
    )
    user: "User" = Relationship(back_populates="cart")
    
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
    
    # ONE cart has MANY cart items (one-to-many)
    cart_items: List["CartItem"] = Relationship(
        back_populates="cart",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    
    # Calculated total price
    total_price: Decimal = Field(default=Decimal('0.00'), nullable=False, decimal_places=2)
    
    def __repr__(self):
        return f"<Cart(id={self.id}, user_id={self.user_id}, items={len(self.cart_items)})>"


class CartItem(SQLModel, table=True):
    """
    Cart Item - Represents a product in a user's cart with quantity
    Many cart items belong to ONE cart
    """
    __tablename__ = 'cart_items'

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
            unique=True,
            nullable=False
        )
    )
    
    # MANY cart items belong to ONE cart
    cart_id: uuid.UUID = Field(
        nullable=False, 
        foreign_key="carts.id",
        index=True
    )
    cart: "Cart" = Relationship(back_populates="cart_items")
    
    # MANY cart items can reference ONE product
    product_id: uuid.UUID = Field(
        nullable=False, 
        foreign_key="products.id",
        index=True
    )
    product: "Product" = Relationship(back_populates="cart_items")
    
    # Quantity and pricing
    quantity: int = Field(default=1, nullable=False, ge=1)
    subtotal_price: Decimal = Field(default=Decimal('0.00'), nullable=False, decimal_places=2)
    
    # Timestamp
    added_at: datetime = Field(
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            default=datetime.utcnow,
            nullable=False
        )
    )
    
    def __repr__(self):
        return f"<CartItem(id={self.id}, product_id={self.product_id}, quantity={self.quantity})>"