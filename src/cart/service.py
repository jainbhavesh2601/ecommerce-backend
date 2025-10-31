from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from src.cart.models import Cart, CartItem
from src.cart.schema import CartCreate, CartItemCreate, CartItemUpdate
from src.product.models import Product
from src.auth.user.models import User, UserRole
from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException, status
from src.common.response import ResponseHandler
from src.common.exceptions import NotFoundError
from decimal import Decimal
import uuid

class CartService:
    @staticmethod
    async def get_my_cart(db: AsyncSession, current_user: User) -> Cart:
        """
        Get the current user's cart.
        This is the PRIMARY way users should access their cart.
        Each user has exactly ONE cart (created during signup).
        """
        from sqlalchemy.orm import selectinload
        
        query = select(Cart).options(
            selectinload(Cart.cart_items).selectinload(CartItem.product)
        ).where(Cart.user_id == current_user.id)
        result = await db.execute(query)
        cart = result.scalar_one_or_none()
        
        if not cart:
            # Auto-create cart if somehow it doesn't exist (shouldn't happen)
            cart = Cart(user_id=current_user.id, total_price=Decimal('0.00'))
            db.add(cart)
            await db.commit()
            await db.refresh(cart)
        
        # Convert cart to dict with nested relationships
        cart_dict = {
            "id": cart.id,
            "user_id": cart.user_id,
            "total_price": cart.total_price,
            "created_at": cart.created_at,
            "updated_at": cart.updated_at,
            "cart_items": [
                {
                    "id": item.id,
                    "cart_id": item.cart_id,
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "subtotal_price": item.subtotal_price,
                    "product": {
                        "id": item.product.id,
                        "title": item.product.title,
                        "description": item.product.description,
                        "price": item.product.price,
                        "discount_percentage": item.product.discount_percentage,
                        "rating": item.product.rating,
                        "stock": item.product.stock,
                        "brand": item.product.brand,
                        "thumbnail": item.product.thumbnail,
                        "images": item.product.images,
                        "category_id": item.product.category_id,
                    } if item.product else None
                }
                for item in cart.cart_items
            ]
        }
            
        return ResponseHandler.get_single_success("Cart", cart.id, cart_dict)
    
    @staticmethod
    async def get_cart(db: AsyncSession, cart_id: uuid.UUID, current_user: User) -> Cart:
        """
        Get a specific cart by ID (admin endpoint or legacy support)
        """
        from sqlalchemy.orm import selectinload
        
        query = select(Cart).options(
            selectinload(Cart.cart_items).selectinload(CartItem.product)
        ).where(Cart.id == cart_id)
        result = await db.execute(query)
        cart = result.scalar_one_or_none()
        
        if not cart:
            raise NotFoundError("Cart", cart_id)
        
        # Only allow users to access their own cart (except admins)
        if cart.user_id != current_user.id and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access your own cart"
            )
        
        # Convert cart to dict with nested relationships
        cart_dict = {
            "id": cart.id,
            "user_id": cart.user_id,
            "total_price": cart.total_price,
            "created_at": cart.created_at,
            "updated_at": cart.updated_at,
            "cart_items": [
                {
                    "id": item.id,
                    "cart_id": item.cart_id,
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "subtotal_price": item.subtotal_price,
                    "product": {
                        "id": item.product.id,
                        "title": item.product.title,
                        "description": item.product.description,
                        "price": item.product.price,
                        "discount_percentage": item.product.discount_percentage,
                        "rating": item.product.rating,
                        "stock": item.product.stock,
                        "brand": item.product.brand,
                        "thumbnail": item.product.thumbnail,
                        "images": item.product.images,
                        "category_id": item.product.category_id,
                    } if item.product else None
                }
                for item in cart.cart_items
            ]
        }
            
        return ResponseHandler.get_single_success("Cart", cart_id, cart_dict)
    
    @staticmethod
    async def get_or_create_user_cart(db: AsyncSession, current_user: User) -> Cart:
        """
        DEPRECATED: Use get_my_cart() instead.
        Get user's cart or create one if it doesn't exist.
        """
        return await CartService.get_my_cart(db, current_user)

    @staticmethod
    async def create_cart(db: AsyncSession, cart: CartCreate, current_user: User) -> Cart:
        """
        DEPRECATED: Carts are now auto-created during user signup.
        This just returns the user's existing cart.
        """
        return await CartService.get_my_cart(db, current_user)

    @staticmethod
    async def delete_cart(db: AsyncSession, cart_id: uuid.UUID, current_user: User) -> None:
        query = select(Cart).where(Cart.id == cart_id)
        result = await db.execute(query)
        cart = result.scalar_one_or_none()
        
        if not cart:
            raise NotFoundError("Cart", cart_id)
        
        # Only authenticated users can delete carts
        if current_user.role not in [UserRole.NORMAL_USER, UserRole.SELLER, UserRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only authenticated users can delete carts"
            )
            
        await db.delete(cart)
        await db.commit()
        return ResponseHandler.delete_success("Cart", cart_id, cart)

    @staticmethod
    async def add_item_to_cart(db: AsyncSession, cart_id: uuid.UUID, item: CartItemCreate, current_user: User) -> CartItem:
        # Only authenticated users can add items to cart
        if current_user.role not in [UserRole.NORMAL_USER, UserRole.SELLER, UserRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only authenticated users can add items to cart"
            )
        
        # Verify cart exists
        cart_query = select(Cart).where(Cart.id == cart_id)
        cart_result = await db.execute(cart_query)
        cart = cart_result.scalar_one_or_none()
        
        if not cart:
            raise NotFoundError("Cart", cart_id)
            
        # Verify product exists and get its price
        product_query = select(Product).where(Product.id == item.product_id)
        product_result = await db.execute(product_query)
        product = product_result.scalar_one_or_none()
        
        if not product:
            raise NotFoundError("Product", item.product_id)
            
        # Calculate subtotal
        subtotal = product.price * item.quantity
        
        # Create cart item
        cart_item = CartItem(
            cart_id=cart_id,
            product_id=item.product_id,
            quantity=item.quantity,
            subtotal_price=subtotal
        )
        
        # Update cart total
        cart.total_price += subtotal
        cart.updated_at = datetime.utcnow()
        
        db.add(cart_item)
        db.add(cart)
        await db.commit()
        await db.refresh(cart_item)
        
        return ResponseHandler.create_success("Cart Item", cart_item.id, cart_item)

    @staticmethod
    async def update_cart_item(
        db: AsyncSession,
        cart_id: uuid.UUID,
        item_id: uuid.UUID,
        item_update: CartItemUpdate,
        current_user: User
    ) -> CartItem:
        # Only authenticated users can update cart items
        if current_user.role not in [UserRole.NORMAL_USER, UserRole.SELLER, UserRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only authenticated users can update cart items"
            )
        
        # Get cart item
        query = select(CartItem).where(
            CartItem.id == item_id,
            CartItem.cart_id == cart_id
        )
        result = await db.execute(query)
        cart_item = result.scalar_one_or_none()
        
        if not cart_item:
            raise NotFoundError("Cart Item", item_id)
            
        # Get product for price calculation
        product_query = select(Product).where(Product.id == cart_item.product_id)
        product_result = await db.execute(product_query)
        product = product_result.scalar_one_or_none()
        
        if not product:
            raise NotFoundError("Product", cart_item.product_id)
            
        # Get cart for total update
        cart_query = select(Cart).where(Cart.id == cart_id)
        cart_result = await db.execute(cart_query)
        cart = cart_result.scalar_one_or_none()
        
        if not cart:
            raise NotFoundError("Cart", cart_id)
            
        # Update quantity and recalculate prices
        old_subtotal = cart_item.subtotal_price
        cart_item.quantity = item_update.quantity
        cart_item.subtotal_price = product.price * item_update.quantity
        
        # Update cart total
        cart.total_price = cart.total_price - old_subtotal + cart_item.subtotal_price
        cart.updated_at = datetime.utcnow()
        
        db.add(cart_item)
        db.add(cart)
        await db.commit()
        await db.refresh(cart_item)
        
        return ResponseHandler.update_success("Cart Item", item_id, cart_item)

    @staticmethod
    async def remove_cart_item(
        db: AsyncSession,
        cart_id: uuid.UUID,
        item_id: uuid.UUID,
        current_user: User
    ) -> None:
        # Only authenticated users can remove cart items
        if current_user.role not in [UserRole.NORMAL_USER, UserRole.SELLER, UserRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only authenticated users can remove cart items"
            )
        
        # Get cart item
        query = select(CartItem).where(
            CartItem.id == item_id,
            CartItem.cart_id == cart_id
        )
        result = await db.execute(query)
        cart_item = result.scalar_one_or_none()
        
        if not cart_item:
            raise NotFoundError("Cart Item", item_id)
            
        # Get cart for total update
        cart_query = select(Cart).where(Cart.id == cart_id)
        cart_result = await db.execute(cart_query)
        cart = cart_result.scalar_one_or_none()
        
        if not cart:
            raise NotFoundError("Cart", cart_id)
            
        # Update cart total
        cart.total_price -= cart_item.subtotal_price
        cart.updated_at = datetime.utcnow()
        
        await db.delete(cart_item)
        db.add(cart)
        await db.commit()
        
        return ResponseHandler.delete_success("Cart Item", item_id, cart_item)
