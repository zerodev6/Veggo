from datetime import datetime
from typing import Any, Dict, List, Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_database
from app.models.order import OrderStatus
from app.routes.orders import serialize_order
from app.schemas.common import APIResponse
from app.schemas.order import OrderResponse
from app.services.auth_service import require_agent
from app.services.notification_service import notification_service
from app.utils.validators import validate_object_id

router = APIRouter(prefix="/api/agent", tags=["Delivery Agent"])


class AgentLocationUpdate(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class AgentOrderStatusUpdate(BaseModel):
    status: OrderStatus
    note: Optional[str] = None


@router.get(
    "/orders",
    response_model=APIResponse[List[OrderResponse]],
    summary="Get Assigned Orders for Agent",
    description="Returns orders assigned to the authenticated delivery agent."
)
async def get_agent_orders(
    current_agent: Dict[str, Any] = Depends(require_agent),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    agent_id = str(current_agent["_id"])
    cursor = db.orders.find({"delivery_agent_id": agent_id}).sort("created_at", -1)
    orders_raw = await cursor.to_list(length=50)
    return APIResponse(data=[serialize_order(o) for o in orders_raw])


@router.get(
    "/orders/{id}",
    response_model=APIResponse[OrderResponse],
    summary="Get Delivery Order Details",
    description="Returns full customer delivery address and order contents for assigned agent."
)
async def get_agent_order(
    id: str,
    current_agent: Dict[str, Any] = Depends(require_agent),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    oid = validate_object_id(id)
    agent_id = str(current_agent["_id"])
    order = await db.orders.find_one({"_id": oid, "delivery_agent_id": agent_id})

    if not order and current_agent.get("role") != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "message": "Order not assigned to this agent", "error_code": "ORDER_NOT_FOUND"}
        )
    if not order:
        order = await db.orders.find_one({"_id": oid})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    return APIResponse(data=serialize_order(order))


@router.post(
    "/orders/{id}/accept",
    response_model=APIResponse[OrderResponse],
    summary="Agent Accepts Delivery Assignment",
    description="Accepts delivery assignment and marks order as READY_FOR_PICKUP or OUT_FOR_DELIVERY."
)
async def accept_delivery(
    id: str,
    current_agent: Dict[str, Any] = Depends(require_agent),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    oid = validate_object_id(id)
    agent_id = str(current_agent["_id"])
    agent_name = current_agent.get("name", "Delivery Rider")

    order = await db.orders.find_one({"_id": oid})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if order.get("delivery_agent_id") and order.get("delivery_agent_id") != agent_id and current_agent.get("role") != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order is already assigned to another delivery agent"
        )

    now = datetime.utcnow()
    tracking_event = {
        "status": OrderStatus.READY_FOR_PICKUP.value,
        "message": f"Assigned to delivery agent {agent_name}. Preparing for dispatch.",
        "timestamp": now,
        "updated_by": f"AGENT_{agent_name}"
    }

    updated = await db.orders.find_one_and_update(
        {"_id": oid},
        {
            "$set": {
                "delivery_agent_id": agent_id,
                "delivery_agent_name": agent_name,
                "order_status": OrderStatus.READY_FOR_PICKUP.value,
                "updated_at": now
            },
            "$push": {"tracking": tracking_event}
        },
        return_document=True
    )

    await notification_service.create_notification(
        db=db,
        user_id=order["user_id"],
        title="Delivery Agent Assigned",
        message=f"{agent_name} has accepted your order delivery.",
        notification_type="AGENT_ASSIGNED",
        data={"order_id": id}
    )

    return APIResponse(message="Delivery accepted", data=serialize_order(updated))


@router.post(
    "/orders/{id}/status",
    response_model=APIResponse[OrderResponse],
    summary="Agent Updates Delivery Status",
    description="Agent transitions delivery (e.g. OUT_FOR_DELIVERY -> DELIVERED)."
)
async def update_delivery_status(
    id: str,
    req: AgentOrderStatusUpdate,
    current_agent: Dict[str, Any] = Depends(require_agent),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    oid = validate_object_id(id)
    agent_id = str(current_agent["_id"])
    agent_name = current_agent.get("name", "Rider")

    order = await db.orders.find_one({"_id": oid})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if order.get("delivery_agent_id") != agent_id and current_agent.get("role") != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized to update this order")

    # Allowed agent status updates: OUT_FOR_DELIVERY, DELIVERED
    if req.status not in [OrderStatus.OUT_FOR_DELIVERY, OrderStatus.DELIVERED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Agents can only update status to OUT_FOR_DELIVERY or DELIVERED"
        )

    now = datetime.utcnow()
    tracking_msg = req.note or (
        "Order is on the way to your address! 🛵" if req.status == OrderStatus.OUT_FOR_DELIVERY
        else "Order has been safely delivered to customer. Thank you for choosing Veggo! 🥬"
    )

    tracking_event = {
        "status": req.status.value,
        "message": tracking_msg,
        "timestamp": now,
        "updated_by": f"AGENT_{agent_name}"
    }

    set_dict = {
        "order_status": req.status.value,
        "updated_at": now
    }
    if req.status == OrderStatus.DELIVERED:
        set_dict["payment_status"] = "PAID"  # Auto mark COD as paid upon verified delivery

    updated = await db.orders.find_one_and_update(
        {"_id": oid},
        {
            "$set": set_dict,
            "$push": {"tracking": tracking_event}
        },
        return_document=True
    )

    await notification_service.create_notification(
        db=db,
        user_id=order["user_id"],
        title="Delivery Status Update",
        message=tracking_msg,
        notification_type=req.status.value,
        data={"order_id": id}
    )

    return APIResponse(message="Delivery status updated", data=serialize_order(updated))


@router.post(
    "/location",
    response_model=APIResponse[Dict[str, Any]],
    summary="Agent Transmits GPS Coordinates",
    description="Submits agent's current live location (latitude & longitude) for order dispatch tracking."
)
async def submit_agent_location(
    req: AgentLocationUpdate,
    current_agent: Dict[str, Any] = Depends(require_agent),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    agent_id = str(current_agent["_id"])
    now = datetime.utcnow()

    doc = {
        "agent_id": agent_id,
        "agent_name": current_agent.get("name"),
        "latitude": req.latitude,
        "longitude": req.longitude,
        "timestamp": now
    }

    # Store latest location
    await db.agent_locations.update_one(
        {"agent_id": agent_id},
        {"$set": doc},
        upsert=True
    )

    return APIResponse(message="Location recorded", data=doc)
