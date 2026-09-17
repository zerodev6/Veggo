from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class OrderStatus(str, Enum):
    PLACED = "PLACED"
    CONFIRMED = "CONFIRMED"
    PREPARING = "PREPARING"
    READY_FOR_PICKUP = "READY_FOR_PICKUP"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class PaymentMethod(str, Enum):
    COD = "COD"
    BANK_TRANSFER = "BANK_TRANSFER"


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    REFUNDED = "REFUNDED"


class OrderItemSnapshot(BaseModel):
    product_id: str
    product_name: str
    product_image: Optional[str] = ""
    unit_type: str = "WEIGHT"
    price_at_purchase: float
    quantity: float
    unit: str  # g, kg, pcs, pack, bundle
    subtotal: float


class TrackingEvent(BaseModel):
    status: OrderStatus
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    updated_by: Optional[str] = "SYSTEM"


class OrderInDB(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
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
    payment_method: PaymentMethod = PaymentMethod.COD
    payment_status: PaymentStatus = PaymentStatus.PENDING
    payment_reference: Optional[str] = None
    payment_proof: Optional[str] = None
    order_status: OrderStatus = OrderStatus.PLACED
    address: Dict[str, Any]
    delivery_agent_id: Optional[str] = None
    delivery_agent_name: Optional[str] = None
    delivery_note: Optional[str] = ""
    cancellation_reason: Optional[str] = None
    tracking: List[TrackingEvent] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
