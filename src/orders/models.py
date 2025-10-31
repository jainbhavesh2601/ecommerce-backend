from sqlmodel import SQLModel, Field, Column
import uuid
from typing import Optional, List, TYPE_CHECKING
import sqlalchemy.dialects.postgresql as pg
from datetime import datetime
from sqlmodel import Relationship
from decimal import Decimal
from enum import Enum

if TYPE_CHECKING:
    from src.auth.user.models import User
    from src.product.models import Product

class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"

class Order(SQLModel, table=True):
    __tablename__ = "orders"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
            unique=True,
            nullable=False
        )
    )
    user_id: uuid.UUID = Field(nullable=False, foreign_key="users.id")
    order_number: str = Field(index=True, nullable=False, unique=True, max_length=50)
    
    # Order details
    status: OrderStatus = Field(default=OrderStatus.PENDING, nullable=False)
    payment_status: PaymentStatus = Field(default=PaymentStatus.PENDING, nullable=False)
    
    # Pricing
    subtotal: Decimal = Field(nullable=False, decimal_places=2)
    tax_amount: Decimal = Field(default=Decimal('0.00'), nullable=False, decimal_places=2)
    shipping_cost: Decimal = Field(default=Decimal('0.00'), nullable=False, decimal_places=2)
    total_amount: Decimal = Field(nullable=False, decimal_places=2)
    
    # Shipping information
    shipping_address: str = Field(nullable=False, max_length=500)
    billing_address: Optional[str] = Field(default=None, max_length=500)
    shipping_notes: Optional[str] = Field(default=None, max_length=500)
    
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
    shipped_at: Optional[datetime] = Field(
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            default=None
        ),
        default=None
    )
    delivered_at: Optional[datetime] = Field(
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            default=None
        ),
        default=None
    )

    # Relationships
    user: "User" = Relationship(back_populates="orders")
    order_items: List["OrderItem"] = Relationship(back_populates="order")

    def __repr__(self):
        return f"<Order(id={self.id}, order_number={self.order_number}, status={self.status})>"

class OrderItem(SQLModel, table=True):
    __tablename__ = "order_items"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
            unique=True,
            nullable=False
        )
    )
    order_id: uuid.UUID = Field(nullable=False, foreign_key="orders.id")
    product_id: uuid.UUID = Field(nullable=False, foreign_key="products.id")
    
    # Product details at time of order (for historical accuracy)
    product_name: str = Field(nullable=False, max_length=100)
    product_price: Decimal = Field(nullable=False, decimal_places=2)
    quantity: int = Field(nullable=False, ge=1)
    subtotal: Decimal = Field(nullable=False, decimal_places=2)
    
    # Timestamps
    created_at: datetime = Field(
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            default=datetime.utcnow,
            nullable=False
        )
    )

    # Relationships
    order: "Order" = Relationship(back_populates="order_items")
    product: "Product" = Relationship()

    def __repr__(self):
        return f"<OrderItem(id={self.id}, product_name={self.product_name}, quantity={self.quantity})>"
