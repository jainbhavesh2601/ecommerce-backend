from pydantic import BaseModel, Field
from typing import Optional, List
import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum

# Import payment enums
from src.payment.models import PaymentMethod, PaymentProvider

class CartItemBase(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(ge=1)

class CartItemCreate(CartItemBase):
    pass

class CartItemUpdate(BaseModel):
    quantity: Optional[int] = Field(None, ge=1)

class CartItemResponse(CartItemBase):
    id: uuid.UUID
    cart_id: uuid.UUID
    subtotal_price: Decimal
    product: Optional[dict] = None  # Product details will be included from the relationship
    
    class Config:
        from_attributes = True

class CartBase(BaseModel):
    total_price: Decimal = Field(default=Decimal('0.00'), decimal_places=2)

class CartCreate(CartBase):
    pass

class CartUpdate(BaseModel):
    pass  # Cart updates are handled through cart items

class CartResponse(CartBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime]
    cart_items: List[CartItemResponse]
    
    class Config:
        from_attributes = True

# Checkout Schema
class CartCheckout(BaseModel):
    cart_id: str = Field(..., description="Cart ID to checkout")
    shipping_address: str = Field(..., min_length=10, max_length=500, description="Shipping address")
    billing_address: Optional[str] = Field(None, max_length=500, description="Billing address")
    shipping_notes: Optional[str] = Field(None, max_length=500, description="Shipping notes")
    
    # Payment details
    payment_method: PaymentMethod = Field(..., description="Payment method")
    payment_provider: PaymentProvider = Field(..., description="Payment provider")
    payment_method_id: Optional[str] = Field(None, description="Saved payment method ID")
    
    # Tax and shipping
    tax_rate: Optional[Decimal] = Field(default=Decimal('0.10'), ge=0, le=1, decimal_places=4, description="Tax rate")
    shipping_cost: Optional[Decimal] = Field(default=Decimal('0.00'), ge=0, decimal_places=2, description="Shipping cost")
    
    # Customer details
    customer_email: Optional[str] = Field(None, description="Customer email")
    customer_name: Optional[str] = Field(None, description="Customer name")
    customer_phone: Optional[str] = Field(None, description="Customer phone")

class CheckoutSummary(BaseModel):
    cart_id: str
    items: List[dict]
    totals: dict
    item_count: int
    total_quantity: int

class CheckoutValidation(BaseModel):
    valid: bool
    errors: List[str]
    warnings: List[str]
    item_count: int