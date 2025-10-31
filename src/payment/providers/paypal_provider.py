import paypalrestsdk
from typing import Dict, Any, Optional
from decimal import Decimal
import logging

from .base import BasePaymentProvider, PaymentResult, RefundResult

logger = logging.getLogger(__name__)

class PayPalProvider(BasePaymentProvider):
    """PayPal payment provider implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # Configure PayPal SDK
        paypalrestsdk.configure({
            "mode": config.get('mode', 'sandbox'),  # 'sandbox' or 'live'
            "client_id": config.get('client_id'),
            "client_secret": config.get('client_secret')
        })
        
        self.webhook_id = config.get('webhook_id')
    
    async def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        payment_method: str,
        customer_email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PaymentResult:
        """Create a PayPal payment"""
        try:
            payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {
                    "payment_method": "paypal"
                },
                "redirect_urls": {
                    "return_url": metadata.get('return_url', 'http://localhost:3000/success') if metadata else 'http://localhost:3000/success',
                    "cancel_url": metadata.get('cancel_url', 'http://localhost:3000/cancel') if metadata else 'http://localhost:3000/cancel'
                },
                "transactions": [{
                    "item_list": {
                        "items": [{
                            "name": metadata.get('item_name', 'Order') if metadata else 'Order',
                            "sku": metadata.get('order_id', 'order') if metadata else 'order',
                            "price": str(amount),
                            "currency": currency.upper(),
                            "quantity": 1
                        }]
                    },
                    "amount": {
                        "total": str(amount),
                        "currency": currency.upper()
                    },
                    "description": metadata.get('description', 'Order payment') if metadata else 'Order payment'
                }]
            })
            
            if payment.create():
                # Get approval URL
                approval_url = None
                for link in payment.links:
                    if link.rel == "approval_url":
                        approval_url = link.href
                        break
                
                return PaymentResult(
                    success=True,
                    payment_id=payment.id,
                    requires_action=True,
                    action_url=approval_url,
                    gateway_response=payment.to_dict()
                )
            else:
                error_msg = payment.error.get('message', 'PayPal payment creation failed')
                return PaymentResult(
                    success=False,
                    error_message=error_msg,
                    gateway_response={'error': payment.error}
                )
                
        except Exception as e:
            logger.error(f"PayPal error creating payment: {str(e)}")
            return PaymentResult(
                success=False,
                error_message="PayPal payment creation failed"
            )
    
    async def confirm_payment(
        self,
        payment_intent_id: str,
        payment_method_id: Optional[str] = None
    ) -> PaymentResult:
        """Execute a PayPal payment"""
        try:
            payment = paypalrestsdk.Payment.find(payment_intent_id)
            
            if payment.execute({"payer_id": payment_method_id}):
                # Get transaction ID
                transaction_id = None
                if payment.transactions and payment.transactions[0].related_resources:
                    sale = payment.transactions[0].related_resources[0].sale
                    if sale:
                        transaction_id = sale.id
                
                return PaymentResult(
                    success=True,
                    payment_id=payment.id,
                    transaction_id=transaction_id,
                    gateway_response=payment.to_dict()
                )
            else:
                error_msg = payment.error.get('message', 'PayPal payment execution failed')
                return PaymentResult(
                    success=False,
                    error_message=error_msg,
                    gateway_response={'error': payment.error}
                )
                
        except Exception as e:
            logger.error(f"PayPal error executing payment: {str(e)}")
            return PaymentResult(
                success=False,
                error_message="PayPal payment execution failed"
            )
    
    async def get_payment_status(
        self,
        payment_id: str
    ) -> PaymentResult:
        """Get PayPal payment status"""
        try:
            payment = paypalrestsdk.Payment.find(payment_id)
            
            # Get transaction ID
            transaction_id = None
            if payment.transactions and payment.transactions[0].related_resources:
                sale = payment.transactions[0].related_resources[0].sale
                if sale:
                    transaction_id = sale.id
            
            return PaymentResult(
                success=payment.state == 'approved',
                payment_id=payment.id,
                transaction_id=transaction_id,
                gateway_response=payment.to_dict()
            )
            
        except Exception as e:
            logger.error(f"PayPal error getting payment status: {str(e)}")
            return PaymentResult(
                success=False,
                error_message="Failed to get PayPal payment status"
            )
    
    async def refund_payment(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None
    ) -> RefundResult:
        """Refund a PayPal payment"""
        try:
            # First, get the sale ID from the payment
            payment = paypalrestsdk.Payment.find(payment_id)
            sale_id = None
            
            if payment.transactions and payment.transactions[0].related_resources:
                sale = payment.transactions[0].related_resources[0].sale
                if sale:
                    sale_id = sale.id
            
            if not sale_id:
                return RefundResult(
                    success=False,
                    amount=amount or Decimal('0'),
                    error_message="Sale ID not found for refund"
                )
            
            # Create refund
            refund_data = {
                "amount": {
                    "total": str(amount) if amount else str(payment.transactions[0].amount.total),
                    "currency": payment.transactions[0].amount.currency
                }
            }
            
            if reason:
                refund_data["description"] = reason
            
            refund = paypalrestsdk.Sale.find(sale_id).refund(refund_data)
            
            if refund.success():
                return RefundResult(
                    success=True,
                    refund_id=refund.id,
                    amount=Decimal(refund.amount.total),
                    gateway_response=refund.to_dict()
                )
            else:
                error_msg = refund.error.get('message', 'PayPal refund failed')
                return RefundResult(
                    success=False,
                    amount=amount or Decimal('0'),
                    error_message=error_msg
                )
                
        except Exception as e:
            logger.error(f"PayPal error refunding payment: {str(e)}")
            return RefundResult(
                success=False,
                amount=amount or Decimal('0'),
                error_message="PayPal refund failed"
            )
    
    async def create_payment_method(
        self,
        payment_method_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """PayPal doesn't support saved payment methods in the same way"""
        return {
            'success': False,
            'error': 'PayPal does not support saved payment methods'
        }
    
    def validate_webhook_signature(
        self,
        payload: str,
        signature: str,
        secret: str
    ) -> bool:
        """Validate PayPal webhook signature"""
        # PayPal webhook validation would go here
        # This is a simplified implementation
        return True
    
    def parse_webhook_event(
        self,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse PayPal webhook event"""
        event_type = payload.get('event_type', '')
        resource = payload.get('resource', {})
        
        return {
            'event_type': event_type,
            'payment_id': resource.get('id'),
            'status': resource.get('state'),
            'amount': resource.get('amount', {}).get('total'),
            'currency': resource.get('amount', {}).get('currency'),
            'raw_data': payload
        }
