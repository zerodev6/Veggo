from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.models.coupon import DiscountType


class CouponCreate(BaseModel):
    code: str = Field(..., min_length=3, max_length=20)
    discount_type: DiscountType = DiscountType.FIXED
    discount_value: float = Field(..., gt=0)
    minimum_order: float = Field(1000.0, ge=0)
    maximum_discount: Optional[float] = Field(500.0, ge=0)
    usage_limit: int = Field(100, ge=1)
    expires_at: Optional[datetime] = None
    is_active: bool = True


class CouponUpdate(BaseModel):
    discount_type: Optional[DiscountType] = None
    discount_value: Optional[float] = None
    minimum_order: Optional[float] = None
    maximum_discount: Optional[float] = None
    usage_limit: Optional[int] = None
    expires_at: Optional[datetime] = None
    is_active: Optional[bool] = None


class CouponValidateRequest(BaseModel):
    code: str
    cart_subtotal: Optional[float] = None


class CouponValidateResponse(BaseModel):
    is_valid: bool
    code: str
    discount_type: DiscountType
    discount_value: float
    calculated_discount: float
    message: str


class CouponResponse(BaseModel):
    id: str
    code: str
    discount_type: DiscountType
    discount_value: float
    minimum_order: float
    maximum_discount: Optional[float] = None
    usage_limit: int
    used_count: int
    expires_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime
