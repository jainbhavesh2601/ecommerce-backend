from pydantic import BaseModel, Field, validator
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
from enum import Enum

from src.payment.models import PaymentMethod, PaymentStatus, PaymentProvider

class PaymentMethodEnum(str, Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PAYPAL = "paypal"
    STRIPE = "stripe"
    BANK_TRANSFER = "bank_transfer"
    CASH_ON_DELIVERY = "cash_on_delivery"
    DIGITAL_WALLET = "digital_wallet"

class PaymentStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"

class PaymentProviderEnum(str, Enum):
    STRIPE = "stripe"
    PAYPAL = "paypal"
    RAZORPAY = "razorpay"
    SQUARE = "square"
    MANUAL = "manual"

# Payment Creation Schemas
class PaymentCreate(BaseModel):
    order_id: str = Field(..., description="Order ID to pay for")
    amount: Decimal = Field(..., gt=0, decimal_places=2, description="Payment amount")
    currency: str = Field(default="USD", max_length=3, description="Payment currency")
    payment_method: PaymentMethodEnum = Field(..., description="Payment method")
    payment_provider: PaymentProviderEnum = Field(..., description="Payment provider")
    
    # Optional payment method details
    payment_method_id: Optional[str] = Field(None, description="Saved payment method ID")
    return_url: Optional[str] = Field(None, description="Return URL after payment")
    cancel_url: Optional[str] = Field(None, description="Cancel URL if payment cancelled")

class PaymentIntentCreate(BaseModel):
    """For creating payment intents (Stripe, etc.)"""
    order_id: str = Field(..., description="Order ID")
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    currency: str = Field(default="USD", max_length=3)
    payment_method: PaymentMethodEnum = Field(..., description="Payment method")
    payment_provider: PaymentProviderEnum = Field(..., description="Payment provider")
    
    # Customer details for payment
    customer_email: Optional[str] = Field(None, description="Customer email")
    customer_name: Optional[str] = Field(None, description="Customer name")
    
    # Metadata
    metadata: Optional[dict] = Field(default_factory=dict, description="Additional metadata")

class PaymentConfirm(BaseModel):
    """For confirming payment intents"""
    payment_intent_id: str = Field(..., description="Payment intent ID")
    payment_method_id: Optional[str] = Field(None, description="Payment method ID")
    return_url: Optional[str] = Field(None, description="Return URL")

# Payment Response Schemas
class PaymentResponse(BaseModel):
    id: str
    payment_number: str
    order_id: str
    amount: Decimal
    currency: str
    payment_method: PaymentMethodEnum
    payment_provider: PaymentProviderEnum
    status: PaymentStatusEnum
    provider_payment_id: Optional[str] = None
    payment_intent_id: Optional[str] = None
    client_secret: Optional[str] = None
    failure_reason: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PaymentListResponse(BaseModel):
    payments: List[PaymentResponse]
    total: int
    page: int
    limit: int

# Payment Method Schemas
class PaymentMethodCreate(BaseModel):
    payment_method: PaymentMethodEnum = Field(..., description="Payment method type")
    provider: PaymentProviderEnum = Field(..., description="Payment provider")
    
    # Card details (for card payments)
    card_number: Optional[str] = Field(None, description="Card number (will be encrypted)")
    card_exp_month: Optional[int] = Field(None, ge=1, le=12, description="Card expiry month")
    card_exp_year: Optional[int] = Field(None, ge=2024, description="Card expiry year")
    card_cvc: Optional[str] = Field(None, description="Card CVC")
    card_holder_name: Optional[str] = Field(None, description="Card holder name")
    
    # Provider-specific
    provider_method_id: Optional[str] = Field(None, description="Provider payment method ID")
    is_default: bool = Field(default=False, description="Set as default payment method")

class PaymentMethodUpdate(BaseModel):
    is_default: Optional[bool] = Field(None, description="Set as default payment method")
    is_active: Optional[bool] = Field(None, description="Activate/deactivate payment method")

class PaymentMethodResponse(BaseModel):
    id: str
    payment_method: PaymentMethodEnum
    provider: PaymentProviderEnum
    card_last_four: Optional[str] = None
    card_brand: Optional[str] = None
    card_exp_month: Optional[int] = None
    card_exp_year: Optional[int] = None
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Refund Schemas
class RefundCreate(BaseModel):
    payment_id: str = Field(..., description="Payment ID to refund")
    amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2, description="Refund amount (full refund if not specified)")
    reason: str = Field(..., min_length=10, max_length=500, description="Refund reason")

class RefundResponse(BaseModel):
    id: str
    refund_number: str
    payment_id: str
    amount: Decimal
    reason: str
    status: PaymentStatusEnum
    provider_refund_id: Optional[str] = None
    failure_reason: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Cart Checkout Schema
class CartCheckout(BaseModel):
    cart_id: str = Field(..., description="Cart ID to checkout")
    shipping_address: str = Field(..., min_length=10, max_length=500, description="Shipping address")
    billing_address: Optional[str] = Field(None, max_length=500, description="Billing address")
    shipping_notes: Optional[str] = Field(None, max_length=500, description="Shipping notes")
    
    # Payment details
    payment_method: PaymentMethodEnum = Field(..., description="Payment method")
    payment_provider: PaymentProviderEnum = Field(..., description="Payment provider")
    payment_method_id: Optional[str] = Field(None, description="Saved payment method ID")
    
    # Tax and shipping
    tax_rate: Optional[Decimal] = Field(default=Decimal('0.10'), ge=0, le=1, decimal_places=4, description="Tax rate")
    shipping_cost: Optional[Decimal] = Field(default=Decimal('0.00'), ge=0, decimal_places=2, description="Shipping cost")
    
    # Customer details
    customer_email: Optional[str] = Field(None, description="Customer email")
    customer_name: Optional[str] = Field(None, description="Customer name")
    customer_phone: Optional[str] = Field(None, description="Customer phone")

class CheckoutResponse(BaseModel):
    order: dict  # Order details
    payment: PaymentResponse  # Payment details
    requires_action: bool = Field(default=False, description="Whether payment requires additional action")
    action_url: Optional[str] = Field(None, description="URL for payment action if required")

# Webhook Schemas
class PaymentWebhook(BaseModel):
    """For handling payment provider webhooks"""
    provider: PaymentProviderEnum = Field(..., description="Payment provider")
    event_type: str = Field(..., description="Webhook event type")
    provider_event_id: str = Field(..., description="Provider event ID")
    data: dict = Field(..., description="Webhook data")
    signature: Optional[str] = Field(None, description="Webhook signature for verification")

# Payment Status Update Schema
class PaymentStatusUpdate(BaseModel):
    status: PaymentStatusEnum = Field(..., description="New payment status")
    provider_payment_id: Optional[str] = Field(None, description="Provider payment ID")
    provider_transaction_id: Optional[str] = Field(None, description="Provider transaction ID")
    gateway_response: Optional[str] = Field(None, description="Gateway response")
    failure_reason: Optional[str] = Field(None, description="Failure reason if failed")

# Validation functions
def validate_card_number(v):
    if v is not None:
        # Remove spaces and dashes
        v = v.replace(' ', '').replace('-', '')
        # Basic card number validation (Luhn algorithm would be better)
        if not v.isdigit() or len(v) < 13 or len(v) > 19:
            raise ValueError('Invalid card number')
    return v

def validate_card_cvc(v):
    if v is not None:
        if not v.isdigit() or len(v) < 3 or len(v) > 4:
            raise ValueError('Invalid CVC')
    return v
