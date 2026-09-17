from datetime import datetime
from typing import Any, Dict
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_database
from app.models.coupon import DiscountType
from app.schemas.common import APIResponse
from app.schemas.coupon import CouponValidateRequest, CouponValidateResponse
from app.services.auth_service import get_current_user
from app.services.pricing_service import pricing_service

router = APIRouter(prefix="/api/coupons", tags=["Coupons"])


@router.post(
    "/validate",
    response_model=APIResponse[CouponValidateResponse],
    summary="Validate Promotional Coupon",
    description="Validates coupon code against cart subtotal, expiration date, and usage limits."
)
async def validate_coupon_code(
    req: CouponValidateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    code = req.code.strip().upper()
    user_id = str(current_user["_id"])

    # If subtotal not provided in payload, fetch from active cart
    subtotal = req.cart_subtotal
    if subtotal is None:
        cart = await db.carts.find_one({"user_id": user_id})
        subtotal = float(cart.get("subtotal", 0.0)) if cart else 0.0

    coupon = await db.coupons.find_one({"code": code, "is_active": True})
    if not coupon:
        return APIResponse(
            message="Coupon not found or inactive",
            data=CouponValidateResponse(
                is_valid=False,
                code=code,
                discount_type=DiscountType.FIXED,
                discount_value=0.0,
                calculated_discount=0.0,
                message="Invalid or inactive coupon code"
            )
        )

    is_valid, calc_discount, msg = await pricing_service.validate_coupon(db, code, subtotal, user_id)

    # Attach coupon code to active cart if valid
    if is_valid:
        await db.carts.update_one({"user_id": user_id}, {"$set": {"coupon_code": code}})

    return APIResponse(
        message=msg,
        data=CouponValidateResponse(
            is_valid=is_valid,
            code=code,
            discount_type=DiscountType(coupon.get("discount_type", "FIXED")),
            discount_value=float(coupon.get("discount_value", 0.0)),
            calculated_discount=calc_discount,
            message=msg
        )
    )
