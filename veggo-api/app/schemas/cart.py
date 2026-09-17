from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class CartItemAdd(BaseModel):
    product_id: str
    quantity: float = Field(..., gt=0, description="Quantity in grams or pieces")
    unit: str = Field(..., description="'g', 'kg', 'pcs', 'pack', 'bundle'")


class CartItemUpdate(BaseModel):
    quantity: float = Field(..., gt=0)
    unit: Optional[str] = None


class CartItemResponse(BaseModel):
    product_id: str
    product_name: str
    product_image: Optional[str] = ""
    unit_type: str
    quantity: float
    unit: str
    unit_price: float
    calculated_price: float
    is_available: bool = True
    added_at: datetime


class CartResponse(BaseModel):
    items: List[CartItemResponse] = []
    items_count: int = 0
    subtotal: float = 0.0
    estimated_delivery_fee: float = 150.0
    discount: float = 0.0
    coupon_code: Optional[str] = None
    total: float = 0.0
    currency: str = "LKR"
