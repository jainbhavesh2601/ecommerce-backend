from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime
from decimal import Decimal
from src.dashboard.models import InvoiceStatus

class DashboardResponse(BaseModel):
    message: str
    data: Dict[str, Any]

class InvoiceBase(BaseModel):
    order_id: uuid.UUID
    due_days: int = Field(default=30, ge=1, le=365)

class InvoiceCreate(InvoiceBase):
    pass

class InvoiceUpdate(BaseModel):
    status: Optional[InvoiceStatus] = None
    notes: Optional[str] = Field(None, max_length=1000)
    terms: Optional[str] = Field(None, max_length=1000)

class InvoiceResponse(BaseModel):
    id: uuid.UUID
    invoice_number: str
    order_id: uuid.UUID
    seller_id: uuid.UUID
    status: InvoiceStatus
    issue_date: datetime
    due_date: datetime
    paid_date: Optional[datetime]
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    customer_name: str
    customer_email: str
    customer_address: str
    seller_name: str
    seller_email: str
    seller_address: Optional[str]
    seller_phone: Optional[str]
    notes: Optional[str]
    terms: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class InvoiceItemResponse(BaseModel):
    id: uuid.UUID
    invoice_id: uuid.UUID
    product_name: str
    product_description: Optional[str]
    unit_price: Decimal
    quantity: int
    total_price: Decimal
    created_at: datetime

    class Config:
        from_attributes = True

class InvoiceWithItemsResponse(BaseModel):
    invoice: InvoiceResponse
    items: List[InvoiceItemResponse]

class InvoiceListResponse(BaseModel):
    message: str
    data: List[InvoiceResponse]
    metadata: Dict[str, Any]

class InvoiceDetailResponse(BaseModel):
    message: str
    data: InvoiceWithItemsResponse
