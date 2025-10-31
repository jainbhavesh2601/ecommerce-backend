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

class PaymentMethod(str, Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PAYPAL = "paypal"
    STRIPE = "stripe"
    BANK_TRANSFER = "bank_transfer"
    CASH_ON_DELIVERY = "cash_on_delivery"
    DIGITAL_WALLET = "digital_wallet"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class PaymentProviderEnum(str, Enum):
    STRIPE = "stripe"
    RAZORPAY = "razorpay"
    PAYPAL = "paypal"


class PaymentProvider(str, Enum):
    STRIPE = "stripe"
    PAYPAL = "paypal"
    RAZORPAY = "razorpay"
    SQUARE = "square"
    MANUAL = "manual"

class Payment(SQLModel, table=True):
    _tablename_ = "payments"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
            unique=True,
            nullable=False
        )
    )
    
    # Relationships
    user_id: uuid.UUID = Field(nullable=False, foreign_key="users.id")
    order_id: uuid.UUID = Field(nullable=False, foreign_key="orders.id")
    
    # Payment details
    payment_number: str = Field(index=True, nullable=False, unique=True, max_length=50)
    amount: Decimal = Field(nullable=False, decimal_places=2)
    currency: str = Field(default="USD", max_length=3)
    
    # Payment method and provider
    payment_method: PaymentMethod = Field(nullable=False)
    payment_provider: PaymentProvider = Field(nullable=False)
    
    # Status and processing
    status: PaymentStatus = Field(default=PaymentStatus.PENDING, nullable=False)
    provider_payment_id: Optional[str] = Field(default=None, max_length=255)
    provider_transaction_id: Optional[str] = Field(default=None, max_length=255)
    
    # Payment processing details
    gateway_response: Optional[str] = Field(default=None)  # JSON response from payment gateway
    failure_reason: Optional[str] = Field(default=None, max_length=500)
    
    # Security and verification
    payment_intent_id: Optional[str] = Field(default=None, max_length=255)  # For Stripe
    client_secret: Optional[str] = Field(default=None, max_length=255)  # For client-side confirmation
    
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
    processed_at: Optional[datetime] = Field(
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            default=None
        ),
        default=None
    )
    completed_at: Optional[datetime] = Field(
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            default=None
        ),
        default=None
    )

    # Relationships
    user: "User" = Relationship()
    order: "Order" = Relationship()

    def _repr_(self):
        return f"<Payment(id={self.id}, payment_number={self.payment_number}, status={self.status})>"

class PaymentRefund(SQLModel, table=True):
    _tablename_ = "payment_refunds"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
            unique=True,
            nullable=False
        )
    )
    
    # Relationships
    payment_id: uuid.UUID = Field(nullable=False, foreign_key="payment.id")
    user_id: uuid.UUID = Field(nullable=False, foreign_key="users.id")
    
    # Refund details
    refund_number: str = Field(index=True, nullable=False, unique=True, max_length=50)
    amount: Decimal = Field(nullable=False, decimal_places=2)
    reason: str = Field(nullable=False, max_length=500)
    
    # Provider details
    provider_refund_id: Optional[str] = Field(default=None, max_length=255)
    provider_response: Optional[str] = Field(default=None)  # JSON response
    
    # Status
    status: PaymentStatus = Field(default=PaymentStatus.PENDING, nullable=False)
    failure_reason: Optional[str] = Field(default=None, max_length=500)
    
    # Timestamps
    created_at: datetime = Field(
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            default=datetime.utcnow,
            nullable=False
        )
    )
    processed_at: Optional[datetime] = Field(
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            default=None
        ),
        default=None
    )

    # Relationships
    payment: Payment = Relationship()
    user: "User" = Relationship()

    def _repr_(self):
        return f"<PaymentRefund(id={self.id}, refund_number={self.refund_number}, amount={self.amount})>"

class PaymentMethodInfo(SQLModel, table=True):
    _tablename_ = "payment_methods"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
            unique=True,
            nullable=False
        )
    )
    
    # User relationship
    user_id: uuid.UUID = Field(nullable=False, foreign_key="users.id")
    
    # Payment method details
    payment_method: PaymentMethod = Field(nullable=False)
    provider: PaymentProvider = Field(nullable=False)
    
    # Encrypted card details (for security)
    card_last_four: Optional[str] = Field(default=None, max_length=4)
    card_brand: Optional[str] = Field(default=None, max_length=20)  # visa, mastercard, etc.
    card_exp_month: Optional[int] = Field(default=None, ge=1, le=12)
    card_exp_year: Optional[int] = Field(default=None, ge=2024)
    
    # Provider-specific IDs
    provider_method_id: Optional[str] = Field(default=None, max_length=255)  # Stripe payment method ID
    
    # Status
    is_default: bool = Field(default=False)
    is_active: bool = Field(default=True)
    
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
    user: "User" = Relationship()

    def _repr_(self):
        return f"<PaymentMethodInfo(id={self.id}, payment_method={self.payment_method}, last_four={self.card_last_four})>"