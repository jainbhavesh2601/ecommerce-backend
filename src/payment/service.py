from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime
import uuid
import logging
from fastapi import HTTPException, status

from src.payment.models import Payment, PaymentRefund, PaymentMethodInfo, PaymentMethod, PaymentStatus, PaymentProvider
from src.payment.schema import (
    PaymentCreate, PaymentIntentCreate, PaymentConfirm, PaymentResponse,
    PaymentMethodCreate, PaymentMethodUpdate, PaymentMethodResponse,
    RefundCreate, RefundResponse, PaymentStatusUpdate
)
from src.payment.providers.stripe_provider import StripeProvider
from src.payment.providers.paypal_provider import PayPalProvider
from src.payment.providers.manual_provider import ManualProvider
from src.auth.user.models import User
from src.orders.models import Order, OrderStatus
from src.common.exceptions import NotFoundError, ValidationError
from src.config import Config

logger = logging.getLogger(__name__)

class PaymentService:
    """Main payment service that handles all payment operations"""
    
    def __init__(self):
        self.providers = self._initialize_providers()
    
    def _initialize_providers(self) -> Dict[str, Any]:
        """Initialize payment providers based on configuration"""
        providers = {}
        
        # Check if we're in simulation mode
        if Config.PAYMENT_SIMULATION_MODE:
            # Use mock providers for simulation (no API keys needed)
            from src.payment.providers.mock_stripe_provider import MockStripeProvider
            from src.payment.providers.mock_paypal_provider import MockPayPalProvider
            
            logger.info("Payment simulation mode enabled - using mock providers")
            providers['stripe'] = MockStripeProvider({})
            providers['paypal'] = MockPayPalProvider({})
        else:
            # Use real providers (only if API keys are configured)
            # Stripe provider
            if Config.STRIPE_SECRET_KEY:
                providers['stripe'] = StripeProvider({
                    'secret_key': Config.STRIPE_SECRET_KEY,
                    'webhook_secret': Config.STRIPE_WEBHOOK_SECRET
                })
            
            # PayPal provider
            if Config.PAYPAL_CLIENT_ID:
                providers['paypal'] = PayPalProvider({
                    'client_id': Config.PAYPAL_CLIENT_ID,
                    'client_secret': Config.PAYPAL_CLIENT_SECRET,
                    'mode': Config.PAYPAL_MODE or 'sandbox',
                    'webhook_id': Config.PAYPAL_WEBHOOK_ID
                })
        
        # Manual provider (always available)
        providers['manual'] = ManualProvider({
            'auto_approve': Config.MANUAL_PAYMENT_AUTO_APPROVE or False
        })
        
        return providers
    
    def _get_provider(self, provider_name: str):
        """Get payment provider by name"""
        provider = self.providers.get(provider_name.lower())
        if not provider:
            raise ValidationError(f"Payment provider '{provider_name}' is not configured")
        return provider
    
    def _generate_payment_number(self) -> str:
        """Generate unique payment number"""
        return f"PAY-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    
    def _generate_refund_number(self) -> str:
        """Generate unique refund number"""
        return f"REF-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    
    async def create_payment_intent(
        self,
        db: AsyncSession,
        payment_data: PaymentIntentCreate,
        current_user: User
    ) -> PaymentResponse:
        """Create a payment intent"""
        try:
            # Verify order exists and belongs to user
            order_query = select(Order).where(Order.id == payment_data.order_id)
            order_result = await db.execute(order_query)
            order = order_result.scalar_one_or_none()
            
            if not order:
                raise NotFoundError("Order", payment_data.order_id)
            
            if order.user_id != current_user.id and current_user.role not in ['admin', 'seller']:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only create payments for your own orders"
                )
            
            # Verify payment amount matches order total
            if payment_data.amount != order.total_amount:
                raise ValidationError("Payment amount must match order total")
            
            # Get payment provider
            provider = self._get_provider(payment_data.payment_provider.value)
            
            # Create payment intent with provider
            result = await provider.create_payment_intent(
                amount=payment_data.amount,
                currency=payment_data.currency,
                payment_method=payment_data.payment_method.value,
                customer_email=payment_data.customer_email or current_user.email,
                metadata={
                    'order_id': str(order.id),
                    'user_id': str(current_user.id),
                    'order_number': order.order_number,
                    **payment_data.metadata
                }
            )
            
            if not result.success:
                raise ValidationError(result.error_message or "Payment intent creation failed")
            
            # Create payment record
            payment = Payment(
                user_id=current_user.id,
                order_id=order.id,
                payment_number=self._generate_payment_number(),
                amount=payment_data.amount,
                currency=payment_data.currency,
                payment_method=PaymentMethod(payment_data.payment_method.value),
                payment_provider=PaymentProvider(payment_data.payment_provider.value),
                status=PaymentStatus.PENDING,
                provider_payment_id=result.payment_id,
                payment_intent_id=result.payment_id,
                client_secret=result.client_secret,
                gateway_response=str(result.gateway_response) if result.gateway_response else None
            )
            
            db.add(payment)
            await db.commit()
            await db.refresh(payment)
            
            # Manually convert UUID fields to strings for response
            return PaymentResponse(
                id=str(payment.id),
                payment_number=payment.payment_number,
                order_id=str(payment.order_id),
                amount=payment.amount,
                currency=payment.currency,
                payment_method=payment.payment_method,
                payment_provider=payment.payment_provider,
                status=payment.status,
                provider_payment_id=payment.provider_payment_id,
                payment_intent_id=payment.payment_intent_id,
                client_secret=payment.client_secret,
                failure_reason=payment.failure_reason,
                created_at=payment.created_at,
                updated_at=payment.updated_at,
                processed_at=payment.processed_at,
                completed_at=payment.completed_at
            )
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating payment intent: {str(e)}")
            raise
    
    async def confirm_payment(
        self,
        db: AsyncSession,
        payment_data: PaymentConfirm,
        current_user: User
    ) -> PaymentResponse:
        """Confirm a payment intent"""
        try:
            # Get payment record
            payment_query = select(Payment).where(Payment.payment_intent_id == payment_data.payment_intent_id)
            payment_result = await db.execute(payment_query)
            payment = payment_result.scalar_one_or_none()
            
            if not payment:
                raise NotFoundError("Payment", payment_data.payment_intent_id)
            
            if payment.user_id != current_user.id and current_user.role not in ['admin', 'seller']:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only confirm your own payments"
                )
            
            # Get payment provider
            provider = self._get_provider(payment.payment_provider.value)
            
            # Confirm payment with provider
            result = await provider.confirm_payment(
                payment_intent_id=payment_data.payment_intent_id,
                payment_method_id=payment_data.payment_method_id
            )
            
            # Update payment status
            if result.success:
                payment.status = PaymentStatus.COMPLETED
                payment.provider_transaction_id = result.transaction_id
                payment.completed_at = datetime.utcnow()
            else:
                payment.status = PaymentStatus.FAILED
                payment.failure_reason = result.error_message
            
            payment.processed_at = datetime.utcnow()
            payment.gateway_response = str(result.gateway_response) if result.gateway_response else None
            
            # Update order payment status
            order_query = select(Order).where(Order.id == payment.order_id)
            order_result = await db.execute(order_query)
            order = order_result.scalar_one_or_none()
            
            if order:
                from src.orders.models import PaymentStatus as OrderPaymentStatus
                order.payment_status = OrderPaymentStatus.PAID if result.success else OrderPaymentStatus.FAILED
            
            await db.commit()
            await db.refresh(payment)
            
            # Manually convert UUID fields to strings for response
            return PaymentResponse(
                id=str(payment.id),
                payment_number=payment.payment_number,
                order_id=str(payment.order_id),
                amount=payment.amount,
                currency=payment.currency,
                payment_method=payment.payment_method,
                payment_provider=payment.payment_provider,
                status=payment.status,
                provider_payment_id=payment.provider_payment_id,
                payment_intent_id=payment.payment_intent_id,
                client_secret=payment.client_secret,
                failure_reason=payment.failure_reason,
                created_at=payment.created_at,
                updated_at=payment.updated_at,
                processed_at=payment.processed_at,
                completed_at=payment.completed_at
            )
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error confirming payment: {str(e)}")
            raise
    
    async def get_payment(
        self,
        db: AsyncSession,
        payment_id: str,
        current_user: User
    ) -> PaymentResponse:
        """Get payment by ID"""
        payment_query = select(Payment).where(Payment.id == payment_id)
        payment_result = await db.execute(payment_query)
        payment = payment_result.scalar_one_or_none()
        
        if not payment:
            raise NotFoundError("Payment", payment_id)
        
        if payment.user_id != current_user.id and current_user.role not in ['admin', 'seller']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own payments"
            )
        
        # Manually convert UUID fields to strings for response
        return PaymentResponse(
            id=str(payment.id),
            payment_number=payment.payment_number,
            order_id=str(payment.order_id),
            amount=payment.amount,
            currency=payment.currency,
            payment_method=payment.payment_method,
            payment_provider=payment.payment_provider,
            status=payment.status,
            provider_payment_id=payment.provider_payment_id,
            payment_intent_id=payment.payment_intent_id,
            client_secret=payment.client_secret,
            failure_reason=payment.failure_reason,
            created_at=payment.created_at,
            updated_at=payment.updated_at,
            processed_at=payment.processed_at,
            completed_at=payment.completed_at
        )
    
    async def get_user_payments(
        self,
        db: AsyncSession,
        current_user: User,
        page: int = 1,
        limit: int = 20,
        status: Optional[PaymentStatus] = None
    ) -> Dict[str, Any]:
        """Get user's payments with pagination"""
        query = select(Payment).where(Payment.user_id == current_user.id)
        
        if status:
            query = query.where(Payment.status == status)
        
        # Add pagination
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit).order_by(Payment.created_at.desc())
        
        result = await db.execute(query)
        payments = result.scalars().all()
        
        # Get total count
        count_query = select(Payment).where(Payment.user_id == current_user.id)
        if status:
            count_query = count_query.where(Payment.status == status)
        
        count_result = await db.execute(count_query)
        total = len(count_result.scalars().all())
        
        # Manually convert UUID fields to strings for each payment
        payment_responses = [
            PaymentResponse(
                id=str(payment.id),
                payment_number=payment.payment_number,
                order_id=str(payment.order_id),
                amount=payment.amount,
                currency=payment.currency,
                payment_method=payment.payment_method,
                payment_provider=payment.payment_provider,
                status=payment.status,
                provider_payment_id=payment.provider_payment_id,
                payment_intent_id=payment.payment_intent_id,
                client_secret=payment.client_secret,
                failure_reason=payment.failure_reason,
                created_at=payment.created_at,
                updated_at=payment.updated_at,
                processed_at=payment.processed_at,
                completed_at=payment.completed_at
            )
            for payment in payments
        ]
        
        return {
            "payments": payment_responses,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit
        }
    
    async def create_refund(
        self,
        db: AsyncSession,
        refund_data: RefundCreate,
        current_user: User
    ) -> RefundResponse:
        """Create a payment refund"""
        try:
            # Get payment record
            payment_query = select(Payment).where(Payment.id == refund_data.payment_id)
            payment_result = await db.execute(payment_query)
            payment = payment_result.scalar_one_or_none()
            
            if not payment:
                raise NotFoundError("Payment", refund_data.payment_id)
            
            if payment.user_id != current_user.id and current_user.role not in ['admin']:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only refund your own payments or admin access required"
                )
            
            if payment.status != PaymentStatus.COMPLETED:
                raise ValidationError("Can only refund completed payments")
            
            # Determine refund amount
            refund_amount = refund_data.amount or payment.amount
            
            if refund_amount > payment.amount:
                raise ValidationError("Refund amount cannot exceed payment amount")
            
            # Get payment provider
            provider = self._get_provider(payment.payment_provider.value)
            
            # Process refund with provider
            result = await provider.refund_payment(
                payment_id=payment.provider_payment_id,
                amount=refund_amount,
                reason=refund_data.reason
            )
            
            # Create refund record
            refund = PaymentRefund(
                payment_id=payment.id,
                user_id=current_user.id,
                refund_number=self._generate_refund_number(),
                amount=refund_amount,
                reason=refund_data.reason,
                provider_refund_id=result.refund_id,
                provider_response=str(result.gateway_response) if result.gateway_response else None,
                status=PaymentStatus.COMPLETED if result.success else PaymentStatus.FAILED,
                failure_reason=result.error_message if not result.success else None,
                processed_at=datetime.utcnow() if result.success else None
            )
            
            # Update payment status
            if result.success:
                if refund_amount == payment.amount:
                    payment.status = PaymentStatus.REFUNDED
                else:
                    payment.status = PaymentStatus.PARTIALLY_REFUNDED
                
                # Update order payment status
                order_query = select(Order).where(Order.id == payment.order_id)
                order_result = await db.execute(order_query)
                order = order_result.scalar_one_or_none()
                
                if order:
                    from src.orders.models import PaymentStatus as OrderPaymentStatus
                    order.payment_status = OrderPaymentStatus.REFUNDED
            
            db.add(refund)
            await db.commit()
            await db.refresh(refund)
            
            return RefundResponse.from_orm(refund)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating refund: {str(e)}")
            raise
    
    async def create_payment_method(
        self,
        db: AsyncSession,
        method_data: PaymentMethodCreate,
        current_user: User
    ) -> PaymentMethodResponse:
        """Create a saved payment method"""
        try:
            # Get payment provider
            provider = self._get_provider(method_data.provider.value)
            
            # Prepare payment method data
            provider_data = {}
            if method_data.payment_method.value in ['credit_card', 'debit_card']:
                provider_data['card'] = {
                    'number': method_data.card_number,
                    'exp_month': method_data.card_exp_month,
                    'exp_year': method_data.card_exp_year,
                    'cvc': method_data.card_cvc
                }
            
            # Create payment method with provider
            result = await provider.create_payment_method(provider_data)
            
            if not result['success']:
                raise ValidationError(result.get('error', 'Payment method creation failed'))
            
            # Extract card details for storage
            card_last_four = None
            card_brand = None
            if method_data.card_number:
                card_last_four = method_data.card_number[-4:]
                # Determine card brand (simplified)
                if method_data.card_number.startswith('4'):
                    card_brand = 'visa'
                elif method_data.card_number.startswith('5'):
                    card_brand = 'mastercard'
                elif method_data.card_number.startswith('3'):
                    card_brand = 'amex'
                else:
                    card_brand = 'unknown'
            
            # If setting as default, unset other defaults
            if method_data.is_default:
                existing_defaults_query = select(PaymentMethodInfo).where(
                    PaymentMethodInfo.user_id == current_user.id,
                    PaymentMethodInfo.is_default == True
                )
                existing_defaults_result = await db.execute(existing_defaults_query)
                existing_defaults = existing_defaults_result.scalars().all()
                
                for existing in existing_defaults:
                    existing.is_default = False
            
            # Create payment method record
            payment_method = PaymentMethodInfo(
                user_id=current_user.id,
                payment_method=PaymentMethod(method_data.payment_method.value),
                provider=PaymentProvider(method_data.provider.value),
                card_last_four=card_last_four,
                card_brand=card_brand,
                card_exp_month=method_data.card_exp_month,
                card_exp_year=method_data.card_exp_year,
                provider_method_id=result.get('payment_method_id'),
                is_default=method_data.is_default,
                is_active=True
            )
            
            db.add(payment_method)
            await db.commit()
            await db.refresh(payment_method)
            
            return PaymentMethodResponse.from_orm(payment_method)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating payment method: {str(e)}")
            raise
    
    async def get_user_payment_methods(
        self,
        db: AsyncSession,
        current_user: User
    ) -> List[PaymentMethodResponse]:
        """Get user's saved payment methods"""
        query = select(PaymentMethodInfo).where(
            PaymentMethodInfo.user_id == current_user.id,
            PaymentMethodInfo.is_active == True
        ).order_by(PaymentMethodInfo.is_default.desc(), PaymentMethodInfo.created_at.desc())
        
        result = await db.execute(query)
        methods = result.scalars().all()
        
        return [PaymentMethodResponse.from_orm(method) for method in methods]
    
    async def update_payment_method(
        self,
        db: AsyncSession,
        method_id: str,
        method_update: PaymentMethodUpdate,
        current_user: User
    ) -> PaymentMethodResponse:
        """Update a payment method"""
        try:
            # Get payment method
            method_query = select(PaymentMethodInfo).where(PaymentMethodInfo.id == method_id)
            method_result = await db.execute(method_query)
            method = method_result.scalar_one_or_none()
            
            if not method:
                raise NotFoundError("Payment Method", method_id)
            
            if method.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only update your own payment methods"
                )
            
            # Update fields
            if method_update.is_default is not None:
                if method_update.is_default:
                    # Unset other defaults
                    existing_defaults_query = select(PaymentMethodInfo).where(
                        PaymentMethodInfo.user_id == current_user.id,
                        PaymentMethodInfo.is_default == True,
                        PaymentMethodInfo.id != method_id
                    )
                    existing_defaults_result = await db.execute(existing_defaults_query)
                    existing_defaults = existing_defaults_result.scalars().all()
                    
                    for existing in existing_defaults:
                        existing.is_default = False
                
                method.is_default = method_update.is_default
            
            if method_update.is_active is not None:
                method.is_active = method_update.is_active
            
            method.updated_at = datetime.utcnow()
            
            await db.commit()
            await db.refresh(method)
            
            return PaymentMethodResponse.from_orm(method)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating payment method: {str(e)}")
            raise
    
    async def delete_payment_method(
        self,
        db: AsyncSession,
        method_id: str,
        current_user: User
    ) -> bool:
        """Delete a payment method"""
        try:
            # Get payment method
            method_query = select(PaymentMethodInfo).where(PaymentMethodInfo.id == method_id)
            method_result = await db.execute(method_query)
            method = method_result.scalar_one_or_none()
            
            if not method:
                raise NotFoundError("Payment Method", method_id)
            
            if method.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only delete your own payment methods"
                )
            
            await db.delete(method)
            await db.commit()
            
            return True
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error deleting payment method: {str(e)}")
            raise
    
    async def process_webhook(
        self,
        db: AsyncSession,
        provider_name: str,
        payload: Dict[str, Any],
        signature: Optional[str] = None
    ) -> bool:
        """Process payment provider webhook"""
        try:
            provider = self._get_provider(provider_name)
            
            # Validate webhook signature if provided
            if signature and hasattr(provider, 'validate_webhook_signature'):
                if not provider.validate_webhook_signature(
                    str(payload), signature, provider.webhook_secret
                ):
                    logger.warning(f"Invalid webhook signature from {provider_name}")
                    return False
            
            # Parse webhook event
            event_data = provider.parse_webhook_event(payload)
            
            # Process based on event type
            event_type = event_data.get('event_type', '')
            payment_id = event_data.get('payment_id')
            
            if payment_id:
                # Find payment record
                payment_query = select(Payment).where(Payment.provider_payment_id == payment_id)
                payment_result = await db.execute(payment_query)
                payment = payment_result.scalar_one_or_none()
                
                if payment:
                    # Update payment status based on webhook
                    if 'payment_intent.succeeded' in event_type or 'payment.completed' in event_type:
                        payment.status = PaymentStatus.COMPLETED
                        payment.completed_at = datetime.utcnow()
                    elif 'payment_intent.payment_failed' in event_type or 'payment.failed' in event_type:
                        payment.status = PaymentStatus.FAILED
                        payment.failure_reason = event_data.get('failure_reason', 'Payment failed')
                    
                    payment.gateway_response = str(payload)
                    await db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing webhook from {provider_name}: {str(e)}")
            return False
