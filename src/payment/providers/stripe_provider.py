import stripe
from typing import Dict, Any, Optional
from decimal import Decimal
import logging

from .base import BasePaymentProvider, PaymentResult, RefundResult

logger = logging.getLogger(__name__)

class StripeProvider(BasePaymentProvider):
    """Stripe payment provider implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        stripe.api_key = config.get('secret_key')
        self.webhook_secret = config.get('webhook_secret')
    
    async def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        payment_method: str,
        customer_email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PaymentResult:
        """Create a Stripe payment intent"""
        try:
            # Convert Decimal to cents for Stripe
            amount_cents = int(amount * 100)
            
            intent_data = {
                'amount': amount_cents,
                'currency': currency.lower(),
                'payment_method_types': ['card'],
                'metadata': metadata or {}
            }
            
            if customer_email:
                intent_data['receipt_email'] = customer_email
            
            intent = stripe.PaymentIntent.create(**intent_data)
            
            return PaymentResult(
                success=True,
                payment_id=intent.id,
                client_secret=intent.client_secret,
                requires_action=intent.status == 'requires_action',
                gateway_response=intent.to_dict()
            )
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating payment intent: {str(e)}")
            return PaymentResult(
                success=False,
                error_message=str(e),
                gateway_response={'error': str(e)}
            )
        except Exception as e:
            logger.error(f"Unexpected error creating payment intent: {str(e)}")
            return PaymentResult(
                success=False,
                error_message="Payment processing failed"
            )
    
    async def confirm_payment(
        self,
        payment_intent_id: str,
        payment_method_id: Optional[str] = None
    ) -> PaymentResult:
        """Confirm a Stripe payment intent"""
        try:
            intent_data = {'id': payment_intent_id}
            
            if payment_method_id:
                intent_data['payment_method'] = payment_method_id
            
            intent = stripe.PaymentIntent.confirm(**intent_data)
            
            return PaymentResult(
                success=intent.status == 'succeeded',
                payment_id=intent.id,
                transaction_id=intent.charges.data[0].id if intent.charges.data else None,
                requires_action=intent.status == 'requires_action',
                gateway_response=intent.to_dict()
            )
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error confirming payment: {str(e)}")
            return PaymentResult(
                success=False,
                error_message=str(e),
                gateway_response={'error': str(e)}
            )
        except Exception as e:
            logger.error(f"Unexpected error confirming payment: {str(e)}")
            return PaymentResult(
                success=False,
                error_message="Payment confirmation failed"
            )
    
    async def get_payment_status(
        self,
        payment_id: str
    ) -> PaymentResult:
        """Get payment status from Stripe"""
        try:
            intent = stripe.PaymentIntent.retrieve(payment_id)
            
            return PaymentResult(
                success=intent.status == 'succeeded',
                payment_id=intent.id,
                transaction_id=intent.charges.data[0].id if intent.charges.data else None,
                gateway_response=intent.to_dict()
            )
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error getting payment status: {str(e)}")
            return PaymentResult(
                success=False,
                error_message=str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected error getting payment status: {str(e)}")
            return PaymentResult(
                success=False,
                error_message="Failed to get payment status"
            )
    
    async def refund_payment(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None
    ) -> RefundResult:
        """Refund a Stripe payment"""
        try:
            refund_data = {'payment_intent': payment_id}
            
            if amount:
                refund_data['amount'] = int(amount * 100)  # Convert to cents
            
            if reason:
                refund_data['reason'] = 'requested_by_customer'
                refund_data['metadata'] = {'reason': reason}
            
            refund = stripe.Refund.create(**refund_data)
            
            return RefundResult(
                success=refund.status == 'succeeded',
                refund_id=refund.id,
                amount=Decimal(refund.amount) / 100,  # Convert from cents
                gateway_response=refund.to_dict()
            )
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error refunding payment: {str(e)}")
            return RefundResult(
                success=False,
                amount=amount or Decimal('0'),
                error_message=str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected error refunding payment: {str(e)}")
            return RefundResult(
                success=False,
                amount=amount or Decimal('0'),
                error_message="Refund failed"
            )
    
    async def create_payment_method(
        self,
        payment_method_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a Stripe payment method"""
        try:
            if 'card' in payment_method_data:
                # Create payment method for card
                method = stripe.PaymentMethod.create(
                    type='card',
                    card=payment_method_data['card']
                )
                return {
                    'success': True,
                    'payment_method_id': method.id,
                    'data': method.to_dict()
                }
            else:
                return {
                    'success': False,
                    'error': 'Unsupported payment method type'
                }
                
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating payment method: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error creating payment method: {str(e)}")
            return {
                'success': False,
                'error': 'Payment method creation failed'
            }
    
    def validate_webhook_signature(
        self,
        payload: str,
        signature: str,
        secret: str
    ) -> bool:
        """Validate Stripe webhook signature"""
        try:
            stripe.Webhook.construct_event(
                payload, signature, secret
            )
            return True
        except ValueError:
            return False
        except stripe.error.SignatureVerificationError:
            return False
    
    def parse_webhook_event(
        self,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse Stripe webhook event"""
        event_type = payload.get('type', '')
        data = payload.get('data', {}).get('object', {})
        
        return {
            'event_type': event_type,
            'payment_id': data.get('id'),
            'status': data.get('status'),
            'amount': data.get('amount'),
            'currency': data.get('currency'),
            'metadata': data.get('metadata', {}),
            'raw_data': payload
        }
