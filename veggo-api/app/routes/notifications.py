from datetime import datetime
from typing import Any, Dict, List
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_database
from app.schemas.common import APIResponse
from app.services.auth_service import get_current_user
from app.utils.validators import validate_object_id

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.get(
    "",
    response_model=APIResponse[List[Dict[str, Any]]],
    summary="Get User Notifications",
    description="Lists in-app order alerts, dispatch status updates, and promotions."
)
async def get_notifications(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    user_id = str(current_user["_id"])
    cursor = db.notifications.find({"user_id": user_id}).sort("created_at", -1).limit(50)
    notifs = await cursor.to_list(length=50)

    for n in notifs:
        n["id"] = str(n["_id"])
        del n["_id"]

    return APIResponse(data=notifs)


@router.put(
    "/{id}/read",
    response_model=APIResponse[Dict[str, str]],
    summary="Mark Notification as Read",
    description="Marks a specific user notification as read."
)
async def mark_as_read(
    id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    oid = validate_object_id(id)
    user_id = str(current_user["_id"])

    res = await db.notifications.update_one(
        {"_id": oid, "user_id": user_id},
        {"$set": {"is_read": True, "updated_at": datetime.utcnow()}}
    )

    if res.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    return APIResponse(message="Notification marked as read", data={"id": id, "status": "read"})


@router.put(
    "/read-all",
    response_model=APIResponse[Dict[str, str]],
    summary="Mark All Notifications as Read",
    description="Marks all unread alerts for current user as read."
)
async def mark_all_read(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    user_id = str(current_user["_id"])
    await db.notifications.update_many(
        {"user_id": user_id, "is_read": False},
        {"$set": {"is_read": True, "updated_at": datetime.utcnow()}}
    )
    return APIResponse(message="All notifications marked as read", data={"status": "all_read"})
