from typing import Dict, Any, Optional
from decimal import Decimal
import logging
import uuid

from .base import BasePaymentProvider, PaymentResult, RefundResult

logger = logging.getLogger(__name__)

class ManualProvider(BasePaymentProvider):
    """Manual payment provider for cash on delivery, bank transfers, etc."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.auto_approve = config.get('auto_approve', False)
    
    async def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        payment_method: str,
        customer_email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PaymentResult:
        """Create a manual payment intent"""
        try:
            # Generate a unique payment ID
            payment_id = f"manual_{uuid.uuid4().hex[:16]}"
            
            # For manual payments, we simulate the process
            status = 'succeeded' if self.auto_approve else 'pending'
            
            return PaymentResult(
                success=True,
                payment_id=payment_id,
                transaction_id=f"txn_{uuid.uuid4().hex[:16]}",
                requires_action=not self.auto_approve,
                gateway_response={
                    'id': payment_id,
                    'status': status,
                    'amount': float(amount),
                    'currency': currency,
                    'payment_method': payment_method,
                    'metadata': metadata or {}
                }
            )
            
        except Exception as e:
            logger.error(f"Error creating manual payment intent: {str(e)}")
            return PaymentResult(
                success=False,
                error_message="Manual payment creation failed"
            )
    
    async def confirm_payment(
        self,
        payment_intent_id: str,
        payment_method_id: Optional[str] = None
    ) -> PaymentResult:
        """Confirm a manual payment"""
        try:
            # For manual payments, confirmation is handled by admin
            return PaymentResult(
                success=True,
                payment_id=payment_intent_id,
                transaction_id=f"txn_{uuid.uuid4().hex[:16]}",
                gateway_response={
                    'id': payment_intent_id,
                    'status': 'succeeded',
                    'confirmed_at': 'manual_confirmation'
                }
            )
            
        except Exception as e:
            logger.error(f"Error confirming manual payment: {str(e)}")
            return PaymentResult(
                success=False,
                error_message="Manual payment confirmation failed"
            )
    
    async def get_payment_status(
        self,
        payment_id: str
    ) -> PaymentResult:
        """Get manual payment status"""
        try:
            # For manual payments, status is managed internally
            return PaymentResult(
                success=True,
                payment_id=payment_id,
                gateway_response={
                    'id': payment_id,
                    'status': 'pending'  # Default status for manual payments
                }
            )
            
        except Exception as e:
            logger.error(f"Error getting manual payment status: {str(e)}")
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
        """Refund a manual payment"""
        try:
            refund_id = f"refund_{uuid.uuid4().hex[:16]}"
            
            return RefundResult(
                success=True,
                refund_id=refund_id,
                amount=amount or Decimal('0'),
                gateway_response={
                    'id': refund_id,
                    'status': 'succeeded',
                    'amount': float(amount) if amount else 0,
                    'reason': reason
                }
            )
            
        except Exception as e:
            logger.error(f"Error refunding manual payment: {str(e)}")
            return RefundResult(
                success=False,
                amount=amount or Decimal('0'),
                error_message="Manual refund failed"
            )
    
    async def create_payment_method(
        self,
        payment_method_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a manual payment method"""
        try:
            method_id = f"method_{uuid.uuid4().hex[:16]}"
            
            return {
                'success': True,
                'payment_method_id': method_id,
                'data': {
                    'id': method_id,
                    'type': 'manual',
                    'payment_method': payment_method_data.get('payment_method', 'manual'),
                    'created': 'manual_creation'
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating manual payment method: {str(e)}")
            return {
                'success': False,
                'error': 'Manual payment method creation failed'
            }
    
    def validate_webhook_signature(
        self,
        payload: str,
        signature: str,
        secret: str
    ) -> bool:
        """Manual payments don't use webhooks"""
        return False
    
    def parse_webhook_event(
        self,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Manual payments don't use webhooks"""
        return {}
