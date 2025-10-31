from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, func, desc, and_, or_
from src.orders.models import Order, OrderItem, OrderStatus, PaymentStatus
from src.product.models import Product
from src.auth.user.models import User, UserRole
from src.dashboard.models import Invoice, InvoiceItem, InvoiceStatus
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from src.common.response import ResponseHandler
from src.common.exceptions import NotFoundError, ValidationError
from decimal import Decimal
import uuid
import random
import string
from sqlalchemy.orm import selectinload

class DashboardService:
    @staticmethod
    async def get_seller_dashboard(
        db: AsyncSession,
        seller_id: uuid.UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get dashboard data for a seller"""
        try:
            # Date range for analytics
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Get seller's products
            products_query = select(Product).where(Product.seller_id == seller_id)
            products_result = await db.execute(products_query)
            products = products_result.scalars().all()
            product_ids = [p.id for p in products]
            
            if not product_ids:
                return {
                    "message": "Dashboard data retrieved successfully",
                    "data": {
                        "total_products": 0,
                        "total_orders": 0,
                        "total_revenue": Decimal('0.00'),
                        "pending_orders": 0,
                        "recent_orders": [],
                        "top_products": [],
                        "revenue_by_day": [],
                        "order_status_breakdown": {},
                        "payment_status_breakdown": {}
                    }
                }
            
            # Get orders for seller's products
            orders_query = select(Order).options(selectinload(Order.user), selectinload(Order.order_items)).join(OrderItem).where(
                and_(
                    OrderItem.product_id.in_(product_ids),
                    Order.created_at >= start_date
                )
            ).distinct()
            orders_result = await db.execute(orders_query)
            orders = orders_result.scalars().all()
            
            # Calculate metrics
            total_orders = len(orders)
            total_revenue = sum(order.total_amount for order in orders if order.payment_status == PaymentStatus.PAID)
            pending_orders = len([o for o in orders if o.status in [OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PROCESSING]])
            
            # Get recent orders (last 10)
            recent_orders_query = select(Order).options(selectinload(Order.user), selectinload(Order.order_items)).join(OrderItem).where(
                and_(
                    OrderItem.product_id.in_(product_ids),
                    Order.created_at >= start_date
                )
            ).order_by(desc(Order.created_at)).limit(10).distinct()
            recent_orders_result = await db.execute(recent_orders_query)
            recent_orders = recent_orders_result.scalars().all()
            
            # Get top products by quantity sold
            top_products_query = select(
                Product.title,
                Product.id,
                func.sum(OrderItem.quantity).label('total_sold'),
                func.sum(OrderItem.subtotal).label('total_revenue')
            ).join(OrderItem).join(Order).where(
                and_(
                    OrderItem.product_id.in_(product_ids),
                    Order.created_at >= start_date,
                    Order.payment_status == PaymentStatus.PAID
                )
            ).group_by(Product.id, Product.title).order_by(desc('total_sold')).limit(5)
            
            top_products_result = await db.execute(top_products_query)
            top_products = top_products_result.all()
            
            # Revenue by day (last 30 days)
            revenue_by_day = []
            for i in range(days):
                day = start_date + timedelta(days=i)
                day_orders = [o for o in orders if o.created_at.date() == day.date() and o.payment_status == PaymentStatus.PAID]
                day_revenue = sum(order.total_amount for order in day_orders)
                revenue_by_day.append({
                    "date": day.strftime("%Y-%m-%d"),
                    "revenue": float(day_revenue)
                })
            
            # Order status breakdown
            order_status_breakdown = {}
            for status in OrderStatus:
                count = len([o for o in orders if o.status == status])
                order_status_breakdown[status.value] = count
            
            # Payment status breakdown
            payment_status_breakdown = {}
            for status in PaymentStatus:
                count = len([o for o in orders if o.payment_status == status])
                payment_status_breakdown[status.value] = count
            
            return {
                "message": "Dashboard data retrieved successfully",
                "data": {
                    "total_products": len(products),
                    "total_orders": total_orders,
                    "total_revenue": float(total_revenue),
                    "pending_orders": pending_orders,
                    "recent_orders": [
                        {
                            "id": str(order.id),
                            "order_number": order.order_number,
                            "status": order.status.value,
                            "payment_status": order.payment_status.value,
                            "total_amount": float(order.total_amount),
                            "created_at": order.created_at.isoformat(),
                            "customer_name": order.user.full_name if order.user else "Unknown"
                        }
                        for order in recent_orders
                    ],
                    "top_products": [
                        {
                            "id": str(product.id),
                            "title": product.title,
                            "total_sold": product.total_sold,
                            "total_revenue": float(product.total_revenue)
                        }
                        for product in top_products
                    ],
                    "revenue_by_day": revenue_by_day,
                    "order_status_breakdown": order_status_breakdown,
                    "payment_status_breakdown": payment_status_breakdown
                }
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving dashboard data: {str(e)}"
            )

    @staticmethod
    async def get_admin_dashboard(
        db: AsyncSession,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get dashboard data for admin"""
        try:
            # Date range for analytics
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Get all orders in date range
            orders_query = select(Order).options(selectinload(Order.user), selectinload(Order.order_items)).where(Order.created_at >= start_date)
            orders_result = await db.execute(orders_query)
            orders = orders_result.scalars().all()
            
            # Get all users
            users_query = select(User)
            users_result = await db.execute(users_query)
            users = users_result.scalars().all()
            
            # Get all products
            products_query = select(Product)
            products_result = await db.execute(products_query)
            products = products_result.scalars().all()
            
            # Calculate metrics
            total_users = len(users)
            total_sellers = len([u for u in users if u.role == UserRole.SELLER])
            total_products = len(products)
            total_orders = len(orders)
            total_revenue = sum(order.total_amount for order in orders if order.payment_status == PaymentStatus.PAID)
            
            # Get recent orders
            recent_orders_query = select(Order).options(selectinload(Order.user), selectinload(Order.order_items)).order_by(desc(Order.created_at)).limit(10)
            recent_orders_result = await db.execute(recent_orders_query)
            recent_orders = recent_orders_result.scalars().all()
            
            # Get top sellers by revenue
            top_sellers_query = select(
                User.full_name,
                User.id,
                func.sum(Order.total_amount).label('total_revenue'),
                func.count(Order.id).label('total_orders')
            ).join(Product, User.id == Product.seller_id).join(OrderItem, Product.id == OrderItem.product_id).join(Order, OrderItem.order_id == Order.id).where(
                and_(
                    Order.created_at >= start_date,
                    Order.payment_status == PaymentStatus.PAID
                )
            ).group_by(User.id, User.full_name).order_by(desc('total_revenue')).limit(5)
            
            top_sellers_result = await db.execute(top_sellers_query)
            top_sellers = top_sellers_result.all()
            
            # Revenue by day
            revenue_by_day = []
            for i in range(days):
                day = start_date + timedelta(days=i)
                day_orders = [o for o in orders if o.created_at.date() == day.date() and o.payment_status == PaymentStatus.PAID]
                day_revenue = sum(order.total_amount for order in day_orders)
                revenue_by_day.append({
                    "date": day.strftime("%Y-%m-%d"),
                    "revenue": float(day_revenue)
                })
            
            # User growth by day
            user_growth_by_day = []
            for i in range(days):
                day = start_date + timedelta(days=i)
                day_users = [u for u in users if u.created_at.date() <= day.date()]
                user_growth_by_day.append({
                    "date": day.strftime("%Y-%m-%d"),
                    "total_users": len(day_users)
                })
            
            # Order status breakdown
            order_status_breakdown = {}
            for status in OrderStatus:
                count = len([o for o in orders if o.status == status])
                order_status_breakdown[status.value] = count
            
            # Payment status breakdown
            payment_status_breakdown = {}
            for status in PaymentStatus:
                count = len([o for o in orders if o.payment_status == status])
                payment_status_breakdown[status.value] = count
            
            return {
                "message": "Admin dashboard data retrieved successfully",
                "data": {
                    "total_users": total_users,
                    "total_sellers": total_sellers,
                    "total_products": total_products,
                    "total_orders": total_orders,
                    "total_revenue": float(total_revenue),
                    "recent_orders": [
                        {
                            "id": str(order.id),
                            "order_number": order.order_number,
                            "status": order.status.value,
                            "payment_status": order.payment_status.value,
                            "total_amount": float(order.total_amount),
                            "created_at": order.created_at.isoformat(),
                            "customer_name": order.user.full_name if order.user else "Unknown"
                        }
                        for order in recent_orders
                    ],
                    "top_sellers": [
                        {
                            "id": str(seller.id),
                            "name": seller.full_name,
                            "total_revenue": float(seller.total_revenue),
                            "total_orders": seller.total_orders
                        }
                        for seller in top_sellers
                    ],
                    "revenue_by_day": revenue_by_day,
                    "user_growth_by_day": user_growth_by_day,
                    "order_status_breakdown": order_status_breakdown,
                    "payment_status_breakdown": payment_status_breakdown
                }
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving admin dashboard data: {str(e)}"
            )

class InvoiceService:
    @staticmethod
    def generate_invoice_number() -> str:
        """Generate a unique invoice number."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"INV-{timestamp}-{random_suffix}"

    @staticmethod
    async def create_invoice_from_order(
        db: AsyncSession,
        order_id: uuid.UUID,
        seller_id: uuid.UUID,
        due_days: int = 30
    ) -> Dict[str, Any]:
        """Create an invoice from an order"""
        try:
            # Get order with items and user
            order_query = select(Order).options(selectinload(Order.user), selectinload(Order.order_items)).where(Order.id == order_id)
            order_result = await db.execute(order_query)
            order = order_result.scalar_one_or_none()
            
            if not order:
                raise NotFoundError("Order", order_id)
            
            # Get order items for this seller's products
            order_items_query = select(OrderItem).join(Product).where(
                and_(
                    OrderItem.order_id == order_id,
                    Product.seller_id == seller_id
                )
            )
            order_items_result = await db.execute(order_items_query)
            order_items = order_items_result.scalars().all()
            
            if not order_items:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No products found for this seller in the order"
                )
            
            # Get seller info
            seller_query = select(User).where(User.id == seller_id)
            seller_result = await db.execute(seller_query)
            seller = seller_result.scalar_one_or_none()
            
            if not seller:
                raise NotFoundError("User", seller_id)
            
            # Calculate totals for seller's items
            subtotal = sum(item.subtotal for item in order_items)
            tax_amount = Decimal('0.00')  # Can be calculated based on seller's tax settings
            total_amount = subtotal + tax_amount
            
            # Create invoice
            invoice = Invoice(
                invoice_number=InvoiceService.generate_invoice_number(),
                order_id=order_id,
                seller_id=seller_id,
                due_date=datetime.utcnow() + timedelta(days=due_days),
                subtotal=subtotal,
                tax_amount=tax_amount,
                total_amount=total_amount,
                customer_name=order.user.full_name,
                customer_email=order.user.email,
                customer_address=order.shipping_address,
                seller_name=seller.full_name,
                seller_email=seller.email,
                seller_address=seller.address,
                seller_phone=seller.phone_number,
                notes=f"Invoice for order {order.order_number}",
                terms="Payment due within 30 days of invoice date."
            )
            
            db.add(invoice)
            await db.commit()
            await db.refresh(invoice)
            
            # Create invoice items
            for item in order_items:
                invoice_item = InvoiceItem(
                    invoice_id=invoice.id,
                    product_name=item.product_name,
                    product_description=f"Product from order {order.order_number}",
                    unit_price=item.product_price,
                    quantity=item.quantity,
                    total_price=item.subtotal
                )
                db.add(invoice_item)
            
            await db.commit()
            await db.refresh(invoice)
            
            return ResponseHandler.create_success("Invoice", invoice.id, invoice)
            
        except (NotFoundError, HTTPException):
            raise
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating invoice: {str(e)}"
            )

    @staticmethod
    async def get_invoices(
        db: AsyncSession,
        seller_id: Optional[uuid.UUID] = None,
        status: Optional[InvoiceStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get invoices with optional filtering"""
        try:
            query = select(Invoice)
            
            if seller_id:
                query = query.where(Invoice.seller_id == seller_id)
            if status:
                query = query.where(Invoice.status == status)
            
            query = query.order_by(desc(Invoice.created_at)).offset(skip).limit(limit)
            result = await db.execute(query)
            invoices = result.scalars().all()
            
            # Get total count
            count_query = select(func.count()).select_from(Invoice)
            if seller_id:
                count_query = count_query.where(Invoice.seller_id == seller_id)
            if status:
                count_query = count_query.where(Invoice.status == status)
            
            total = await db.scalar(count_query)
            
            return {
                "message": "Invoices retrieved successfully",
                "data": invoices,
                "metadata": {
                    "skip": skip,
                    "limit": limit,
                    "total": total
                }
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving invoices: {str(e)}"
            )

    @staticmethod
    async def get_invoice(
        db: AsyncSession,
        invoice_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Get a specific invoice with items"""
        try:
            # Get invoice
            invoice_query = select(Invoice).where(Invoice.id == invoice_id)
            invoice_result = await db.execute(invoice_query)
            invoice = invoice_result.scalar_one_or_none()
            
            if not invoice:
                raise NotFoundError("Invoice", invoice_id)
            
            # Get invoice items
            items_query = select(InvoiceItem).where(InvoiceItem.invoice_id == invoice_id)
            items_result = await db.execute(items_query)
            items = items_result.scalars().all()
            
            return {
                "message": "Invoice retrieved successfully",
                "data": {
                    "invoice": invoice,
                    "items": items
                }
            }
        except NotFoundError:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving invoice: {str(e)}"
            )

    @staticmethod
    async def update_invoice_status(
        db: AsyncSession,
        invoice_id: uuid.UUID,
        status: InvoiceStatus,
        current_user: User
    ) -> Dict[str, Any]:
        """Update invoice status"""
        try:
            # Get invoice
            invoice_query = select(Invoice).where(Invoice.id == invoice_id)
            invoice_result = await db.execute(invoice_query)
            invoice = invoice_result.scalar_one_or_none()
            
            if not invoice:
                raise NotFoundError("Invoice", invoice_id)
            
            # Check permissions (seller can only update their own invoices, admin can update any)
            if current_user.role != UserRole.ADMIN and invoice.seller_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only update your own invoices"
                )
            
            # Update status
            invoice.status = status
            if status == InvoiceStatus.PAID:
                invoice.paid_date = datetime.utcnow()
            
            invoice.updated_at = datetime.utcnow()
            
            db.add(invoice)
            await db.commit()
            await db.refresh(invoice)
            
            return ResponseHandler.update_success("Invoice", invoice_id, invoice)
            
        except (NotFoundError, HTTPException):
            raise
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error updating invoice: {str(e)}"
            )
