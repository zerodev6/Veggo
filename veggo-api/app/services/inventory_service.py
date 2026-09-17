import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.inventory import InventoryEventType

logger = logging.getLogger("veggo.inventory")


class InventoryService:
    @staticmethod
    async def reserve_stock_atomic(
        db: AsyncIOMotorDatabase,
        product_id: str,
        quantity: float,
        unit: str,
        order_number: str
    ) -> float:
        """
        Atomically decrements product stock to prevent race-condition overselling.
        If stock is insufficient, raises HTTP 400.
        Returns the new remaining stock.
        """
        p_oid = ObjectId(product_id)
        product = await db.products.find_one({"_id": p_oid})
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product '{product_id}' not found."
            )

        unit = unit.lower().strip()
        unit_type = product.get("unit_type", "WEIGHT")

        # Normalize quantity to product stock unit (kg for WEIGHT, piece count for others)
        if unit_type == "WEIGHT":
            if unit in ["g", "gram", "grams"]:
                deduct_amount = quantity / 1000.0
            else:
                deduct_amount = quantity
        else:
            deduct_amount = quantity

        current_stock = float(product.get("stock", 0.0))

        # Atomic decrement with condition stock >= deduct_amount
        res = await db.products.find_one_and_update(
            {"_id": p_oid, "stock": {"$gte": deduct_amount}},
            {
                "$inc": {"stock": -deduct_amount},
                "$set": {"updated_at": datetime.utcnow()}
            },
            return_document=True
        )

        if not res:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for '{product.get('name')}'. Available: {current_stock}, Requested: {deduct_amount}"
            )

        new_stock = float(res.get("stock", 0.0))

        # Log inventory log event
        try:
            await db.inventory_logs.insert_one({
                "product_id": str(product_id),
                "event_type": InventoryEventType.ORDER_RESERVED.value,
                "quantity_change": -deduct_amount,
                "previous_stock": current_stock,
                "new_stock": new_stock,
                "reference_id": order_number,
                "note": f"Reserved for order {order_number}",
                "created_at": datetime.utcnow()
            })
        except Exception as e:
            logger.error(f"Failed to log inventory change: {e}")

        return new_stock

    @staticmethod
    async def release_stock_atomic(
        db: AsyncIOMotorDatabase,
        product_id: str,
        quantity: float,
        unit: str,
        order_number: str
    ):
        """Restores reserved inventory when an order is cancelled or rejected."""
        try:
            p_oid = ObjectId(product_id)
            product = await db.products.find_one({"_id": p_oid})
            if not product:
                return

            unit = unit.lower().strip()
            unit_type = product.get("unit_type", "WEIGHT")

            if unit_type == "WEIGHT":
                restore_amount = (quantity / 1000.0) if unit in ["g", "gram", "grams"] else quantity
            else:
                restore_amount = quantity

            current_stock = float(product.get("stock", 0.0))
            
            res = await db.products.find_one_and_update(
                {"_id": p_oid},
                {
                    "$inc": {"stock": restore_amount},
                    "$set": {"updated_at": datetime.utcnow()}
                },
                return_document=True
            )
            
            if res:
                new_stock = float(res.get("stock", 0.0))
                await db.inventory_logs.insert_one({
                    "product_id": str(product_id),
                    "event_type": InventoryEventType.ORDER_CANCELLED.value,
                    "quantity_change": restore_amount,
                    "previous_stock": current_stock,
                    "new_stock": new_stock,
                    "reference_id": order_number,
                    "note": f"Restored from cancelled order {order_number}",
                    "created_at": datetime.utcnow()
                })
        except Exception as e:
            logger.error(f"Failed to release stock for product {product_id}: {e}")

    @staticmethod
    async def log_price_change(
        db: AsyncIOMotorDatabase,
        product_id: str,
        old_price: float,
        new_price: float,
        changed_by: str
    ):
        """Tracks audit log of product price modifications."""
        try:
            await db.price_history.insert_one({
                "product_id": str(product_id),
                "old_price": old_price,
                "new_price": new_price,
                "changed_by": changed_by,
                "created_at": datetime.utcnow()
            })
        except Exception as e:
            logger.error(f"Failed to log price change: {e}")


inventory_service = InventoryService()
