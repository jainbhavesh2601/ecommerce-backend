from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from decimal import Decimal
from pydantic import BaseModel

class PaymentResult(BaseModel):
    """Base class for payment operation results"""
    success: bool
    payment_id: Optional[str] = None
    transaction_id: Optional[str] = None
    client_secret: Optional[str] = None
    requires_action: bool = False
    action_url: Optional[str] = None
    error_message: Optional[str] = None
    gateway_response: Optional[Dict[str, Any]] = None

class RefundResult(BaseModel):
    """Base class for refund operation results"""
    success: bool
    refund_id: Optional[str] = None
    amount: Decimal
    error_message: Optional[str] = None
    gateway_response: Optional[Dict[str, Any]] = None

class BasePaymentProvider(ABC):
    """Abstract base class for payment providers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.provider_name = self.__class__.__name__.replace('Provider', '').lower()
    
    @abstractmethod
    async def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        payment_method: str,
        customer_email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PaymentResult:
        """Create a payment intent"""
        pass
    
    @abstractmethod
    async def confirm_payment(
        self,
        payment_intent_id: str,
        payment_method_id: Optional[str] = None
    ) -> PaymentResult:
        """Confirm a payment intent"""
        pass
    
    @abstractmethod
    async def get_payment_status(
        self,
        payment_id: str
    ) -> PaymentResult:
        """Get payment status from provider"""
        pass
    
    @abstractmethod
    async def refund_payment(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None
    ) -> RefundResult:
        """Refund a payment"""
        pass
    
    @abstractmethod
    async def create_payment_method(
        self,
        payment_method_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a payment method"""
        pass
    
    def validate_webhook_signature(
        self,
        payload: str,
        signature: str,
        secret: str
    ) -> bool:
        """Validate webhook signature"""
        return True  # Default implementation
    
    def parse_webhook_event(
        self,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse webhook event data"""
        return payload  # Default implementation
