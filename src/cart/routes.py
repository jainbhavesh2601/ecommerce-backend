from fastapi import APIRouter, Depends, status, Path, Query, Body
from src.db.main import get_db
from src.cart.schema import CartCreate, CartResponse, CartItemCreate, CartItemUpdate, CartItemResponse, CartCheckout
from src.cart.service import CartService
from src.cart.checkout_service import CartCheckoutService
from src.auth.utils import get_current_active_user
from src.auth.user.models import User
from typing import List, Optional
from sqlmodel.ext.asyncio.session import AsyncSession
from decimal import Decimal
import uuid

router = APIRouter()
checkout_service = CartCheckoutService()

@router.get("/me")
async def get_my_cart(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the current user's cart.
    This is the PRIMARY endpoint for accessing your cart.
    Each user has exactly ONE cart that is automatically created during signup.
    """
    return await CartService.get_my_cart(db, current_user)

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_cart(
    cart: CartCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    DEPRECATED: Carts are now auto-created during user signup.
    This endpoint now just returns your existing cart.
    Use GET /carts/me instead.
    """
    return await CartService.get_my_cart(db, current_user)

@router.get("/{cart_id}")
async def get_cart(
    cart_id: uuid.UUID = Path(..., title="The ID of the cart to retrieve"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get cart details by ID"""
    return await CartService.get_cart(db, cart_id, current_user)

# Checkout Routes
@router.post("/{cart_id}/checkout")
async def checkout_cart(
    cart_id: uuid.UUID = Path(..., title="The ID of the cart to checkout"),
    checkout_data: CartCheckout = ...,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Checkout cart and process payment"""
    checkout_data.cart_id = str(cart_id)
    return await checkout_service.checkout_cart(db, checkout_data, current_user)

@router.get("/{cart_id}/checkout/summary")
async def get_checkout_summary(
    cart_id: uuid.UUID = Path(..., title="The ID of the cart"),
    tax_rate: Optional[float] = Query(0.10, ge=0, le=1, description="Tax rate (0.0 to 1.0)"),
    shipping_cost: Optional[float] = Query(0.0, ge=0, description="Shipping cost"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get checkout summary with totals"""
    return await checkout_service.get_checkout_summary(
        db, str(cart_id), current_user, 
        Decimal(str(tax_rate)), Decimal(str(shipping_cost))
    )

@router.get("/{cart_id}/checkout/validate")
async def validate_cart_for_checkout(
    cart_id: uuid.UUID = Path(..., title="The ID of the cart"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Validate cart items before checkout"""
    return await checkout_service.validate_cart_for_checkout(db, str(cart_id), current_user)

@router.delete("/{cart_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cart(
    cart_id: uuid.UUID = Path(..., title="The ID of the cart to delete"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a specific cart (requires authentication)"""
    return await CartService.delete_cart(db, cart_id, current_user)

@router.post("/me/items")
async def add_item_to_my_cart(
    item: CartItemCreate = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add an item to YOUR cart.
    This is the PRIMARY endpoint for adding items to cart.
    No need to know your cart_id - we'll automatically add to your cart.
    """
    # Get user's cart
    cart_response = await CartService.get_my_cart(db, current_user)
    cart_id = cart_response['data']['id']
    
    return await CartService.add_item_to_cart(db, cart_id, item, current_user)

@router.post("/{cart_id}/items")
async def add_item_to_cart(
    cart_id: uuid.UUID = Path(..., title="The ID of the cart to add an item to"),
    item: CartItemCreate = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    LEGACY: Add an item to a specific cart by ID.
    Use POST /carts/me/items instead for simpler usage.
    """
    return await CartService.add_item_to_cart(db, cart_id, item, current_user)

@router.put("/{cart_id}/items/{item_id}")
async def update_cart_item(
    cart_id: uuid.UUID = Path(..., title="The ID of the cart"),
    item_id: uuid.UUID = Path(..., title="The ID of the item to update"),
    item_update: CartItemUpdate = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a specific item in a cart (requires authentication)"""
    return await CartService.update_cart_item(db, cart_id, item_id, item_update, current_user)

@router.delete("/{cart_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_cart_item(
    cart_id: uuid.UUID = Path(..., title="The ID of the cart"),
    item_id: uuid.UUID = Path(..., title="The ID of the item to remove"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a specific item from a cart (requires authentication)"""
    return await CartService.remove_cart_item(db, cart_id, item_id, current_user)
