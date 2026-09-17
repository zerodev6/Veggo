from datetime import datetime
from typing import Any, Dict, List
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_database
from app.schemas.common import APIResponse

router = APIRouter(prefix="/api/banners", tags=["Banners & Promotions"])


@router.get(
    "",
    response_model=APIResponse[List[Dict[str, Any]]],
    summary="Get Active Promotional Banners",
    description="Retrieves promotional hero banners for home carousel."
)
async def get_banners(db: AsyncIOMotorDatabase = Depends(get_database)):
    cursor = db.banners.find({"is_active": True}).sort("priority", 1).limit(10)
    banners = await cursor.to_list(length=10)
    for b in banners:
        b["id"] = str(b["_id"])
        del b["_id"]
    return APIResponse(data=banners)
