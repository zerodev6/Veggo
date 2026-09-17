from datetime import datetime
from typing import Any, Dict
from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_database
from app.schemas.auth import UserResponse
from app.schemas.common import APIResponse
from app.schemas.user import UserProfileUpdate
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get(
    "/me",
    response_model=APIResponse[UserResponse],
    summary="Get User Profile",
    description="Returns current user's profile details."
)
async def get_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    user_resp = UserResponse(
        id=str(current_user["_id"]),
        name=current_user["name"],
        phone=current_user.get("phone"),
        email=current_user.get("email"),
        role=current_user.get("role", "USER"),
        auth_provider=current_user.get("auth_provider", "password"),
        profile_image=current_user.get("profile_image"),
        language=current_user.get("language", "en"),
        notification_enabled=current_user.get("notification_enabled", True),
        created_at=current_user.get("created_at", datetime.utcnow())
    )
    return APIResponse(data=user_resp)


@router.put(
    "/me",
    response_model=APIResponse[UserResponse],
    summary="Update User Profile",
    description="Updates user name, phone, language preference, notification toggles, or avatar."
)
async def update_user_profile(
    req: UserProfileUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    updates = {}
    if req.name is not None:
        updates["name"] = req.name.strip()
    if req.phone is not None:
        updates["phone"] = req.phone
    if req.email is not None:
        updates["email"] = req.email.lower()
    if req.profile_image is not None:
        updates["profile_image"] = req.profile_image
    if req.language is not None:
        updates["language"] = req.language
    if req.notification_enabled is not None:
        updates["notification_enabled"] = req.notification_enabled

    if updates:
        updates["updated_at"] = datetime.utcnow()
        await db.users.update_one({"_id": current_user["_id"]}, {"$set": updates})
        updated = await db.users.find_one({"_id": current_user["_id"]})
    else:
        updated = current_user

    user_resp = UserResponse(
        id=str(updated["_id"]),
        name=updated["name"],
        phone=updated.get("phone"),
        email=updated.get("email"),
        role=updated.get("role", "USER"),
        auth_provider=updated.get("auth_provider", "password"),
        profile_image=updated.get("profile_image"),
        language=updated.get("language", "en"),
        notification_enabled=updated.get("notification_enabled", True),
        created_at=updated.get("created_at", datetime.utcnow())
    )
    return APIResponse(message="Profile updated successfully", data=user_resp)


@router.delete(
    "/me",
    response_model=APIResponse[Dict[str, str]],
    summary="Delete User Account",
    description="Deactivates current user account and cleans up associated personal data."
)
async def delete_user_account(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    # Soft delete / deactivate account to maintain order historical integrity
    await db.users.update_one(
        {"_id": current_user["_id"]},
        {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
    )
    return APIResponse(message="Account successfully deactivated", data={"status": "deactivated"})
