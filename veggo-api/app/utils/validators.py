from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.models.order import OrderStatus


def validate_object_id(id_str: str) -> ObjectId:
    """Validates string as valid 24-character hexadecimal MongoDB ObjectId."""
    if not ObjectId.is_valid(id_str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "message": f"Invalid ID format: '{id_str}'",
                "error_code": "INVALID_ID_FORMAT"
            }
        )
    return ObjectId(id_str)


# Allowed forward status progressions
VALID_ORDER_TRANSITIONS = {
    OrderStatus.PLACED: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
    OrderStatus.CONFIRMED: [OrderStatus.PREPARING, OrderStatus.CANCELLED],
    OrderStatus.PREPARING: [OrderStatus.READY_FOR_PICKUP, OrderStatus.CANCELLED],
    OrderStatus.READY_FOR_PICKUP: [OrderStatus.OUT_FOR_DELIVERY, OrderStatus.CANCELLED],
    OrderStatus.OUT_FOR_DELIVERY: [OrderStatus.DELIVERED, OrderStatus.CANCELLED],
    OrderStatus.DELIVERED: [],  # Terminal state
    OrderStatus.CANCELLED: [],  # Terminal state
}


def validate_order_status_transition(
    current_status: OrderStatus,
    new_status: OrderStatus,
    is_admin: bool = False
) -> bool:
    """
    Validates whether an order status transition is permissible.
    Non-admin cannot bypass valid transitions or cancel after dispatch.
    """
    if current_status == new_status:
        return True
        
    allowed_next = VALID_ORDER_TRANSITIONS.get(current_status, [])
    
    if new_status in allowed_next:
        return True
        
    # Admin override permissions for exceptional customer support cases
    if is_admin:
        # Prevent completely nonsensical moves even for admin unless explicit
        if current_status == OrderStatus.DELIVERED and new_status not in [OrderStatus.CANCELLED]:
            return False
        return True

    return False
