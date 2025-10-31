from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
from src.common.email_service import EmailService
from src.orders.models import Order, OrderItem, OrderStatus, PaymentStatus
from src.auth.user.models import User
from src.product.models import Product
import logging

logger = logging.getLogger(__name__)

class OrderNotificationService:
    """Service for sending order-related email notifications"""
    
    @staticmethod
    async def send_order_confirmation_email(
        order: Order,
        order_items: List[OrderItem],
        customer: User
    ) -> bool:
        """
        Send order confirmation email to customer
        
        Args:
            order: The order object
            order_items: List of order items
            customer: Customer user object
            
        Returns:
            bool: True if email was sent successfully
        """
        # Check if customer has notifications enabled
        if not customer.email_notifications_enabled or not customer.order_notifications_enabled:
            logger.info(f"Order confirmation email skipped for user {customer.id} - notifications disabled")
            return True
        try:
            subject = f"Order Confirmation - {order.order_number}"
            
            # Create order items list for email
            items_html = ""
            items_text = ""
            for item in order_items:
                items_html += f"""
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">{item.product_name}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: center;">{item.quantity}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: right;">Rs. {item.product_price:.2f}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: right;">Rs. {item.subtotal:.2f}</td>
                </tr>
                """
                items_text += f"{item.product_name} - Qty: {item.quantity} - Rs. {item.subtotal:.2f}\n"
            
            # Plain text version
            body = f"""
Dear {customer.full_name},

Thank you for your order! We have received your order and are processing it.

Order Details:
Order Number: {order.order_number}
Order Date: {order.created_at.strftime('%B %d, %Y at %I:%M %p')}
Status: {order.status.value.title()}
Payment Status: {order.payment_status.value.title()}

Items Ordered:
{items_text}

Order Summary:
Subtotal: Rs. {order.subtotal:.2f}
Tax: Rs. {order.tax_amount:.2f}
Shipping: Rs. {order.shipping_cost:.2f}
Total: Rs. {order.total_amount:.2f}

Shipping Address:
{order.shipping_address}

We will send you another email once your order has been shipped.

Thank you for shopping with Artisans Alley!

Best regards,
Artisans Alley Team
            """.strip()
            
            # HTML version
            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background-color: #4CAF50;
            color: white;
            padding: 20px;
            text-align: center;
            border-radius: 8px 8px 0 0;
        }}
        .content {{
            background-color: #f9f9f9;
            padding: 20px;
            border-radius: 0 0 8px 8px;
        }}
        .order-info {{
            background-color: white;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
        }}
        .items-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            background-color: white;
            border-radius: 5px;
            overflow: hidden;
        }}
        .items-table th {{
            background-color: #4CAF50;
            color: white;
            padding: 12px 8px;
            text-align: left;
        }}
        .items-table td {{
            padding: 8px;
            border-bottom: 1px solid #eee;
        }}
        .total-section {{
            background-color: #e8f5e8;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
        }}
        .footer {{
            text-align: center;
            margin-top: 20px;
            font-size: 12px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Order Confirmation</h1>
        <p>Thank you for your order!</p>
    </div>
    
    <div class="content">
        <p>Dear {customer.full_name},</p>
        
        <p>We have received your order and are processing it. Here are your order details:</p>
        
        <div class="order-info">
            <h3>Order Information</h3>
            <p><strong>Order Number:</strong> {order.order_number}</p>
            <p><strong>Order Date:</strong> {order.created_at.strftime('%B %d, %Y at %I:%M %p')}</p>
            <p><strong>Status:</strong> {order.status.value.title()}</p>
            <p><strong>Payment Status:</strong> {order.payment_status.value.title()}</p>
        </div>
        
        <h3>Items Ordered</h3>
        <table class="items-table">
            <thead>
                <tr>
                    <th>Product</th>
                    <th style="text-align: center;">Qty</th>
                    <th style="text-align: right;">Price</th>
                    <th style="text-align: right;">Total</th>
                </tr>
            </thead>
            <tbody>
                {items_html}
            </tbody>
        </table>
        
        <div class="total-section">
            <h3>Order Summary</h3>
            <p><strong>Subtotal:</strong> Rs. {order.subtotal:.2f}</p>
            <p><strong>Tax:</strong> Rs. {order.tax_amount:.2f}</p>
            <p><strong>Shipping:</strong> Rs. {order.shipping_cost:.2f}</p>
            <p style="font-size: 18px; font-weight: bold; color: #4CAF50;"><strong>Total: Rs. {order.total_amount:.2f}</strong></p>
        </div>
        
        <div class="order-info">
            <h3>Shipping Address</h3>
            <p>{order.shipping_address}</p>
        </div>
        
        <p>We will send you another email once your order has been shipped.</p>
        
        <p>Thank you for shopping with Artisans Alley!</p>
    </div>
    
    <div class="footer">
        <p>Best regards,<br>Artisans Alley Team</p>
        <p>This is an automated email. Please do not reply to this message.</p>
    </div>
</body>
</html>
            """.strip()
            
            return EmailService.send_email(customer.email, subject, body, html_body)
            
        except Exception as e:
            logger.error(f"Failed to send order confirmation email: {str(e)}")
            return False

    @staticmethod
    async def send_order_status_update_email(
        order: Order,
        customer: User,
        old_status: OrderStatus,
        new_status: OrderStatus
    ) -> bool:
        """
        Send order status update email to customer
        
        Args:
            order: The order object
            customer: Customer user object
            old_status: Previous order status
            new_status: New order status
            
        Returns:
            bool: True if email was sent successfully
        """
        # Check if customer has notifications enabled
        if not customer.email_notifications_enabled or not customer.order_notifications_enabled:
            logger.info(f"Order status update email skipped for user {customer.id} - notifications disabled")
            return True
        try:
            subject = f"Order Update - {order.order_number}"
            
            # Status-specific messages
            status_messages = {
                OrderStatus.CONFIRMED: "Your order has been confirmed and is being prepared.",
                OrderStatus.PROCESSING: "Your order is being processed and will be shipped soon.",
                OrderStatus.SHIPPED: "Great news! Your order has been shipped and is on its way to you.",
                OrderStatus.DELIVERED: "Your order has been delivered! We hope you love your items.",
                OrderStatus.CANCELLED: "Your order has been cancelled as requested.",
                OrderStatus.REFUNDED: "Your order has been refunded. The refund will be processed within 3-5 business days."
            }
            
            message = status_messages.get(new_status, f"Your order status has been updated to {new_status.value}.")
            
            # Plain text version
            body = f"""
Dear {customer.full_name},

Your order status has been updated.

Order Details:
Order Number: {order.order_number}
Previous Status: {old_status.value.title()}
New Status: {new_status.value.title()}
Updated: {datetime.utcnow().strftime('%B %d, %Y at %I:%M %p')}

{message}

Order Total: Rs. {order.total_amount:.2f}

You can track your order status by logging into your account.

Thank you for shopping with Artisans Alley!

Best regards,
Artisans Alley Team
            """.strip()
            
            # HTML version
            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background-color: #2196F3;
            color: white;
            padding: 20px;
            text-align: center;
            border-radius: 8px 8px 0 0;
        }}
        .content {{
            background-color: #f9f9f9;
            padding: 20px;
            border-radius: 0 0 8px 8px;
        }}
        .status-update {{
            background-color: white;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
            border-left: 4px solid #2196F3;
        }}
        .order-info {{
            background-color: #e3f2fd;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
        }}
        .footer {{
            text-align: center;
            margin-top: 20px;
            font-size: 12px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Order Status Update</h1>
        <p>Your order has been updated</p>
    </div>
    
    <div class="content">
        <p>Dear {customer.full_name},</p>
        
        <div class="status-update">
            <h3>Status Change</h3>
            <p><strong>Previous Status:</strong> {old_status.value.title()}</p>
            <p><strong>New Status:</strong> {new_status.value.title()}</p>
            <p><strong>Updated:</strong> {datetime.utcnow().strftime('%B %d, %Y at %I:%M %p')}</p>
        </div>
        
        <div class="order-info">
            <h3>Order Information</h3>
            <p><strong>Order Number:</strong> {order.order_number}</p>
            <p><strong>Order Total:</strong> Rs. {order.total_amount:.2f}</p>
        </div>
        
        <p>{message}</p>
        
        <p>You can track your order status by logging into your account.</p>
        
        <p>Thank you for shopping with Artisans Alley!</p>
    </div>
    
    <div class="footer">
        <p>Best regards,<br>Artisans Alley Team</p>
        <p>This is an automated email. Please do not reply to this message.</p>
    </div>
</body>
</html>
            """.strip()
            
            return EmailService.send_email(customer.email, subject, body, html_body)
            
        except Exception as e:
            logger.error(f"Failed to send order status update email: {str(e)}")
            return False

    @staticmethod
    async def send_new_order_notification_to_sellers(
        order: Order,
        order_items: List[OrderItem],
        customer: User,
        sellers: List[User]
    ) -> bool:
        """
        Send new order notification to sellers
        
        Args:
            order: The order object
            order_items: List of order items
            customer: Customer user object
            sellers: List of seller users
            
        Returns:
            bool: True if all emails were sent successfully
        """
        try:
            # Group items by seller
            seller_items = {}
            for item in order_items:
                # Get product to find seller
                # This would need to be passed in or queried
                # For now, we'll assume all items are from the same seller
                seller_id = "seller_id"  # This should be the actual seller ID
                if seller_id not in seller_items:
                    seller_items[seller_id] = []
                seller_items[seller_id].append(item)
            
            # Send email to each seller
            success = True
            for seller in sellers:
                seller_success = await OrderNotificationService._send_seller_order_notification(
                    order, order_items, customer, seller
                )
                if not seller_success:
                    success = False
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send seller notifications: {str(e)}")
            return False

    @staticmethod
    async def _send_seller_order_notification(
        order: Order,
        order_items: List[OrderItem],
        customer: User,
        seller: User
    ) -> bool:
        """
        Send new order notification to a specific seller
        
        Args:
            order: The order object
            order_items: List of order items
            customer: Customer user object
            seller: Seller user object
            
        Returns:
            bool: True if email was sent successfully
        """
        try:
            subject = f"New Order Received - {order.order_number}"
            
            # Filter items for this seller (this would need proper implementation)
            seller_items = order_items  # For now, assume all items
            
            # Create items list for email
            items_html = ""
            items_text = ""
            for item in seller_items:
                items_html += f"""
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">{item.product_name}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: center;">{item.quantity}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: right;">Rs. {item.subtotal:.2f}</td>
                </tr>
                """
                items_text += f"{item.product_name} - Qty: {item.quantity} - Rs. {item.subtotal:.2f}\n"
            
            # Plain text version
            body = f"""
Dear {seller.full_name},

You have received a new order!

Order Details:
Order Number: {order.order_number}
Customer: {customer.full_name}
Customer Email: {customer.email}
Order Date: {order.created_at.strftime('%B %d, %Y at %I:%M %p')}
Payment Status: {order.payment_status.value.title()}

Items Ordered:
{items_text}

Customer Shipping Address:
{order.shipping_address}

Please process this order as soon as possible. You can update the order status in your seller dashboard.

Thank you for being part of Artisans Alley!

Best regards,
Artisans Alley Team
            """.strip()
            
            # HTML version
            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background-color: #FF9800;
            color: white;
            padding: 20px;
            text-align: center;
            border-radius: 8px 8px 0 0;
        }}
        .content {{
            background-color: #f9f9f9;
            padding: 20px;
            border-radius: 0 0 8px 8px;
        }}
        .order-info {{
            background-color: white;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
        }}
        .items-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            background-color: white;
            border-radius: 5px;
            overflow: hidden;
        }}
        .items-table th {{
            background-color: #FF9800;
            color: white;
            padding: 12px 8px;
            text-align: left;
        }}
        .items-table td {{
            padding: 8px;
            border-bottom: 1px solid #eee;
        }}
        .customer-info {{
            background-color: #fff3e0;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
        }}
        .footer {{
            text-align: center;
            margin-top: 20px;
            font-size: 12px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>New Order Received!</h1>
        <p>You have a new order to process</p>
    </div>
    
    <div class="content">
        <p>Dear {seller.full_name},</p>
        
        <p>You have received a new order that requires your attention.</p>
        
        <div class="order-info">
            <h3>Order Information</h3>
            <p><strong>Order Number:</strong> {order.order_number}</p>
            <p><strong>Order Date:</strong> {order.created_at.strftime('%B %d, %Y at %I:%M %p')}</p>
            <p><strong>Payment Status:</strong> {order.payment_status.value.title()}</p>
        </div>
        
        <div class="customer-info">
            <h3>Customer Information</h3>
            <p><strong>Name:</strong> {customer.full_name}</p>
            <p><strong>Email:</strong> {customer.email}</p>
        </div>
        
        <h3>Items Ordered</h3>
        <table class="items-table">
            <thead>
                <tr>
                    <th>Product</th>
                    <th style="text-align: center;">Qty</th>
                    <th style="text-align: right;">Total</th>
                </tr>
            </thead>
            <tbody>
                {items_html}
            </tbody>
        </table>
        
        <div class="order-info">
            <h3>Shipping Address</h3>
            <p>{order.shipping_address}</p>
        </div>
        
        <p><strong>Action Required:</strong> Please process this order as soon as possible. You can update the order status in your seller dashboard.</p>
        
        <p>Thank you for being part of Artisans Alley!</p>
    </div>
    
    <div class="footer">
        <p>Best regards,<br>Artisans Alley Team</p>
        <p>This is an automated email. Please do not reply to this message.</p>
    </div>
</body>
</html>
            """.strip()
            
            return EmailService.send_email(seller.email, subject, body, html_body)
            
        except Exception as e:
            logger.error(f"Failed to send seller order notification: {str(e)}")
            return False

    @staticmethod
    async def send_payment_confirmation_email(
        order: Order,
        customer: User
    ) -> bool:
        """
        Send payment confirmation email to customer
        
        Args:
            order: The order object
            customer: Customer user object
            
        Returns:
            bool: True if email was sent successfully
        """
        # Check if customer has notifications enabled
        if not customer.email_notifications_enabled or not customer.order_notifications_enabled:
            logger.info(f"Payment confirmation email skipped for user {customer.id} - notifications disabled")
            return True
        try:
            subject = f"Payment Confirmed - {order.order_number}"
            
            # Plain text version
            body = f"""
Dear {customer.full_name},

Great news! Your payment has been confirmed.

Order Details:
Order Number: {order.order_number}
Payment Amount: Rs. {order.total_amount:.2f}
Payment Date: {datetime.utcnow().strftime('%B %d, %Y at %I:%M %p')}
Payment Status: {order.payment_status.value.title()}

Your order is now being processed and you will receive another email once it has been shipped.

Thank you for your purchase!

Best regards,
Artisans Alley Team
            """.strip()
            
            # HTML version
            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background-color: #4CAF50;
            color: white;
            padding: 20px;
            text-align: center;
            border-radius: 8px 8px 0 0;
        }}
        .content {{
            background-color: #f9f9f9;
            padding: 20px;
            border-radius: 0 0 8px 8px;
        }}
        .payment-info {{
            background-color: #e8f5e8;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
            text-align: center;
        }}
        .order-info {{
            background-color: white;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
        }}
        .footer {{
            text-align: center;
            margin-top: 20px;
            font-size: 12px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Payment Confirmed!</h1>
        <p>Your payment has been processed successfully</p>
    </div>
    
    <div class="content">
        <p>Dear {customer.full_name},</p>
        
        <div class="payment-info">
            <h2>✅ Payment Confirmed</h2>
            <p style="font-size: 24px; font-weight: bold; color: #4CAF50;">Rs. {order.total_amount:.2f}</p>
        </div>
        
        <div class="order-info">
            <h3>Order Information</h3>
            <p><strong>Order Number:</strong> {order.order_number}</p>
            <p><strong>Payment Date:</strong> {datetime.utcnow().strftime('%B %d, %Y at %I:%M %p')}</p>
            <p><strong>Payment Status:</strong> {order.payment_status.value.title()}</p>
        </div>
        
        <p>Your order is now being processed and you will receive another email once it has been shipped.</p>
        
        <p>Thank you for your purchase!</p>
    </div>
    
    <div class="footer">
        <p>Best regards,<br>Artisans Alley Team</p>
        <p>This is an automated email. Please do not reply to this message.</p>
    </div>
</body>
</html>
            """.strip()
            
            return EmailService.send_email(customer.email, subject, body, html_body)
            
        except Exception as e:
            logger.error(f"Failed to send payment confirmation email: {str(e)}")
            return False

    @staticmethod
    async def send_order_shipped_email(
        order: Order,
        customer: User,
        tracking_number: Optional[str] = None
    ) -> bool:
        """
        Send order shipped notification to customer
        
        Args:
            order: The order object
            customer: Customer user object
            tracking_number: Optional tracking number
            
        Returns:
            bool: True if email was sent successfully
        """
        # Check if customer has notifications enabled
        if not customer.email_notifications_enabled or not customer.order_notifications_enabled:
            logger.info(f"Order shipped email skipped for user {customer.id} - notifications disabled")
            return True
        try:
            subject = f"Your Order Has Shipped! - {order.order_number}"
            
            tracking_info = ""
            if tracking_number:
                tracking_info = f"""
Tracking Information:
Tracking Number: {tracking_number}
You can track your package using the tracking number above.
                """
            
            # Plain text version
            body = f"""
Dear {customer.full_name},

Great news! Your order has been shipped and is on its way to you.

Order Details:
Order Number: {order.order_number}
Shipped Date: {datetime.utcnow().strftime('%B %d, %Y at %I:%M %p')}

{tracking_info}

Your order should arrive within 3-7 business days. Please ensure someone is available to receive the package.

Thank you for shopping with Artisans Alley!

Best regards,
Artisans Alley Team
            """.strip()
            
            # HTML version
            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background-color: #2196F3;
            color: white;
            padding: 20px;
            text-align: center;
            border-radius: 8px 8px 0 0;
        }}
        .content {{
            background-color: #f9f9f9;
            padding: 20px;
            border-radius: 0 0 8px 8px;
        }}
        .shipped-info {{
            background-color: #e3f2fd;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
            text-align: center;
        }}
        .tracking-info {{
            background-color: white;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
            border: 2px solid #2196F3;
        }}
        .footer {{
            text-align: center;
            margin-top: 20px;
            font-size: 12px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚚 Your Order Has Shipped!</h1>
        <p>Your package is on its way</p>
    </div>
    
    <div class="content">
        <p>Dear {customer.full_name},</p>
        
        <div class="shipped-info">
            <h2>📦 Order Shipped</h2>
            <p>Your order has been shipped and is on its way to you!</p>
        </div>
        
        <div class="tracking-info">
            <h3>Order Information</h3>
            <p><strong>Order Number:</strong> {order.order_number}</p>
            <p><strong>Shipped Date:</strong> {datetime.utcnow().strftime('%B %d, %Y at %I:%M %p')}</p>
            {f'<p><strong>Tracking Number:</strong> {tracking_number}</p>' if tracking_number else ''}
        </div>
        
        <p>Your order should arrive within 3-7 business days. Please ensure someone is available to receive the package.</p>
        
        <p>Thank you for shopping with Artisans Alley!</p>
    </div>
    
    <div class="footer">
        <p>Best regards,<br>Artisans Alley Team</p>
        <p>This is an automated email. Please do not reply to this message.</p>
    </div>
</body>
</html>
            """.strip()
            
            return EmailService.send_email(customer.email, subject, body, html_body)
            
        except Exception as e:
            logger.error(f"Failed to send order shipped email: {str(e)}")
            return False
