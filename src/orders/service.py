from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, func, desc
from src.orders.models import Order, OrderItem, OrderStatus, PaymentStatus
from src.orders.schema import OrderCreate, OrderUpdate
from src.orders.notification_service import OrderNotificationService
from src.product.models import Product
from src.auth.user.models import User, UserRole
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from src.common.response import ResponseHandler
from src.common.exceptions import NotFoundError, ValidationError
from decimal import Decimal
import uuid
import random
import string
import logging

logger = logging.getLogger(__name__)

class OrderService:
    @staticmethod
    def generate_order_number() -> str:
        """Generate a unique order number."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"ORD-{timestamp}-{random_suffix}"

    @staticmethod
    async def get_all_orders(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        status: Optional[OrderStatus] = None,
        payment_status: Optional[PaymentStatus] = None,
        user_id: Optional[uuid.UUID] = None,
        current_user: User = None
    ) -> Dict[str, Any]:
        try:
            # Import selectinload for eager loading relationships
            from sqlalchemy.orm import selectinload
            
            query = select(Order).options(selectinload(Order.order_items))
            
            # Apply filters
            if status:
                query = query.where(Order.status == status)
            if payment_status:
                query = query.where(Order.payment_status == payment_status)
            if user_id:
                query = query.where(Order.user_id == user_id)
            
            # Role-based access control
            if current_user.role == UserRole.NORMAL_USER:
                query = query.where(Order.user_id == current_user.id)
            elif current_user.role == UserRole.SELLER:
                # Sellers can only see orders for their products
                from src.product.models import Product
                from src.orders.models import OrderItem
                # Get seller's product IDs
                product_query = select(Product.id).where(Product.seller_id == current_user.id)
                product_result = await db.execute(product_query)
                product_ids = [row[0] for row in product_result.all()]
                
                if product_ids:
                    # Join with OrderItem and filter by product IDs
                    query = query.join(OrderItem, Order.id == OrderItem.order_id).where(
                        OrderItem.product_id.in_(product_ids)
                    ).distinct()
                else:
                    # No products, return empty result
                    query = query.where(False)
            
            query = query.order_by(desc(Order.created_at)).offset(skip).limit(limit)
            result = await db.execute(query)
            orders = result.scalars().all()
            
            # Get total count
            count_query = select(func.count()).select_from(Order)
            if status:
                count_query = count_query.where(Order.status == status)
            if payment_status:
                count_query = count_query.where(Order.payment_status == payment_status)
            if user_id:
                count_query = count_query.where(Order.user_id == user_id)
            if current_user.role == UserRole.NORMAL_USER:
                count_query = count_query.where(Order.user_id == current_user.id)
            elif current_user.role == UserRole.SELLER:
                # Get product_ids variable from above
                if 'product_ids' in locals() and product_ids:
                    from src.orders.models import OrderItem
                    count_query = count_query.join(OrderItem, Order.id == OrderItem.order_id).where(
                        OrderItem.product_id.in_(product_ids)
                    ).distinct()
                else:
                    count_query = count_query.where(False)
            
            total = await db.scalar(count_query)
            
            # Convert orders to response format
            from src.orders.schema import OrderResponse, OrderItemResponse
            
            orders_response = []
            for order in orders:
                # Convert order items to response format
                order_items_response = [
                    OrderItemResponse(
                        id=item.id,
                        order_id=item.order_id,
                        product_id=item.product_id,
                        product_name=item.product_name,
                        product_price=item.product_price,
                        quantity=item.quantity,
                        subtotal=item.subtotal,
                        created_at=item.created_at
                    )
                    for item in order.order_items
                ]
                
                # Create OrderResponse
                order_response = OrderResponse(
                    id=order.id,
                    user_id=order.user_id,
                    order_number=order.order_number,
                    status=order.status,
                    payment_status=order.payment_status,
                    shipping_address=order.shipping_address,
                    billing_address=order.billing_address,
                    shipping_notes=order.shipping_notes,
                    subtotal=order.subtotal,
                    tax_amount=order.tax_amount,
                    shipping_cost=order.shipping_cost,
                    total_amount=order.total_amount,
                    created_at=order.created_at,
                    updated_at=order.updated_at,
                    shipped_at=order.shipped_at,
                    delivered_at=order.delivered_at,
                    order_items=order_items_response
                )
                orders_response.append(order_response)
            
            return {
                "message": "Successfully retrieved orders",
                "data": orders_response,
                "metadata": {
                    "skip": skip,
                    "limit": limit,
                    "total": total
                }
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving orders: {str(e)}"
            )

    @staticmethod
    async def get_order(db: AsyncSession, order_id: uuid.UUID, current_user: User) -> Order:
        try:
            query = select(Order).where(Order.id == order_id)
            result = await db.execute(query)
            order = result.scalar_one_or_none()
            
            if not order:
                raise NotFoundError("Order", order_id)
            
            # Check permissions
            if current_user.role == UserRole.NORMAL_USER and order.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only view your own orders"
                )
            
            return ResponseHandler.get_single_success("Order", order_id, order)
        except (NotFoundError, HTTPException):
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving order: {str(e)}"
            )

    @staticmethod
    async def create_order(db: AsyncSession, order_data: OrderCreate, current_user: User) -> Order:
        try:
            logger.info(f"Creating order for user {current_user.id}")
            logger.info(f"Order data: {order_data}")
            
            # Validate products and calculate totals
            subtotal = Decimal('0.00')
            order_items_data = []
            
            for item in order_data.order_items:
                # Get product
                product_query = select(Product).where(Product.id == item.product_id)
                product_result = await db.execute(product_query)
                product = product_result.scalar_one_or_none()
                
                if not product:
                    raise NotFoundError("Product", item.product_id)
                
                if product.stock < item.quantity:
                    raise ValidationError(f"Insufficient stock for product {product.title}. Available: {product.stock}")
                
                # Calculate item subtotal
                item_subtotal = product.price * item.quantity
                subtotal += item_subtotal
                
                order_items_data.append({
                    "product_id": item.product_id,
                    "product_name": product.title,
                    "product_price": product.price,
                    "quantity": item.quantity,
                    "subtotal": item_subtotal
                })
            
            # Calculate tax and shipping (simplified)
            tax_amount = subtotal * Decimal('0.10')  # 10% tax
            shipping_cost = Decimal('10.00')  # Fixed shipping cost
            total_amount = subtotal + tax_amount + shipping_cost
            
            # Create order
            order_dict = order_data.model_dump(exclude={"order_items"})
            order_dict.update({
                "user_id": current_user.id,
                "order_number": OrderService.generate_order_number(),
                "subtotal": subtotal,
                "tax_amount": tax_amount,
                "shipping_cost": shipping_cost,
                "total_amount": total_amount,
                "status": OrderStatus.PENDING,
                "payment_status": PaymentStatus.PENDING
            })
            
            logger.info(f"Creating order with dict: {order_dict}")
            db_order = Order(**order_dict)
            db.add(db_order)
            await db.flush()  # Get the order ID
            logger.info(f"Order created with ID: {db_order.id}")
            
            # Create order items and update product stock
            for item_data in order_items_data:
                order_item = OrderItem(
                    order_id=db_order.id,
                    **item_data
                )
                db.add(order_item)
                
                # Update product stock
                product_query = select(Product).where(Product.id == item_data["product_id"])
                product_result = await db.execute(product_query)
                product = product_result.scalar_one_or_none()
                product.stock -= item_data["quantity"]
                db.add(product)
            
            await db.commit()
            await db.refresh(db_order)
            
            from sqlalchemy.orm import selectinload
            order_query = select(Order).options(selectinload(Order.order_items)).where(Order.id == db_order.id)
            order_result = await db.execute(order_query)
            db_order_with_items = order_result.scalar_one_or_none()
            
            if not db_order_with_items:
                raise ValueError(f"Failed to retrieve order {db_order.id} with items")
            
            # Send order confirmation email to customer
            try:
                # Get order items for email
                order_items_query = select(OrderItem).where(OrderItem.order_id == db_order.id)
                order_items_result = await db.execute(order_items_query)
                order_items = order_items_result.scalars().all()
                
                # Send confirmation email
                await OrderNotificationService.send_order_confirmation_email(
                    db_order, order_items, current_user
                )
                
                # Send notification to sellers
                # Get unique sellers from order items
                seller_ids = set()
                for item in order_items:
                    product_query = select(Product).where(Product.id == item.product_id)
                    product_result = await db.execute(product_query)
                    product = product_result.scalar_one_or_none()
                    if product:
                        seller_ids.add(product.seller_id)
                
                # Get seller users
                if seller_ids:
                    sellers_query = select(User).where(User.id.in_(seller_ids))
                    sellers_result = await db.execute(sellers_query)
                    sellers = sellers_result.scalars().all()
                    
                    # Send notifications to sellers
                    await OrderNotificationService.send_new_order_notification_to_sellers(
                        db_order, order_items, current_user, sellers
                    )
                
            except Exception as e:
                logger.error(f"Failed to send order notifications: {str(e)}")
                # Don't fail the order creation if email fails
            
            # Convert to dict for proper serialization
            from src.orders.schema import OrderResponse, OrderItemResponse
            
            # Convert order items to response format
            order_items_response = [
                OrderItemResponse(
                    id=item.id,
                    order_id=item.order_id,
                    product_id=item.product_id,
                    product_name=item.product_name,
                    product_price=item.product_price,
                    quantity=item.quantity,
                    subtotal=item.subtotal,
                    created_at=item.created_at
                )
                for item in db_order_with_items.order_items
            ]
            
            # Create OrderResponse
            order_response = OrderResponse(
                id=db_order_with_items.id,
                user_id=db_order_with_items.user_id,
                order_number=db_order_with_items.order_number,
                status=db_order_with_items.status,
                payment_status=db_order_with_items.payment_status,
                shipping_address=db_order_with_items.shipping_address,
                billing_address=db_order_with_items.billing_address,
                shipping_notes=db_order_with_items.shipping_notes,
                subtotal=db_order_with_items.subtotal,
                tax_amount=db_order_with_items.tax_amount,
                shipping_cost=db_order_with_items.shipping_cost,
                total_amount=db_order_with_items.total_amount,
                created_at=db_order_with_items.created_at,
                updated_at=db_order_with_items.updated_at,
                shipped_at=db_order_with_items.shipped_at,
                delivered_at=db_order_with_items.delivered_at,
                order_items=order_items_response
            )
            
            # Return the order directly instead of using ResponseHandler
            return order_response
        except (NotFoundError, ValidationError) as e:
            logger.error(f"Validation/NotFound error: {str(e)}")
            await db.rollback()
            raise
        except Exception as e:
            import traceback
            logger.error(f"Error creating order: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating order: {str(e)}"
            )

    @staticmethod
    async def update_order(
        db: AsyncSession,
        order_id: uuid.UUID,
        order_update: OrderUpdate,
        current_user: User
    ) -> Order:
        try:
            query = select(Order).where(Order.id == order_id)
            result = await db.execute(query)
            db_order = result.scalar_one_or_none()
            
            if not db_order:
                raise NotFoundError("Order", order_id)
            
            # Check permissions
            if current_user.role == UserRole.NORMAL_USER and db_order.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only update your own orders"
                )
            
            # Store old status for notification
            old_status = db_order.status
            old_payment_status = db_order.payment_status
            
            # Update fields
            for key, value in order_update.model_dump(exclude_unset=True).items():
                setattr(db_order, key, value)
            
            db_order.updated_at = datetime.utcnow()
            
            db.add(db_order)
            await db.commit()
            await db.refresh(db_order)
            
            # Send notifications for status changes
            try:
                # Get customer for notifications
                customer_query = select(User).where(User.id == db_order.user_id)
                customer_result = await db.execute(customer_query)
                customer = customer_result.scalar_one_or_none()
                
                if customer:
                    # Send status update email if status changed
                    if old_status != db_order.status:
                        await OrderNotificationService.send_order_status_update_email(
                            db_order, customer, old_status, db_order.status
                        )
                    
                    # Send payment confirmation email if payment status changed to PAID
                    if old_payment_status != db_order.payment_status and db_order.payment_status == PaymentStatus.PAID:
                        await OrderNotificationService.send_payment_confirmation_email(
                            db_order, customer
                        )
                    
                    # Send shipped email if status changed to SHIPPED
                    if old_status != db_order.status and db_order.status == OrderStatus.SHIPPED:
                        await OrderNotificationService.send_order_shipped_email(
                            db_order, customer
                        )
                
            except Exception as e:
                logger.error(f"Failed to send order update notifications: {str(e)}")
                # Don't fail the order update if email fails
            
            return ResponseHandler.update_success("Order", order_id, db_order)
        except (NotFoundError, HTTPException):
            raise
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error updating order: {str(e)}"
            )

    @staticmethod
    async def cancel_order(db: AsyncSession, order_id: uuid.UUID, current_user: User) -> Order:
        try:
            query = select(Order).where(Order.id == order_id)
            result = await db.execute(query)
            order = result.scalar_one_or_none()
            
            if not order:
                raise NotFoundError("Order", order_id)
            
            # Check permissions
            if current_user.role == UserRole.NORMAL_USER and order.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only cancel your own orders"
                )
            
            # Check if order can be cancelled
            if order.status in [OrderStatus.SHIPPED, OrderStatus.DELIVERED, OrderStatus.CANCELLED]:
                raise ValidationError(f"Order cannot be cancelled. Current status: {order.status}")
            
            # Update order status
            order.status = OrderStatus.CANCELLED
            order.updated_at = datetime.utcnow()
            
            # Restore product stock
            order_items_query = select(OrderItem).where(OrderItem.order_id == order_id)
            order_items_result = await db.execute(order_items_query)
            order_items = order_items_result.scalars().all()
            
            for item in order_items:
                product_query = select(Product).where(Product.id == item.product_id)
                product_result = await db.execute(product_query)
                product = product_result.scalar_one_or_none()
                if product:
                    product.stock += item.quantity
                    db.add(product)
            
            db.add(order)
            await db.commit()
            await db.refresh(order)
            
            return ResponseHandler.update_success("Order", order_id, order)
        except (NotFoundError, ValidationError, HTTPException):
            raise
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error cancelling order: {str(e)}"
            )

    @staticmethod
    async def get_user_orders(
        db: AsyncSession,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
        current_user: User = None
    ) -> Dict[str, Any]:
        try:
            # Check permissions
            if current_user.role == UserRole.NORMAL_USER and current_user.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only view your own orders"
                )
            
            return await OrderService.get_all_orders(
                db, skip, limit, user_id=user_id, current_user=current_user
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving user orders: {str(e)}"
            )
