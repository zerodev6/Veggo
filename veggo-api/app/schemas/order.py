from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.models.order import OrderItemSnapshot, OrderStatus, PaymentMethod, PaymentStatus, TrackingEvent


class CheckoutRequest(BaseModel):
    address_id: str
    payment_method: PaymentMethod = PaymentMethod.COD
    delivery_note: Optional[str] = ""
    coupon_code: Optional[str] = None
    payment_reference: Optional[str] = None


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    note: Optional[str] = None


class PaymentStatusUpdate(BaseModel):
    payment_status: PaymentStatus
    payment_reference: Optional[str] = None
    note: Optional[str] = None


class AssignAgentRequest(BaseModel):
    agent_id: str


class CancelOrderRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=200)


class BankProofUpload(BaseModel):
    payment_reference: str = Field(..., min_length=3)
    payment_proof: str = Field(..., min_length=5, description="Image URL of the bank deposit slip / transfer receipt")


class OrderResponse(BaseModel):
    id: str
    order_number: str
    user_id: str
    customer_name: str
    customer_phone: str
    items: List[OrderItemSnapshot] = []
    subtotal: float
    delivery_fee: float
    discount: float = 0.0
    coupon_code: Optional[str] = None
    total: float
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    payment_reference: Optional[str] = None
    payment_proof: Optional[str] = None
    order_status: OrderStatus
    address: Dict[str, Any]
    delivery_agent_id: Optional[str] = None
    delivery_agent_name: Optional[str] = None
    delivery_note: Optional[str] = ""
    cancellation_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class OrderTrackingResponse(BaseModel):
    order_id: str
    order_number: str
    order_status: OrderStatus
    estimated_delivery: Optional[str] = None
    timeline: List[TrackingEvent]
