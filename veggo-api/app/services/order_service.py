import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.config import settings
from app.models.order import (
    OrderItemSnapshot,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    TrackingEvent,
)
from app.schemas.order import CheckoutRequest
from app.services.delivery_service import delivery_service
from app.services.inventory_service import inventory_service
from app.services.notification_service import notification_service
from app.services.pricing_service import pricing_service
from app.utils.helpers import generate_order_number
from app.utils.validators import validate_object_id

logger = logging.getLogger("veggo.order_service")


class OrderService:
    @staticmethod
    async def checkout(
        db: AsyncIOMotorDatabase,
        current_user: Dict[str, Any],
        req: CheckoutRequest
    ) -> Dict[str, Any]:
        """
        Executes complete checkout pipeline:
        1. Store availability check
        2. Address verification
        3. Cart retrieval & item stock verification
        4. Server-side price & weight calculation
        5. Coupon application
        6. Delivery fee computation
        7. Atomic stock reservation
        8. Order creation with immutable snapshots
        9. Cart clearance & user notification
        """
        user_id = str(current_user["_id"])

        # 1. Check store status & order acceptance
        if not settings.ORDER_ACCEPTANCE_ENABLED or settings.MAINTENANCE_MODE:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"success": False, "message": "The store is temporarily not accepting orders.", "error_code": "STORE_CLOSED"}
            )

        # 2. Check address
        addr_id = validate_object_id(req.address_id)
        address = await db.addresses.find_one({"_id": addr_id, "user_id": user_id})
        if not address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"success": False, "message": "Selected delivery address not found.", "error_code": "ADDRESS_NOT_FOUND"}
            )

        # 3. Retrieve user cart
        cart = await db.carts.find_one({"user_id": user_id})
        if not cart or not cart.get("items"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "message": "Your cart is empty.", "error_code": "EMPTY_CART"}
            )

        cart_items = cart.get("items", [])
        order_snapshots: List[Dict[str, Any]] = []
        calculated_subtotal = 0.0

        # 4 & 5. Validate each product and re-calculate prices on server
        for item in cart_items:
            p_id = item["product_id"]
            qty = float(item["quantity"])
            unit = item["unit"]

            product = await db.products.find_one({"_id": ObjectId(p_id)})
            if not product or not product.get("is_available", True):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"success": False, "message": f"Product '{item.get('product_name', p_id)}' is no longer available.", "error_code": "PRODUCT_UNAVAILABLE"}
                )

            # Recalculate true price on server
            unit_price, line_total = pricing_service.calculate_line_item_price(
                unit_type=product.get("unit_type", "WEIGHT"),
                price_per_kg=product.get("price_per_kg"),
                price_per_piece=product.get("price_per_piece"),
                quantity=qty,
                unit=unit
            )

            calculated_subtotal += line_total

            order_snapshots.append({
                "product_id": str(product["_id"]),
                "product_name": product["name"],
                "product_image": product.get("images", [""])[0] if product.get("images") else "",
                "unit_type": product.get("unit_type", "WEIGHT"),
                "price_at_purchase": unit_price,
                "quantity": qty,
                "unit": unit,
                "subtotal": line_total
            })

        calculated_subtotal = round(calculated_subtotal, 2)

        # 6. Apply coupon if provided
        discount_amount = 0.0
        applied_coupon_code = None
        coupon_to_use = req.coupon_code or cart.get("coupon_code")

        if coupon_to_use:
            is_valid, discount, _ = await pricing_service.validate_coupon(
                db, coupon_to_use, calculated_subtotal, user_id
            )
            if is_valid:
                discount_amount = discount
                applied_coupon_code = coupon_to_use.strip().upper()

        # 7. Delivery fee estimation
        delivery_est = await delivery_service.estimate_delivery_fee(
            db=db,
            subtotal=calculated_subtotal,
            latitude=address.get("latitude"),
            longitude=address.get("longitude"),
            district=address.get("district"),
            city=address.get("city")
        )

        if not delivery_est.get("is_serviceable", True):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "message": delivery_est.get("reason", "Location is outside serviceable delivery radius"), "error_code": "UNSERVICEABLE_LOCATION"}
            )

        delivery_fee = float(delivery_est["delivery_fee"])
        final_total = round(max(0.0, (calculated_subtotal - discount_amount) + delivery_fee), 2)

        # 8. Generate order number
        order_num = await generate_order_number(db)

        # 9. Atomically reserve inventory for each item
        reserved_items: List[Dict[str, Any]] = []
        try:
            for snap in order_snapshots:
                await inventory_service.reserve_stock_atomic(
                    db=db,
                    product_id=snap["product_id"],
                    quantity=snap["quantity"],
                    unit=snap["unit"],
                    order_number=order_num
                )
                reserved_items.append(snap)
        except HTTPException as e:
            # Rollback reserved items if any product failed stock check
            for res_snap in reserved_items:
                await inventory_service.release_stock_atomic(
                    db=db,
                    product_id=res_snap["product_id"],
                    quantity=res_snap["quantity"],
                    unit=res_snap["unit"],
                    order_number=order_num
                )
            raise e

        # 10. Increment coupon used count if coupon applied
        if applied_coupon_code:
            await db.coupons.update_one(
                {"code": applied_coupon_code},
                {"$inc": {"used_count": 1}}
            )

        # 11. Create order record
        now = datetime.utcnow()
        clean_address = {
            "name": address.get("name"),
            "phone": address.get("phone"),
            "address_line": address.get("address_line"),
            "city": address.get("city"),
            "district": address.get("district"),
            "province": address.get("province"),
            "postal_code": address.get("postal_code", ""),
            "latitude": address.get("latitude"),
            "longitude": address.get("longitude")
        }

        initial_tracking = [{
            "status": OrderStatus.PLACED.value,
            "message": "Order successfully placed and received by Veggo.",
            "timestamp": now,
            "updated_by": "CUSTOMER"
        }]

        order_doc = {
            "order_number": order_num,
            "user_id": user_id,
            "customer_name": current_user.get("name", "Customer"),
            "customer_phone": current_user.get("phone", address.get("phone")),
            "items": order_snapshots,
            "subtotal": calculated_subtotal,
            "delivery_fee": delivery_fee,
            "discount": discount_amount,
            "coupon_code": applied_coupon_code,
            "total": final_total,
            "payment_method": req.payment_method.value,
            "payment_status": PaymentStatus.PENDING.value,
            "payment_reference": req.payment_reference,
            "payment_proof": None,
            "order_status": OrderStatus.PLACED.value,
            "address": clean_address,
            "delivery_agent_id": None,
            "delivery_agent_name": None,
            "delivery_note": req.delivery_note or address.get("delivery_note", ""),
            "cancellation_reason": None,
            "tracking": initial_tracking,
            "created_at": now,
            "updated_at": now
        }

        res = await db.orders.insert_one(order_doc)
        order_id = str(res.inserted_id)
        order_doc["id"] = order_id
        order_doc["_id"] = str(order_doc["_id"])

        # 12. Clear user's cart
        await db.carts.update_one(
            {"user_id": user_id},
            {"$set": {"items": [], "subtotal": 0.0, "discount": 0.0, "coupon_code": None, "total": 0.0, "updated_at": now}}
        )

        # 13. Create in-app notification
        await notification_service.create_notification(
            db=db,
            user_id=user_id,
            title="Order Placed! 🥬",
            message=f"Your order {order_num} for Rs. {final_total:.2f} has been placed.",
            notification_type="ORDER_PLACED",
            data={"order_id": order_id, "order_number": order_num}
        )

        return order_doc

    @staticmethod
    async def cancel_order(
        db: AsyncIOMotorDatabase,
        order_id: str,
        user_id: str,
        reason: str,
        is_admin: bool = False
    ) -> Dict[str, Any]:
        """Cancels an eligible order and restores inventory."""
        oid = validate_object_id(order_id)
        query = {"_id": oid} if is_admin else {"_id": oid, "user_id": user_id}
        order = await db.orders.find_one(query)

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"success": False, "message": "Order not found", "error_code": "ORDER_NOT_FOUND"}
            )

        current_status = OrderStatus(order.get("order_status", "PLACED"))

        # Customers can only cancel if PLACED or CONFIRMED
        if not is_admin and current_status not in [OrderStatus.PLACED, OrderStatus.CONFIRMED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "message": f"Cannot cancel order in '{current_status.value}' state. Please contact customer support.", "error_code": "CANNOT_CANCEL"}
            )

        now = datetime.utcnow()
        tracking_event = {
            "status": OrderStatus.CANCELLED.value,
            "message": f"Order cancelled: {reason}",
            "timestamp": now,
            "updated_by": "ADMIN" if is_admin else "CUSTOMER"
        }

        # Restore inventory
        order_items = order.get("items", [])
        for item in order_items:
            await inventory_service.release_stock_atomic(
                db=db,
                product_id=item["product_id"],
                quantity=item["quantity"],
                unit=item["unit"],
                order_number=order.get("order_number", "")
            )

        # Update order status
        await db.orders.update_one(
            {"_id": oid},
            {
                "$set": {
                    "order_status": OrderStatus.CANCELLED.value,
                    "cancellation_reason": reason,
                    "updated_at": now
                },
                "$push": {"tracking": tracking_event}
            }
        )

        # Notify user
        await notification_service.create_notification(
            db=db,
            user_id=order["user_id"],
            title="Order Cancelled",
            message=f"Order {order.get('order_number')} has been cancelled.",
            notification_type="ORDER_CANCELLED",
            data={"order_id": str(order["_id"])}
        )

        order["order_status"] = OrderStatus.CANCELLED.value
        order["cancellation_reason"] = reason
        order["id"] = str(order["_id"])
        return order


order_service = OrderService()
