from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.config import settings
from app.database import get_database
from app.models.coupon import CouponInDB
from app.models.order import OrderStatus, PaymentStatus
from app.models.user import UserRole
from app.routes.orders import serialize_order
from app.schemas.auth import UserResponse
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.coupon import CouponCreate, CouponResponse, CouponUpdate
from app.schemas.order import OrderResponse
from app.services.auth_service import require_admin
from app.services.inventory_service import inventory_service
from app.services.notification_service import notification_service
from app.utils.helpers import log_audit_event
from app.utils.pagination import build_paginated_response, parse_pagination
from app.utils.validators import validate_object_id, validate_order_status_transition

router = APIRouter(prefix="/api/admin", tags=["Admin Operations"])


class AdminStatusUpdate(BaseModel):
    status: OrderStatus
    note: Optional[str] = None


class AdminPaymentUpdate(BaseModel):
    payment_status: PaymentStatus
    payment_reference: Optional[str] = None
    note: Optional[str] = None


class AdminAssignAgent(BaseModel):
    agent_id: str


class AdminBannerCreate(BaseModel):
    title: str = Field(..., min_length=2)
    subtitle: Optional[str] = ""
    image: str = Field(..., min_length=5)
    product_ids: List[str] = []
    category_id: Optional[str] = None
    is_active: bool = True
    priority: int = 1


class AdminStoreSettingsUpdate(BaseModel):
    store_name: Optional[str] = None
    store_phone: Optional[str] = None
    store_email: Optional[str] = None
    store_address: Optional[str] = None
    currency: Optional[str] = None
    base_delivery_fee: Optional[float] = None
    free_delivery_threshold: Optional[float] = None
    per_km_delivery_fee: Optional[float] = None
    minimum_order: Optional[float] = None
    maximum_delivery_distance_km: Optional[float] = None
    opening_time: Optional[str] = None
    closing_time: Optional[str] = None
    order_acceptance_enabled: Optional[bool] = None
    maintenance_mode: Optional[bool] = None


@router.get(
    "/dashboard",
    response_model=APIResponse[Dict[str, Any]],
    summary="Admin Operational Dashboard",
    description="Real-time aggregation of store revenue, order pipeline, active users, and low-stock alerts."
)
async def get_dashboard_metrics(
    low_stock_threshold: float = Query(10.0, ge=0),
    current_admin: Dict[str, Any] = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    month_start = datetime(now.year, now.month, 1)

    # User counts
    total_users = await db.users.count_documents({"role": UserRole.USER.value})
    active_users = await db.users.count_documents({"role": UserRole.USER.value, "is_active": True})

    # Catalog & Low Stock
    total_products = await db.products.count_documents({})
    low_stock_products = await db.products.count_documents({"stock": {"$lte": low_stock_threshold}})

    # Order statistics
    total_orders = await db.orders.count_documents({})
    pending_orders = await db.orders.count_documents({"order_status": {"$in": [OrderStatus.PLACED.value, OrderStatus.CONFIRMED.value, OrderStatus.PREPARING.value]}})
    cancelled_orders = await db.orders.count_documents({"order_status": OrderStatus.CANCELLED.value})
    delivery_orders = await db.orders.count_documents({"order_status": OrderStatus.OUT_FOR_DELIVERY.value})
    today_orders = await db.orders.count_documents({"created_at": {"$gte": today_start}})

    # Revenue pipeline
    pipeline_today = [
        {"$match": {"created_at": {"$gte": today_start}, "order_status": {"$ne": OrderStatus.CANCELLED.value}}},
        {"$group": {"_id": None, "rev": {"$sum": "$total"}}}
    ]
    res_today = await db.orders.aggregate(pipeline_today).to_list(length=1)
    today_revenue = round(float(res_today[0]["rev"]), 2) if res_today else 0.0

    pipeline_month = [
        {"$match": {"created_at": {"$gte": month_start}, "order_status": {"$ne": OrderStatus.CANCELLED.value}}},
        {"$group": {"_id": None, "rev": {"$sum": "$total"}}}
    ]
    res_month = await db.orders.aggregate(pipeline_month).to_list(length=1)
    month_revenue = round(float(res_month[0]["rev"]), 2) if res_month else 0.0

    return APIResponse(data={
        "total_users": total_users,
        "active_users": active_users,
        "total_products": total_products,
        "low_stock_products": low_stock_products,
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "today_orders": today_orders,
        "today_revenue": today_revenue,
        "monthly_revenue": month_revenue,
        "cancelled_orders": cancelled_orders,
        "delivery_orders": delivery_orders,
        "currency": settings.CURRENCY
    })


# ---------------- ORDERS MANAGEMENT ----------------

@router.get(
    "/orders",
    response_model=PaginatedResponse[OrderResponse],
    summary="Admin Orders List",
    description="Lists all customer orders with status, date, and customer filters."
)
async def admin_get_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    payment_status: Optional[str] = Query(None),
    current_admin: Dict[str, Any] = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    skip, limit, page = parse_pagination(page, limit)
    query: Dict[str, Any] = {}
    if status:
        query["order_status"] = status
    if payment_status:
        query["payment_status"] = payment_status

    total = await db.orders.count_documents(query)
    cursor = db.orders.find(query).sort("created_at", -1).skip(skip).limit(limit)
    orders_raw = await cursor.to_list(length=limit)

    items = [serialize_order(o).model_dump() for o in orders_raw]
    return build_paginated_response(items, total, page, limit)


@router.get(
    "/orders/{id}",
    response_model=APIResponse[OrderResponse],
    summary="Admin Get Order Detail",
    description="Retrieves comprehensive order snapshot for administration."
)
async def admin_get_order(
    id: str,
    current_admin: Dict[str, Any] = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    oid = validate_object_id(id)
    order = await db.orders.find_one({"_id": oid})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return APIResponse(data=serialize_order(order))


@router.put(
    "/orders/{id}/status",
    response_model=APIResponse[OrderResponse],
    summary="Admin Update Order Status",
    description="Admin transitions order status (CONFIRMED, PREPARING, READY_FOR_PICKUP, DELIVERED, CANCELLED)."
)
async def admin_update_order_status(
    id: str,
    req: AdminStatusUpdate,
    current_admin: Dict[str, Any] = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    oid = validate_object_id(id)
    order = await db.orders.find_one({"_id": oid})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    curr_status = OrderStatus(order.get("order_status", "PLACED"))
    if not validate_order_status_transition(curr_status, req.status, is_admin=True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid transition from {curr_status.value} to {req.status.value}"
        )

    # If status is CANCELLED, release inventory
    if req.status == OrderStatus.CANCELLED and curr_status != OrderStatus.CANCELLED:
        for item in order.get("items", []):
            await inventory_service.release_stock_atomic(
                db, item["product_id"], item["quantity"], item["unit"], order.get("order_number", "")
            )

    now = datetime.utcnow()
    tracking_msg = req.note or f"Order status updated to {req.status.value} by Veggo Admin."
    tracking_event = {
        "status": req.status.value,
        "message": tracking_msg,
        "timestamp": now,
        "updated_by": f"ADMIN_{current_admin.get('name', 'Admin')}"
    }

    updated = await db.orders.find_one_and_update(
        {"_id": oid},
        {
            "$set": {"order_status": req.status.value, "updated_at": now},
            "$push": {"tracking": tracking_event}
        },
        return_document=True
    )

    await log_audit_event(
        db, str(current_admin["_id"]), "ORDER_STATUS_CHANGED", "ORDER", id,
        old_value=curr_status.value, new_value=req.status.value
    )

    await notification_service.create_notification(
        db=db,
        user_id=order["user_id"],
        title=f"Order Update: {req.status.value}",
        message=tracking_msg,
        notification_type=req.status.value,
        data={"order_id": id}
    )

    return APIResponse(message="Order status updated", data=serialize_order(updated))


@router.put(
    "/orders/{id}/payment",
    response_model=APIResponse[OrderResponse],
    summary="Admin Verify & Update Payment Status",
    description="Admin approves Bank Transfer receipt or updates payment status (PAID, REJECTED, REFUNDED)."
)
async def admin_update_payment_status(
    id: str,
    req: AdminPaymentUpdate,
    current_admin: Dict[str, Any] = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    oid = validate_object_id(id)
    order = await db.orders.find_one({"_id": oid})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    old_payment = order.get("payment_status", "PENDING")
    updates: Dict[str, Any] = {
        "payment_status": req.payment_status.value,
        "updated_at": datetime.utcnow()
    }
    if req.payment_reference:
        updates["payment_reference"] = req.payment_reference

    updated = await db.orders.find_one_and_update(
        {"_id": oid},
        {"$set": updates},
        return_document=True
    )

    await log_audit_event(
        db, str(current_admin["_id"]), "PAYMENT_STATUS_CHANGED", "ORDER", id,
        old_value=old_payment, new_value=req.payment_status.value
    )

    return APIResponse(message="Payment status updated", data=serialize_order(updated))


@router.put(
    "/orders/{id}/assign-agent",
    response_model=APIResponse[OrderResponse],
    summary="Admin Assign Delivery Agent",
    description="Assigns a delivery agent to an order."
)
async def admin_assign_agent(
    id: str,
    req: AdminAssignAgent,
    current_admin: Dict[str, Any] = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    oid = validate_object_id(id)
    agent_oid = validate_object_id(req.agent_id)
    agent = await db.users.find_one({"_id": agent_oid, "role": UserRole.DELIVERY_AGENT.value})

    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery agent not found")

    now = datetime.utcnow()
    tracking_event = {
        "status": OrderStatus.READY_FOR_PICKUP.value,
        "message": f"Assigned to delivery agent {agent.get('name')}.",
        "timestamp": now,
        "updated_by": "ADMIN"
    }

    updated = await db.orders.find_one_and_update(
        {"_id": oid},
        {
            "$set": {
                "delivery_agent_id": str(agent["_id"]),
                "delivery_agent_name": agent.get("name"),
                "order_status": OrderStatus.READY_FOR_PICKUP.value,
                "updated_at": now
            },
            "$push": {"tracking": tracking_event}
        },
        return_document=True
    )

    await log_audit_event(
        db, str(current_admin["_id"]), "AGENT_ASSIGNED", "ORDER", id,
        new_value={"agent_id": req.agent_id, "agent_name": agent.get("name")}
    )

    return APIResponse(message="Delivery agent assigned", data=serialize_order(updated))


# ---------------- USER MANAGEMENT ----------------

@router.get(
    "/users",
    response_model=PaginatedResponse[UserResponse],
    summary="Admin List Users",
    description="Admin lists customers, delivery agents, and staff."
)
async def admin_get_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    role: Optional[str] = Query(None),
    current_admin: Dict[str, Any] = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    skip, limit, page = parse_pagination(page, limit)
    query: Dict[str, Any] = {}
    if role:
        query["role"] = role

    total = await db.users.count_documents(query)
    cursor = db.users.find(query).sort("created_at", -1).skip(skip).limit(limit)
    users_raw = await cursor.to_list(length=limit)

    items = [
        UserResponse(
            id=str(u["_id"]),
            name=u["name"],
            phone=u.get("phone"),
            email=u.get("email"),
            role=UserRole(u.get("role", "USER")),
            auth_provider=u.get("auth_provider", "password"),
            profile_image=u.get("profile_image"),
            language=u.get("language", "en"),
            notification_enabled=u.get("notification_enabled", True),
            created_at=u.get("created_at", datetime.utcnow())
        ).model_dump()
        for u in users_raw
    ]
    return build_paginated_response(items, total, page, limit)


@router.get(
    "/users/{id}",
    response_model=APIResponse[Dict[str, Any]],
    summary="Admin Get User Details & Order History",
    description="Retrieves user profile along with their order summary."
)
async def admin_get_user_detail(
    id: str,
    current_admin: Dict[str, Any] = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    oid = validate_object_id(id)
    user = await db.users.find_one({"_id": oid})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Order history count
    order_count = await db.orders.count_documents({"user_id": id})
    orders_cursor = db.orders.find({"user_id": id}).sort("created_at", -1).limit(5)
    recent_orders = await orders_cursor.to_list(length=5)

    data = {
        "user": {
            "id": str(user["_id"]),
            "name": user["name"],
            "phone": user.get("phone"),
            "email": user.get("email"),
            "role": user.get("role", "USER"),
            "is_active": user.get("is_active", True),
            "created_at": user.get("created_at")
        },
        "order_count": order_count,
        "recent_orders": [serialize_order(o).model_dump() for o in recent_orders]
    }
    return APIResponse(data=data)


@router.put(
    "/users/{id}/status",
    response_model=APIResponse[Dict[str, Any]],
    summary="Admin Activate or Deactivate User",
    description="Toggles user active state (ban/unban)."
)
async def admin_toggle_user_status(
    id: str,
    is_active: bool = Query(...),
    current_admin: Dict[str, Any] = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    oid = validate_object_id(id)
    res = await db.users.find_one_and_update(
        {"_id": oid},
        {"$set": {"is_active": is_active, "updated_at": datetime.utcnow()}},
        return_document=True
    )
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await log_audit_event(
        db, str(current_admin["_id"]), "USER_STATUS_CHANGED", "USER", id,
        new_value={"is_active": is_active}
    )
    return APIResponse(message=f"User {'activated' if is_active else 'deactivated'}", data={"id": id, "is_active": is_active})


# ---------------- COUPONS CRUD (ADMIN) ----------------

@router.post(
    "/coupons",
    response_model=APIResponse[CouponResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Admin Create Coupon",
    description="Creates promotional discount code (FIXED or PERCENTAGE)."
)
async def admin_create_coupon(
    req: CouponCreate,
    current_admin: Dict[str, Any] = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    code = req.code.strip().upper()
    exists = await db.coupons.find_one({"code": code})
    if exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Coupon code already exists")

    doc = req.model_dump()
    doc["code"] = code
    doc["used_count"] = 0
    doc["created_at"] = datetime.utcnow()
    res = await db.coupons.insert_one(doc)
    doc["id"] = str(res.inserted_id)
    return APIResponse(message="Coupon created", data=CouponResponse(**doc))


@router.put(
    "/coupons/{id}",
    response_model=APIResponse[CouponResponse],
    summary="Admin Update Coupon",
    description="Updates coupon rules or active status."
)
async def admin_update_coupon(
    id: str,
    req: CouponUpdate,
    current_admin: Dict[str, Any] = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    oid = validate_object_id(id)
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    res = await db.coupons.find_one_and_update({"_id": oid}, {"$set": updates}, return_document=True)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coupon not found")
    res["id"] = str(res["_id"])
    return APIResponse(message="Coupon updated", data=CouponResponse(**res))


@router.delete(
    "/coupons/{id}",
    response_model=APIResponse[Dict[str, str]],
    summary="Admin Delete Coupon",
    description="Deletes a promotional coupon."
)
async def admin_delete_coupon(
    id: str,
    current_admin: Dict[str, Any] = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    oid = validate_object_id(id)
    res = await db.coupons.delete_one({"_id": oid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coupon not found")
    return APIResponse(message="Coupon deleted", data={"id": id, "status": "deleted"})


# ---------------- BANNERS CRUD (ADMIN) ----------------

@router.post(
    "/banners",
    response_model=APIResponse[Dict[str, Any]],
    status_code=status.HTTP_201_CREATED,
    summary="Admin Create Banner",
    description="Adds a promotional home banner."
)
async def admin_create_banner(
    req: AdminBannerCreate,
    current_admin: Dict[str, Any] = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    doc = req.model_dump()
    doc["created_at"] = datetime.utcnow()
    res = await db.banners.insert_one(doc)
    doc["id"] = str(res.inserted_id)
    del doc["_id"]
    return APIResponse(message="Banner created", data=doc)


@router.put(
    "/banners/{id}",
    response_model=APIResponse[Dict[str, Any]],
    summary="Admin Update Banner",
    description="Updates a promotional banner."
)
async def admin_update_banner(
    id: str,
    req: AdminBannerCreate,
    current_admin: Dict[str, Any] = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    oid = validate_object_id(id)
    res = await db.banners.find_one_and_update({"_id": oid}, {"$set": req.model_dump()}, return_document=True)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Banner not found")
    res["id"] = str(res["_id"])
    del res["_id"]
    return APIResponse(message="Banner updated", data=res)


@router.delete(
    "/banners/{id}",
    response_model=APIResponse[Dict[str, str]],
    summary="Admin Delete Banner",
    description="Deletes a promotional banner."
)
async def admin_delete_banner(
    id: str,
    current_admin: Dict[str, Any] = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    oid = validate_object_id(id)
    res = await db.banners.delete_one({"_id": oid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Banner not found")
    return APIResponse(message="Banner deleted", data={"id": id, "status": "deleted"})


# ---------------- SETTINGS (ADMIN) ----------------

@router.put(
    "/settings",
    response_model=APIResponse[Dict[str, Any]],
    summary="Admin Update Store Settings",
    description="Updates operating hours, delivery fees, order acceptance toggle, and maintenance mode."
)
async def admin_update_settings(
    req: AdminStoreSettingsUpdate,
    current_admin: Dict[str, Any] = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    updates["updated_at"] = datetime.utcnow()
    updates["type"] = "store_config"

    await db.settings.update_one(
        {"type": "store_config"},
        {"$set": updates},
        upsert=True
    )
    saved = await db.settings.find_one({"type": "store_config"})
    saved["id"] = str(saved["_id"])
    del saved["_id"]
    return APIResponse(message="Store configuration updated", data=saved)


# ---------------- AUDIT LOGS (ADMIN) ----------------

@router.get(
    "/audit-logs",
    response_model=APIResponse[List[Dict[str, Any]]],
    summary="Admin View Audit Trail",
    description="Lists administrative modifications to products, prices, stock, users, and orders."
)
async def get_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    current_admin: Dict[str, Any] = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    cursor = db.audit_logs.find({}).sort("timestamp", -1).limit(limit)
    logs = await cursor.to_list(length=limit)
    for l in logs:
        l["id"] = str(l["_id"])
        del l["_id"]
    return APIResponse(data=logs)
