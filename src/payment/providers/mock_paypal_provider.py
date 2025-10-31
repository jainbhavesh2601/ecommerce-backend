"""
Mock PayPal Provider for Payment Simulation
Simulates PayPal payment processing without making real API calls
"""
from typing import Dict, Any, Optional
from decimal import Decimal
import uuid
import logging

from .base import BasePaymentProvider, PaymentResult, RefundResult

logger = logging.getLogger(__name__)

class MockPayPalProvider(BasePaymentProvider):
    """Mock PayPal payment provider for simulation/testing"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        logger.info("Initialized MockPayPalProvider (Simulation Mode)")
    
    async def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        payment_method: str,
        customer_email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PaymentResult:
        """Create a simulated PayPal payment"""
        try:
            # Generate mock PayPal payment ID
            payment_id = f"PAYID-MOCK{uuid.uuid4().hex[:16].upper()}"
            
            logger.info(f"Mock PayPal: Created payment for ${amount} {currency}")
            
            return PaymentResult(
                success=True,
                payment_id=payment_id,
                requires_action=False,  # No redirect simulation
                action_url=None,  # In real PayPal, this would be approval URL
                gateway_response={
                    'id': payment_id,
                    'state': 'created',
                    'intent': 'sale',
                    'payer': {
                        'payment_method': 'paypal',
                        'payer_info': {
                            'email': customer_email
                        }
                    },
                    'transactions': [{
                        'amount': {
                            'total': str(amount),
                            'currency': currency.upper()
                        },
                        'description': metadata.get('description', 'Order payment') if metadata else 'Order payment'
                    }],
                    'mock': True
                }
            )
            
        except Exception as e:
            logger.error(f"Mock PayPal error creating payment: {str(e)}")
            return PaymentResult(
                success=False,
                error_message="Mock PayPal payment creation failed",
                gateway_response={'error': str(e), 'mock': True}
            )
    
    async def confirm_payment(
        self,
        payment_intent_id: str,
        payment_method_id: Optional[str] = None
    ) -> PaymentResult:
        """Execute a simulated PayPal payment"""
        try:
            # Generate mock transaction/sale ID
            transaction_id = f"SALE-MOCK{uuid.uuid4().hex[:16].upper()}"
            
            logger.info(f"Mock PayPal: Executed payment {payment_intent_id}")
            
            # Simulate successful execution
            return PaymentResult(
                success=True,
                payment_id=payment_intent_id,
                transaction_id=transaction_id,
                gateway_response={
                    'id': payment_intent_id,
                    'state': 'approved',
                    'transactions': [{
                        'related_resources': [{
                            'sale': {
                                'id': transaction_id,
                                'state': 'completed',
                                'payment_mode': 'INSTANT_TRANSFER'
                            }
                        }]
                    }],
                    'mock': True
                }
            )
            
        except Exception as e:
            logger.error(f"Mock PayPal error executing payment: {str(e)}")
            return PaymentResult(
                success=False,
                error_message="Mock PayPal payment execution failed",
                gateway_response={'error': str(e), 'mock': True}
            )
    
    async def get_payment_status(
        self,
        payment_id: str
    ) -> PaymentResult:
        """Get simulated PayPal payment status"""
        try:
            logger.info(f"Mock PayPal: Getting status for {payment_id}")
            
            transaction_id = f"SALE-MOCK{uuid.uuid4().hex[:16].upper()}"
            
            return PaymentResult(
                success=True,
                payment_id=payment_id,
                transaction_id=transaction_id,
                gateway_response={
                    'id': payment_id,
                    'state': 'approved',
                    'mock': True
                }
            )
            
        except Exception as e:
            logger.error(f"Mock PayPal error getting payment status: {str(e)}")
            return PaymentResult(
                success=False,
                error_message="Failed to get PayPal payment status",
                gateway_response={'error': str(e), 'mock': True}
            )
    
    async def refund_payment(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None
    ) -> RefundResult:
        """Simulate a PayPal refund"""
        try:
            refund_id = f"REFUND-MOCK{uuid.uuid4().hex[:16].upper()}"
            
            logger.info(f"Mock PayPal: Created refund {refund_id} for payment {payment_id}")
            
            return RefundResult(
                success=True,
                refund_id=refund_id,
                amount=amount or Decimal('0'),
                gateway_response={
                    'id': refund_id,
                    'state': 'completed',
                    'amount': {
                        'total': str(amount or Decimal('0')),
                        'currency': 'USD'
                    },
                    'reason': reason,
                    'mock': True
                }
            )
            
        except Exception as e:
            logger.error(f"Mock PayPal error refunding payment: {str(e)}")
            return RefundResult(
                success=False,
                amount=amount or Decimal('0'),
                error_message="Mock PayPal refund failed",
                gateway_response={'error': str(e), 'mock': True}
            )
    
    async def create_payment_method(
        self,
        payment_method_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Mock PayPal doesn't support saved payment methods"""
        logger.info("Mock PayPal: Payment method creation (not supported)")
        return {
            'success': False,
            'error': 'PayPal does not support saved payment methods',
            'mock': True
        }
    
    def validate_webhook_signature(
        self,
        payload: str,
        signature: str,
        secret: str
    ) -> bool:
        """Mock webhook signature validation (always returns True)"""
        logger.info("Mock PayPal: Webhook signature validation (simulated)")
        return True
    
    def parse_webhook_event(
        self,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse simulated PayPal webhook event"""
        event_type = payload.get('event_type', 'PAYMENT.SALE.COMPLETED')
        resource = payload.get('resource', {})
        
        return {
            'event_type': event_type,
            'payment_id': resource.get('id'),
            'status': resource.get('state', 'completed'),
            'amount': resource.get('amount', {}).get('total'),
            'currency': resource.get('amount', {}).get('currency'),
            'raw_data': payload,
            'mock': True
        }

