from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime
import uuid
import logging
from fastapi import HTTPException, status

from src.cart.models import Cart, CartItem
from src.cart.schema import CartCheckout
from src.orders.models import Order, OrderItem, OrderStatus
from src.orders.schema import OrderCreate, OrderItemCreate
from src.payment.service import PaymentService
from src.payment.schema import PaymentIntentCreate, PaymentResponse
from src.payment.models import PaymentMethod, PaymentProvider
from src.product.models import Product
from src.auth.user.models import User
from src.common.exceptions import NotFoundError, ValidationError

logger = logging.getLogger(__name__)

class CartCheckoutService:
    """Service for handling cart checkout and payment processing"""
    
    def __init__(self):
        self.payment_service = PaymentService()
    
    def _generate_order_number(self) -> str:
        """Generate unique order number"""
        return f"ORD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    
    async def checkout_cart(
        self,
        db: AsyncSession,
        checkout_data: CartCheckout,
        current_user: User
    ) -> Dict[str, Any]:
        """Process cart checkout with payment"""
        try:
            # Get cart and verify ownership
            cart_query = select(Cart).where(Cart.id == checkout_data.cart_id)
            cart_result = await db.execute(cart_query)
            cart = cart_result.scalar_one_or_none()
            
            if not cart:
                raise NotFoundError("Cart", checkout_data.cart_id)
            
            # Get cart items
            cart_items_query = select(CartItem).where(CartItem.cart_id == checkout_data.cart_id)
            cart_items_result = await db.execute(cart_items_query)
            cart_items = cart_items_result.scalars().all()
            
            if not cart_items:
                raise ValidationError("Cart is empty")
            
            # Verify all products are still available and get current prices
            order_items = []
            total_amount = Decimal('0.00')
            
            for cart_item in cart_items:
                # Get product details
                product_query = select(Product).where(Product.id == cart_item.product_id)
                product_result = await db.execute(product_query)
                product = product_result.scalar_one_or_none()
                
                if not product:
                    raise ValidationError(f"Product {cart_item.product_id} no longer exists")
                
                if not product.is_active:
                    raise ValidationError(f"Product {product.title} is no longer available")
                
                if product.stock_quantity < cart_item.quantity:
                    raise ValidationError(f"Insufficient stock for product {product.title}")
                
                # Calculate item total
                item_total = product.price * cart_item.quantity
                total_amount += item_total
                
                # Create order item
                order_item = OrderItemCreate(
                    product_id=cart_item.product_id,
                    quantity=cart_item.quantity
                )
                order_items.append(order_item)
            
            # Calculate tax and shipping
            tax_amount = total_amount * checkout_data.tax_rate
            shipping_cost = checkout_data.shipping_cost
            final_total = total_amount + tax_amount + shipping_cost
            
            # Create order
            order_data = OrderCreate(
                shipping_address=checkout_data.shipping_address,
                billing_address=checkout_data.billing_address or checkout_data.shipping_address,
                shipping_notes=checkout_data.shipping_notes,
                order_items=order_items
            )
            
            # Create order in database
            order = Order(
                user_id=current_user.id,
                order_number=self._generate_order_number(),
                status=OrderStatus.PENDING,
                subtotal=total_amount,
                tax_amount=tax_amount,
                shipping_cost=shipping_cost,
                total_amount=final_total,
                shipping_address=checkout_data.shipping_address,
                billing_address=checkout_data.billing_address or checkout_data.shipping_address,
                shipping_notes=checkout_data.shipping_notes
            )
            
            db.add(order)
            await db.flush()  # Get the order ID
            
            # Create order items
            for cart_item in cart_items:
                product_query = select(Product).where(Product.id == cart_item.product_id)
                product_result = await db.execute(product_query)
                product = product_result.scalar_one_or_none()
                
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=cart_item.product_id,
                    product_name=product.title,
                    product_price=product.price,
                    quantity=cart_item.quantity,
                    subtotal=product.price * cart_item.quantity
                )
                
                db.add(order_item)
            
            await db.commit()
            await db.refresh(order)
            
            # Create payment intent
            payment_intent_data = PaymentIntentCreate(
                order_id=str(order.id),
                amount=final_total,
                currency="USD",
                payment_method=checkout_data.payment_method,
                payment_provider=checkout_data.payment_provider,
                customer_email=checkout_data.customer_email or current_user.email,
                customer_name=checkout_data.customer_name or current_user.full_name,
                metadata={
                    'order_number': order.order_number,
                    'cart_id': checkout_data.cart_id,
                    'shipping_address': checkout_data.shipping_address
                }
            )
            
            payment = await self.payment_service.create_payment_intent(
                db, payment_intent_data, current_user
            )
            
            # Clear cart after successful checkout
            await self._clear_cart(db, checkout_data.cart_id)
            
            return {
                "order": {
                    "id": str(order.id),
                    "order_number": order.order_number,
                    "status": order.status.value,
                    "total_amount": float(order.total_amount),
                    "created_at": order.created_at.isoformat()
                },
                "payment": payment.dict(),
                "requires_action": payment.client_secret is not None,
                "action_url": None  # Will be set by payment provider if needed
            }
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error during cart checkout: {str(e)}")
            raise
    
    async def _clear_cart(self, db: AsyncSession, cart_id: str) -> None:
        """Clear cart items after successful checkout"""
        try:
            # Delete cart items
            cart_items_query = select(CartItem).where(CartItem.cart_id == cart_id)
            cart_items_result = await db.execute(cart_items_query)
            cart_items = cart_items_result.scalars().all()
            
            for cart_item in cart_items:
                await db.delete(cart_item)
            
            # Reset cart total
            cart_query = select(Cart).where(Cart.id == cart_id)
            cart_result = await db.execute(cart_query)
            cart = cart_result.scalar_one_or_none()
            
            if cart:
                cart.total_price = Decimal('0.00')
                cart.updated_at = datetime.utcnow()
                db.add(cart)
            
            await db.commit()
            
        except Exception as e:
            logger.error(f"Error clearing cart: {str(e)}")
            # Don't raise exception here as checkout was successful
    
    async def get_checkout_summary(
        self,
        db: AsyncSession,
        cart_id: str,
        current_user: User,
        tax_rate: Optional[Decimal] = None,
        shipping_cost: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """Get checkout summary with totals"""
        try:
            # Get cart and items
            cart_query = select(Cart).where(Cart.id == cart_id)
            cart_result = await db.execute(cart_query)
            cart = cart_result.scalar_one_or_none()
            
            if not cart:
                raise NotFoundError("Cart", cart_id)
            
            cart_items_query = select(CartItem).where(CartItem.cart_id == cart_id)
            cart_items_result = await db.execute(cart_items_query)
            cart_items = cart_items_result.scalars().all()
            
            if not cart_items:
                raise ValidationError("Cart is empty")
            
            # Calculate totals
            subtotal = Decimal('0.00')
            items_summary = []
            
            for cart_item in cart_items:
                product_query = select(Product).where(Product.id == cart_item.product_id)
                product_result = await db.execute(product_query)
                product = product_result.scalar_one_or_none()
                
                if product:
                    item_total = product.price * cart_item.quantity
                    subtotal += item_total
                    
                    items_summary.append({
                        "product_id": str(product.id),
                        "product_name": product.title,
                        "price": float(product.price),
                        "quantity": cart_item.quantity,
                        "subtotal": float(item_total),
                        "image_url": product.image_url
                    })
            
            # Calculate tax and shipping
            tax_rate = tax_rate or Decimal('0.10')  # Default 10% tax
            shipping_cost = shipping_cost or Decimal('0.00')
            tax_amount = subtotal * tax_rate
            total = subtotal + tax_amount + shipping_cost
            
            return {
                "cart_id": cart_id,
                "items": items_summary,
                "totals": {
                    "subtotal": float(subtotal),
                    "tax_rate": float(tax_rate),
                    "tax_amount": float(tax_amount),
                    "shipping_cost": float(shipping_cost),
                    "total": float(total)
                },
                "item_count": len(items_summary),
                "total_quantity": sum(item["quantity"] for item in items_summary)
            }
            
        except Exception as e:
            logger.error(f"Error getting checkout summary: {str(e)}")
            raise
    
    async def validate_cart_for_checkout(
        self,
        db: AsyncSession,
        cart_id: str,
        current_user: User
    ) -> Dict[str, Any]:
        """Validate cart items before checkout"""
        try:
            # Get cart items
            cart_items_query = select(CartItem).where(CartItem.cart_id == cart_id)
            cart_items_result = await db.execute(cart_items_query)
            cart_items = cart_items_result.scalars().all()
            
            if not cart_items:
                return {
                    "valid": False,
                    "errors": ["Cart is empty"],
                    "warnings": []
                }
            
            errors = []
            warnings = []
            
            for cart_item in cart_items:
                product_query = select(Product).where(Product.id == cart_item.product_id)
                product_result = await db.execute(product_query)
                product = product_result.scalar_one_or_none()
                
                if not product:
                    errors.append(f"Product {cart_item.product_id} no longer exists")
                    continue
                
                if not product.is_active:
                    errors.append(f"Product '{product.title}' is no longer available")
                    continue
                
                if product.stock_quantity < cart_item.quantity:
                    errors.append(f"Insufficient stock for '{product.title}'. Available: {product.stock_quantity}, Requested: {cart_item.quantity}")
                    continue
                
                # Check for price changes
                if product.price != cart_item.subtotal_price / cart_item.quantity:
                    warnings.append(f"Price for '{product.title}' has changed from ${cart_item.subtotal_price / cart_item.quantity} to ${product.price}")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "item_count": len(cart_items)
            }
            
        except Exception as e:
            logger.error(f"Error validating cart: {str(e)}")
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": []
            }
