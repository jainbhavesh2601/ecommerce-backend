from fastapi import APIRouter, Depends, status, Query, Path, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Optional, Dict, Any
import uuid

from src.db.main import get_db
from src.auth.utils import get_current_active_user
from src.auth.user.models import User
from src.payment.service import PaymentService
from src.payment.schema import (
    PaymentIntentCreate, PaymentConfirm, PaymentResponse, PaymentListResponse,
    PaymentMethodCreate, PaymentMethodUpdate, PaymentMethodResponse,
    RefundCreate, RefundResponse, PaymentWebhook, PaymentStatusUpdate
)
from src.payment.models import PaymentStatus, PaymentProviderEnum

router = APIRouter()
payment_service = PaymentService()

# Payment Intent Routes
@router.post("/intents", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment_intent(
    payment_data: PaymentIntentCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a payment intent for an order"""
    return await payment_service.create_payment_intent(db, payment_data, current_user)

@router.post("/confirm", response_model=PaymentResponse)
async def confirm_payment(
    payment_data: PaymentConfirm,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Confirm a payment intent"""
    return await payment_service.confirm_payment(db, payment_data, current_user)

# Payment Routes
@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: uuid.UUID = Path(..., description="Payment ID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get payment details by ID"""
    return await payment_service.get_payment(db, str(payment_id), current_user)

@router.get("/", response_model=PaymentListResponse)
async def get_user_payments(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[PaymentStatus] = Query(None, description="Filter by payment status"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's payments with pagination"""
    result = await payment_service.get_user_payments(db, current_user, page, limit, status)
    return PaymentListResponse(**result)

# Refund Routes
@router.post("/refunds", response_model=RefundResponse, status_code=status.HTTP_201_CREATED)
async def create_refund(
    refund_data: RefundCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a payment refund"""
    return await payment_service.create_refund(db, refund_data, current_user)

# Payment Method Routes
@router.post("/methods", response_model=PaymentMethodResponse, status_code=status.HTTP_201_CREATED)
async def create_payment_method(
    method_data: PaymentMethodCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a saved payment method"""
    return await payment_service.create_payment_method(db, method_data, current_user)

@router.get("/methods/", response_model=List[PaymentMethodResponse])
async def get_payment_methods(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's saved payment methods"""
    return await payment_service.get_user_payment_methods(db, current_user)

@router.put("/methods/{method_id}", response_model=PaymentMethodResponse)
async def update_payment_method(
    method_id: uuid.UUID = Path(..., description="Payment method ID"),
    method_update: PaymentMethodUpdate = ...,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a payment method"""
    return await payment_service.update_payment_method(db, str(method_id), method_update, current_user)

@router.delete("/methods/{method_id}")
async def delete_payment_method(
    method_id: uuid.UUID = Path(..., description="Payment method ID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a payment method"""
    success = await payment_service.delete_payment_method(db, str(method_id), current_user)
    if success:
        return {"message": "Payment method deleted successfully"}
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to delete payment method")

# Webhook Routes
@router.post("/webhooks/{provider}")
async def process_payment_webhook(
    provider: PaymentProviderEnum = Path(..., description="Payment provider"),
    webhook_data: PaymentWebhook = ...,
    db: AsyncSession = Depends(get_db)
):
    """Process payment provider webhook"""
    success = await payment_service.process_webhook(
        db, provider.value, webhook_data.data, webhook_data.signature
    )
    
    if success:
        return {"status": "success", "message": "Webhook processed successfully"}
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Webhook processing failed")

# Admin Routes
@router.put("/{payment_id}/status", response_model=PaymentResponse)
async def update_payment_status(
    payment_id: uuid.UUID = Path(..., description="Payment ID"),
    status_update: PaymentStatusUpdate = ...,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update payment status (Admin only)"""
    # Check if user is admin
    if current_user.role not in ['admin']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    # This would be implemented in the service
    # For now, return a placeholder response
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet")

# Health Check
@router.get("/health")
async def payment_health_check():
    """Check payment system health"""
    return {
        "status": "healthy",
        "providers": list(payment_service.providers.keys()),
        "message": "Payment system is operational"
    }
