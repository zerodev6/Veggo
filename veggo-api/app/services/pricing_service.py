from datetime import datetime
from typing import Any, Dict, Optional, Tuple
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.config import settings
from app.models.coupon import DiscountType


class PricingService:
    @staticmethod
    def calculate_line_item_price(
        unit_type: str,
        price_per_kg: Optional[float],
        price_per_piece: Optional[float],
        quantity: float,
        unit: str
    ) -> Tuple[float, float]:
        """
        Calculates exact line item price on server.
        Returns: (base_unit_price, total_item_price)
        
        Rules:
        - If unit_type is WEIGHT:
            If unit is 'g' (grams), price = (price_per_kg / 1000.0) * quantity
            If unit is 'kg', price = price_per_kg * quantity
        - If unit_type is PIECE / PACK / BUNDLE:
            price = price_per_piece * quantity
        """
        unit = unit.lower().strip()
        
        if unit_type == "WEIGHT":
            if price_per_kg is None or price_per_kg < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Product does not have a valid price per kg."
                )
            base_price = float(price_per_kg)
            
            if unit in ["g", "gram", "grams"]:
                # Convert grams to kg fraction
                calculated = (base_price / 1000.0) * float(quantity)
            elif unit in ["kg", "kilo", "kilogram"]:
                calculated = base_price * float(quantity)
            else:
                # Default assume grams if > 10, otherwise kg
                if quantity >= 10:
                    calculated = (base_price / 1000.0) * float(quantity)
                else:
                    calculated = base_price * float(quantity)
            
            return base_price, round(calculated, 2)
            
        else:
            # PIECE, PACK, BUNDLE
            if price_per_piece is None or price_per_piece < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Product does not have a valid piece/pack price."
                )
            base_price = float(price_per_piece)
            calculated = base_price * float(quantity)
            return base_price, round(calculated, 2)

    @staticmethod
    async def validate_coupon(
        db: AsyncIOMotorDatabase,
        code: str,
        subtotal: float,
        user_id: Optional[str] = None
    ) -> Tuple[bool, float, str]:
        """
        Validates a coupon code against subtotal, usage limit, expiration, and active status.
        Returns: (is_valid, discount_amount, message)
        """
        if not code:
            return False, 0.0, "No coupon provided"
            
        code = code.strip().upper()
        coupon = await db.coupons.find_one({"code": code, "is_active": True})
        
        if not coupon:
            return False, 0.0, "Coupon code is invalid or inactive"
            
        # Check expiration
        expires_at = coupon.get("expires_at")
        if expires_at and datetime.utcnow() > expires_at:
            return False, 0.0, "Coupon code has expired"
            
        # Check usage limit
        usage_limit = coupon.get("usage_limit", 100)
        used_count = coupon.get("used_count", 0)
        if used_count >= usage_limit:
            return False, 0.0, "Coupon usage limit has been reached"
            
        # Check minimum order subtotal
        min_order = coupon.get("minimum_order", 0.0)
        if subtotal < min_order:
            return False, 0.0, f"Minimum order of Rs. {min_order:.2f} required for this coupon"
            
        # Calculate discount
        discount_type = coupon.get("discount_type", "FIXED")
        discount_val = coupon.get("discount_value", 0.0)
        
        if discount_type == DiscountType.PERCENTAGE:
            calc_discount = (subtotal * discount_val) / 100.0
            max_disc = coupon.get("maximum_discount")
            if max_disc and calc_discount > max_disc:
                calc_discount = max_disc
        else:
            calc_discount = min(discount_val, subtotal)
            
        return True, round(calc_discount, 2), "Coupon applied successfully"


pricing_service = PricingService()
