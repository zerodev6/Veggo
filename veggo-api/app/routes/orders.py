from typing import Any, Dict, List, Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_database
from app.models.order import OrderStatus, PaymentStatus
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.order import (
    BankProofUpload,
    CancelOrderRequest,
    CheckoutRequest,
    OrderResponse,
    OrderTrackingResponse,
)
from app.services.auth_service import get_current_user
from app.services.order_service import order_service
from app.utils.pagination import build_paginated_response, parse_pagination
from app.utils.validators import validate_object_id

router = APIRouter(prefix="/api/orders", tags=["Orders"])


def serialize_order(doc: Dict[str, Any]) -> OrderResponse:
    return OrderResponse(
        id=str(doc["_id"]),
        order_number=doc["order_number"],
        user_id=str(doc["user_id"]),
        customer_name=doc.get("customer_name", ""),
        customer_phone=doc.get("customer_phone", ""),
        items=doc.get("items", []),
        subtotal=float(doc.get("subtotal", 0.0)),
        delivery_fee=float(doc.get("delivery_fee", 0.0)),
        discount=float(doc.get("discount", 0.0)),
        coupon_code=doc.get("coupon_code"),
        total=float(doc.get("total", 0.0)),
        payment_method=doc.get("payment_method", "COD"),
        payment_status=doc.get("payment_status", "PENDING"),
        payment_reference=doc.get("payment_reference"),
        payment_proof=doc.get("payment_proof"),
        order_status=doc.get("order_status", "PLACED"),
        address=doc.get("address", {}),
        delivery_agent_id=doc.get("delivery_agent_id"),
        delivery_agent_name=doc.get("delivery_agent_name"),
        delivery_note=doc.get("delivery_note", ""),
        cancellation_reason=doc.get("cancellation_reason"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"]
    )


@router.post(
    "/checkout",
    response_model=APIResponse[OrderResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Checkout Cart & Place Order",
    description="Processes cart items, recalculates server prices, reserves stock atomically, and creates the order."
)
async def checkout(
    req: CheckoutRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    order_doc = await order_service.checkout(db, current_user, req)
    return APIResponse(
        message="Order placed successfully! 🥬",
        data=serialize_order(order_doc)
    )


@router.get(
    "",
    response_model=PaginatedResponse[OrderResponse],
    summary="Get User Orders",
    description="Returns order history of the authenticated customer with pagination."
)
async def get_my_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    skip, limit, page = parse_pagination(page, limit)
    user_id = str(current_user["_id"])
    query = {"user_id": user_id}

    total = await db.orders.count_documents(query)
    cursor = db.orders.find(query).sort("created_at", -1).skip(skip).limit(limit)
    orders_raw = await cursor.to_list(length=limit)

    items = [serialize_order(o).model_dump() for o in orders_raw]
    return build_paginated_response(items, total, page, limit)


@router.get(
    "/{id}",
    response_model=APIResponse[OrderResponse],
    summary="Get Order Details",
    description="Retrieves full details of a customer's specific order."
)
async def get_order_by_id(
    id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    oid = validate_object_id(id)
    user_id = str(current_user["_id"])
    role = current_user.get("role", "USER")

    query = {"_id": oid} if role in ["ADMIN", "DELIVERY_AGENT"] else {"_id": oid, "user_id": user_id}
    order = await db.orders.find_one(query)

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "message": "Order not found", "error_code": "ORDER_NOT_FOUND"}
        )

    return APIResponse(data=serialize_order(order))


@router.post(
    "/{id}/cancel",
    response_model=APIResponse[OrderResponse],
    summary="Cancel Order",
    description="Cancels an eligible order (PLACED or CONFIRMED) and automatically releases reserved stock."
)
async def cancel_order(
    id: str,
    req: CancelOrderRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    user_id = str(current_user["_id"])
    is_admin = current_user.get("role") == "ADMIN"
    order = await order_service.cancel_order(db, id, user_id, req.reason, is_admin=is_admin)
    return APIResponse(message="Order cancelled successfully", data=serialize_order(order))


@router.get(
    "/{id}/tracking",
    response_model=APIResponse[OrderTrackingResponse],
    summary="Track Order Timeline",
    description="Retrieves step-by-step delivery tracking timeline (PLACED -> CONFIRMED -> PREPARING -> READY -> OUT_FOR_DELIVERY -> DELIVERED)."
)
async def track_order(
    id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    oid = validate_object_id(id)
    order = await db.orders.find_one({"_id": oid})

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "message": "Order not found", "error_code": "ORDER_NOT_FOUND"}
        )

    # Permission check
    if current_user.get("role") not in ["ADMIN", "DELIVERY_AGENT"] and order["user_id"] != str(current_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"success": False, "message": "Access denied to tracking data", "error_code": "FORBIDDEN"}
        )

    return APIResponse(
        data=OrderTrackingResponse(
            order_id=str(order["_id"]),
            order_number=order["order_number"],
            order_status=OrderStatus(order.get("order_status", "PLACED")),
            estimated_delivery="Within 2-4 hours",
            timeline=order.get("tracking", [])
        )
    )


@router.post(
    "/{id}/proof",
    response_model=APIResponse[OrderResponse],
    summary="Upload Bank Payment Proof",
    description="Customer attaches transaction reference and receipt image for Bank Transfer payments."
)
async def upload_payment_proof(
    id: str,
    req: BankProofUpload,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    oid = validate_object_id(id)
    order = await db.orders.find_one({"_id": oid, "user_id": str(current_user["_id"])})

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "message": "Order not found", "error_code": "ORDER_NOT_FOUND"}
        )

    await db.orders.update_one(
        {"_id": oid},
        {
            "$set": {
                "payment_reference": req.payment_reference,
                "payment_proof": req.payment_proof,
                "payment_status": PaymentStatus.PENDING.value
            }
        }
    )
    updated = await db.orders.find_one({"_id": oid})
    return APIResponse(message="Payment receipt attached. Veggo staff will verify shortly.", data=serialize_order(updated))
