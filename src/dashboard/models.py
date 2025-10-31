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
    from src.orders.models import Order

class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"

class Invoice(SQLModel, table=True):
    __tablename__ = "invoices"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
            unique=True,
            nullable=False
        )
    )
    
    # Invoice details
    invoice_number: str = Field(index=True, nullable=False, unique=True, max_length=50)
    order_id: uuid.UUID = Field(nullable=False, foreign_key="orders.id")
    seller_id: uuid.UUID = Field(nullable=False, foreign_key="users.id")
    
    # Invoice status and dates
    status: InvoiceStatus = Field(default=InvoiceStatus.DRAFT, nullable=False)
    issue_date: datetime = Field(
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            default=datetime.utcnow,
            nullable=False
        )
    )
    due_date: datetime = Field(
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False
        )
    )
    paid_date: Optional[datetime] = Field(
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            default=None
        ),
        default=None
    )
    
    # Financial details
    subtotal: Decimal = Field(nullable=False, decimal_places=2)
    tax_amount: Decimal = Field(default=Decimal('0.00'), nullable=False, decimal_places=2)
    total_amount: Decimal = Field(nullable=False, decimal_places=2)
    
    # Customer information (snapshot at time of invoice)
    customer_name: str = Field(nullable=False, max_length=100)
    customer_email: str = Field(nullable=False, max_length=255)
    customer_address: str = Field(nullable=False, max_length=500)
    
    # Seller information (snapshot at time of invoice)
    seller_name: str = Field(nullable=False, max_length=100)
    seller_email: str = Field(nullable=False, max_length=255)
    seller_address: Optional[str] = Field(default=None, max_length=500)
    seller_phone: Optional[str] = Field(default=None, max_length=20)
    
    # Additional details
    notes: Optional[str] = Field(default=None, max_length=1000)
    terms: Optional[str] = Field(default=None, max_length=1000)
    
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

    # Relationships
    order: "Order" = Relationship()
    seller: "User" = Relationship()

    def __repr__(self):
        return f"<Invoice(id={self.id}, invoice_number={self.invoice_number}, status={self.status})>"

class InvoiceItem(SQLModel, table=True):
    __tablename__ = "invoice_items"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
            unique=True,
            nullable=False
        )
    )
    invoice_id: uuid.UUID = Field(nullable=False, foreign_key="invoices.id")
    
    # Product details (snapshot at time of invoice)
    product_name: str = Field(nullable=False, max_length=100)
    product_description: Optional[str] = Field(default=None, max_length=500)
    unit_price: Decimal = Field(nullable=False, decimal_places=2)
    quantity: int = Field(nullable=False, ge=1)
    total_price: Decimal = Field(nullable=False, decimal_places=2)
    
    # Timestamps
    created_at: datetime = Field(
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            default=datetime.utcnow,
            nullable=False
        )
    )

    # Relationships
    invoice: "Invoice" = Relationship()

    def __repr__(self):
        return f"<InvoiceItem(id={self.id}, product_name={self.product_name}, quantity={self.quantity})>"
