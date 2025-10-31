"""
Mock Stripe Provider for Payment Simulation
Simulates Stripe payment processing without making real API calls
"""
from typing import Dict, Any, Optional
from decimal import Decimal
import uuid
import logging

from .base import BasePaymentProvider, PaymentResult, RefundResult

logger = logging.getLogger(__name__)

class MockStripeProvider(BasePaymentProvider):
    """Mock Stripe payment provider for simulation/testing"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        logger.info("Initialized MockStripeProvider (Simulation Mode)")
    
    async def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        payment_method: str,
        customer_email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PaymentResult:
        """Create a simulated Stripe payment intent"""
        try:
            # Generate mock IDs
            payment_id = f"pi_mock_{uuid.uuid4().hex[:24]}"
            client_secret = f"pi_mock_{uuid.uuid4().hex[:24]}_secret_{uuid.uuid4().hex[:10]}"
            
            logger.info(f"Mock Stripe: Created payment intent for ${amount} {currency}")
            
            return PaymentResult(
                success=True,
                payment_id=payment_id,
                client_secret=client_secret,
                requires_action=False,  # No 3D Secure simulation
                gateway_response={
                    'id': payment_id,
                    'amount': int(amount * 100),  # Convert to cents
                    'currency': currency.lower(),
                    'status': 'requires_confirmation',
                    'client_secret': client_secret,
                    'metadata': metadata or {},
                    'mock': True
                }
            )
            
        except Exception as e:
            logger.error(f"Mock Stripe error creating payment intent: {str(e)}")
            return PaymentResult(
                success=False,
                error_message="Mock payment intent creation failed",
                gateway_response={'error': str(e), 'mock': True}
            )
    
    async def confirm_payment(
        self,
        payment_intent_id: str,
        payment_method_id: Optional[str] = None
    ) -> PaymentResult:
        """Confirm a simulated Stripe payment"""
        try:
            # Generate mock transaction ID
            transaction_id = f"ch_mock_{uuid.uuid4().hex[:24]}"
            
            logger.info(f"Mock Stripe: Confirmed payment {payment_intent_id}")
            
            # Simulate successful payment
            return PaymentResult(
                success=True,
                payment_id=payment_intent_id,
                transaction_id=transaction_id,
                requires_action=False,
                gateway_response={
                    'id': payment_intent_id,
                    'status': 'succeeded',
                    'charges': {
                        'data': [{
                            'id': transaction_id,
                            'status': 'succeeded',
                            'paid': True
                        }]
                    },
                    'mock': True
                }
            )
            
        except Exception as e:
            logger.error(f"Mock Stripe error confirming payment: {str(e)}")
            return PaymentResult(
                success=False,
                error_message="Mock payment confirmation failed",
                gateway_response={'error': str(e), 'mock': True}
            )
    
    async def get_payment_status(
        self,
        payment_id: str
    ) -> PaymentResult:
        """Get simulated payment status"""
        try:
            logger.info(f"Mock Stripe: Getting status for {payment_id}")
            
            return PaymentResult(
                success=True,
                payment_id=payment_id,
                transaction_id=f"ch_mock_{uuid.uuid4().hex[:24]}",
                gateway_response={
                    'id': payment_id,
                    'status': 'succeeded',
                    'mock': True
                }
            )
            
        except Exception as e:
            logger.error(f"Mock Stripe error getting payment status: {str(e)}")
            return PaymentResult(
                success=False,
                error_message="Failed to get payment status",
                gateway_response={'error': str(e), 'mock': True}
            )
    
    async def refund_payment(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None
    ) -> RefundResult:
        """Simulate a Stripe refund"""
        try:
            refund_id = f"re_mock_{uuid.uuid4().hex[:24]}"
            
            logger.info(f"Mock Stripe: Created refund {refund_id} for payment {payment_id}")
            
            return RefundResult(
                success=True,
                refund_id=refund_id,
                amount=amount or Decimal('0'),
                gateway_response={
                    'id': refund_id,
                    'amount': int((amount or Decimal('0')) * 100),
                    'status': 'succeeded',
                    'reason': reason,
                    'mock': True
                }
            )
            
        except Exception as e:
            logger.error(f"Mock Stripe error refunding payment: {str(e)}")
            return RefundResult(
                success=False,
                amount=amount or Decimal('0'),
                error_message="Mock refund failed",
                gateway_response={'error': str(e), 'mock': True}
            )
    
    async def create_payment_method(
        self,
        payment_method_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Simulate creating a Stripe payment method"""
        try:
            method_id = f"pm_mock_{uuid.uuid4().hex[:24]}"
            
            logger.info(f"Mock Stripe: Created payment method {method_id}")
            
            return {
                'success': True,
                'payment_method_id': method_id,
                'data': {
                    'id': method_id,
                    'type': 'card',
                    'card': payment_method_data.get('card', {}),
                    'mock': True
                }
            }
                
        except Exception as e:
            logger.error(f"Mock Stripe error creating payment method: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'mock': True
            }
    
    def validate_webhook_signature(
        self,
        payload: str,
        signature: str,
        secret: str
    ) -> bool:
        """Mock webhook signature validation (always returns True)"""
        logger.info("Mock Stripe: Webhook signature validation (simulated)")
        return True
    
    def parse_webhook_event(
        self,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse simulated webhook event"""
        event_type = payload.get('type', 'payment_intent.succeeded')
        data = payload.get('data', {}).get('object', {})
        
        return {
            'event_type': event_type,
            'payment_id': data.get('id'),
            'status': data.get('status', 'succeeded'),
            'amount': data.get('amount'),
            'currency': data.get('currency'),
            'metadata': data.get('metadata', {}),
            'raw_data': payload,
            'mock': True
        }

