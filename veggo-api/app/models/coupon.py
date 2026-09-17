from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class DiscountType(str, Enum):
    FIXED = "FIXED"
    PERCENTAGE = "PERCENTAGE"


class CouponInDB(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    code: str
    discount_type: DiscountType = DiscountType.FIXED
    discount_value: float  # e.g. 100 LKR or 10%
    minimum_order: float = 1000.0
    maximum_discount: Optional[float] = 500.0  # Cap for percentage discounts
    usage_limit: int = 100
    used_count: int = 0
    expires_at: Optional[datetime] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
