from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class CartItem(BaseModel):
    product_id: str
    product_name: str
    product_image: Optional[str] = ""
    unit_type: str = "WEIGHT"  # WEIGHT, PIECE, PACK, BUNDLE
    quantity: float  # e.g., 750 for grams, or 2 for pieces
    unit: str  # "g", "kg", "pcs", "pack", "bundle"
    unit_price: float  # Base price per kg or piece
    calculated_price: float  # Server calculated price for this line item
    is_available: bool = True
    added_at: datetime = Field(default_factory=datetime.utcnow)


class CartInDB(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    user_id: str
    items: List[CartItem] = []
    subtotal: float = 0.0
    estimated_delivery_fee: float = 150.0
    discount: float = 0.0
    coupon_code: Optional[str] = None
    total: float = 0.0
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
