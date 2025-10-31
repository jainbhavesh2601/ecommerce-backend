from fastapi import APIRouter, Depends, Query, Path, status, HTTPException
from src.db.main import get_db
from src.orders.schema import (
    OrderCreate, OrderUpdate, OrderResponse, OrderListResponse
)
from src.orders.service import OrderService
from src.orders.models import OrderStatus, PaymentStatus
from src.auth.user.models import User
from src.auth.utils import get_current_active_user, require_admin, require_seller_or_admin
from src.common.exceptions import NotFoundError, ValidationError
from typing import Dict, Any, Optional
from sqlmodel.ext.asyncio.session import AsyncSession
import uuid

router = APIRouter()

@router.get("/")
async def get_all_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    status: Optional[OrderStatus] = Query(None),
    payment_status: Optional[PaymentStatus] = Query(None),
    current_user: User = Depends(require_seller_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all orders (Seller/Admin only).
    """
    try:
        return await OrderService.get_all_orders(
            db, skip, limit, status, payment_status, current_user=current_user
        )
    except Exception as e:
        raise e

@router.get("/my-orders")
async def get_my_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    status: Optional[OrderStatus] = Query(None),
    payment_status: Optional[PaymentStatus] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's orders.
    """
    try:
        return await OrderService.get_all_orders(
            db, skip, limit, status, payment_status, 
            user_id=current_user.id, current_user=current_user
        )
    except Exception as e:
        raise e

@router.get("/user/{user_id}")
async def get_user_orders(
    user_id: uuid.UUID = Path(..., description="The UUID of the user"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get orders for a specific user (Admin only).
    """
    try:
        return await OrderService.get_user_orders(db, user_id, skip, limit, current_user)
    except Exception as e:
        raise e

@router.get("/{order_id}")
async def get_order(
    order_id: uuid.UUID = Path(..., description="The UUID of the order"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific order by ID.
    Users can only view their own orders unless they are admin/seller.
    """
    try:
        return await OrderService.get_order(db, order_id, current_user)
    except (NotFoundError, HTTPException):
        raise
    except Exception as e:
        raise e

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_order(
    order: OrderCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new order.
    """
    try:
        return await OrderService.create_order(db, order, current_user)
    except (NotFoundError, ValidationError):
        raise
    except Exception as e:
        raise e

@router.put("/{order_id}")
async def update_order(
    order_id: uuid.UUID = Path(..., description="The UUID of the order"),
    order_update: OrderUpdate = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update an order.
    Users can only update their own orders unless they are admin/seller.
    """
    try:
        return await OrderService.update_order(db, order_id, order_update, current_user)
    except (NotFoundError, ValidationError, HTTPException):
        raise
    except Exception as e:
        raise e

@router.post("/{order_id}/cancel")
async def cancel_order(
    order_id: uuid.UUID = Path(..., description="The UUID of the order"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel an order.
    Users can only cancel their own orders.
    """
    try:
        return await OrderService.cancel_order(db, order_id, current_user)
    except (NotFoundError, ValidationError, HTTPException):
        raise
    except Exception as e:
        raise e

@router.put("/{order_id}/status")
async def update_order_status(
    order_id: uuid.UUID = Path(..., description="The UUID of the order"),
    status: OrderStatus = Query(..., description="New order status"),
    current_user: User = Depends(require_seller_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Update order status (Seller/Admin only).
    """
    try:
        order_update = OrderUpdate(status=status)
        return await OrderService.update_order(db, order_id, order_update, current_user)
    except (NotFoundError, ValidationError, HTTPException):
        raise
    except Exception as e:
        raise e

@router.put("/{order_id}/payment-status")
async def update_payment_status(
    order_id: uuid.UUID = Path(..., description="The UUID of the order"),
    payment_status: PaymentStatus = Query(..., description="New payment status"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Update payment status (Admin only).
    """
    try:
        order_update = OrderUpdate(payment_status=payment_status)
        return await OrderService.update_order(db, order_id, order_update, current_user)
    except (NotFoundError, ValidationError, HTTPException):
        raise
    except Exception as e:
        raise e
