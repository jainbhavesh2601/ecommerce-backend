from pydantic import BaseModel, Field
from typing import Optional, List
import uuid
from datetime import datetime
from decimal import Decimal
from src.orders.models import OrderStatus, PaymentStatus

class OrderItemBase(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(ge=1)

class OrderItemCreate(OrderItemBase):
    pass

class OrderItemResponse(OrderItemBase):
    id: uuid.UUID
    order_id: uuid.UUID
    product_name: str
    product_price: Decimal
    subtotal: Decimal
    created_at: datetime

    class Config:
        from_attributes = True

class OrderBase(BaseModel):
    shipping_address: str = Field(..., max_length=500)
    billing_address: Optional[str] = Field(None, max_length=500)
    shipping_notes: Optional[str] = Field(None, max_length=500)

class OrderCreate(OrderBase):
    order_items: List[OrderItemCreate]

class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    payment_status: Optional[PaymentStatus] = None
    shipping_address: Optional[str] = Field(None, max_length=500)
    billing_address: Optional[str] = Field(None, max_length=500)
    shipping_notes: Optional[str] = Field(None, max_length=500)
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None

class OrderResponse(OrderBase):
    id: uuid.UUID
    user_id: uuid.UUID
    order_number: str
    status: OrderStatus
    payment_status: PaymentStatus
    subtotal: Decimal
    tax_amount: Decimal
    shipping_cost: Decimal
    total_amount: Decimal
    created_at: datetime
    updated_at: Optional[datetime]
    shipped_at: Optional[datetime]
    delivered_at: Optional[datetime]
    order_items: List[OrderItemResponse]

    class Config:
        from_attributes = True

class OrderListResponse(BaseModel):
    message: str
    data: List[OrderResponse]
    metadata: dict

    class Config:
        from_attributes = True

class OrderSummary(BaseModel):
    id: uuid.UUID
    order_number: str
    status: OrderStatus
    payment_status: PaymentStatus
    total_amount: Decimal
    created_at: datetime
    item_count: int

    class Config:
        from_attributes = True
