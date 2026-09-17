from datetime import datetime
from typing import Any, Dict, List, Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.config import settings
from app.database import get_database
from app.schemas.common import APIResponse
from app.services.auth_service import require_admin
from app.services.delivery_service import delivery_service
from app.utils.validators import validate_object_id

router = APIRouter(tags=["Delivery & Store Configuration"])


class ServiceAreaCreate(BaseModel):
    name: str = Field(..., min_length=2)
    district: str = Field(..., min_length=2)
    delivery_fee: float = Field(..., ge=0)
    minimum_order: float = Field(500.0, ge=0)
    is_active: bool = True


class ServiceAreaUpdate(BaseModel):
    name: Optional[str] = None
    district: Optional[str] = None
    delivery_fee: Optional[float] = None
    minimum_order: Optional[float] = None
    is_active: Optional[bool] = None


@router.get(
    "/api/delivery/estimate",
    response_model=APIResponse[Dict[str, Any]],
    summary="Estimate Delivery Fee",
    description="Calculates delivery fee based on order subtotal, coordinates, district, and configured service areas."
)
async def estimate_delivery(
    subtotal: float = Query(..., ge=0),
    latitude: Optional[float] = Query(None, ge=-90, le=90),
    longitude: Optional[float] = Query(None, ge=-180, le=180),
    district: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    est = await delivery_service.estimate_delivery_fee(
        db=db,
        subtotal=subtotal,
        latitude=latitude,
        longitude=longitude,
        district=district,
        city=city
    )
    return APIResponse(data=est)


@router.get(
    "/api/store/status",
    response_model=APIResponse[Dict[str, Any]],
    summary="Get Store Operating Status",
    description="Checks whether Veggo is accepting orders, opening/closing hours, and maintenance flags."
)
async def get_store_status(db: AsyncIOMotorDatabase = Depends(get_database)):
    # Check if admin overrides exist in settings collection
    custom_settings = await db.settings.find_one({"type": "store_config"})
    
    is_accepting = settings.ORDER_ACCEPTANCE_ENABLED
    is_maint = settings.MAINTENANCE_MODE
    open_time = settings.OPENING_TIME
    close_time = settings.CLOSING_TIME

    if custom_settings:
        is_accepting = custom_settings.get("order_acceptance_enabled", is_accepting)
        is_maint = custom_settings.get("maintenance_mode", is_maint)
        open_time = custom_settings.get("opening_time", open_time)
        close_time = custom_settings.get("closing_time", close_time)

    is_open = is_accepting and not is_maint
    msg = "We are accepting orders across Sri Lanka 🇱🇰" if is_open else "We are temporarily closed for maintenance."

    return APIResponse(data={
        "is_open": is_open,
        "message": msg,
        "opening_time": open_time,
        "closing_time": close_time,
        "maintenance_mode": is_maint
    })


@router.get(
    "/api/settings",
    response_model=APIResponse[Dict[str, Any]],
    summary="Get Store Public Settings",
    description="Returns public store parameters such as currency, base delivery fee, and thresholds."
)
async def get_public_settings(db: AsyncIOMotorDatabase = Depends(get_database)):
    custom = await db.settings.find_one({"type": "store_config"}) or {}
    return APIResponse(data={
        "store_name": custom.get("store_name", settings.STORE_NAME),
        "currency": custom.get("currency", settings.CURRENCY),
        "store_phone": custom.get("store_phone", settings.STORE_PHONE),
        "store_email": custom.get("store_email", settings.STORE_EMAIL),
        "store_address": custom.get("store_address", settings.STORE_ADDRESS),
        "base_delivery_fee": custom.get("base_delivery_fee", settings.BASE_DELIVERY_FEE),
        "free_delivery_threshold": custom.get("free_delivery_threshold", settings.FREE_DELIVERY_THRESHOLD),
        "per_km_delivery_fee": custom.get("per_km_delivery_fee", settings.PER_KM_DELIVERY_FEE),
        "max_delivery_distance_km": custom.get("max_delivery_distance_km", settings.MAX_DELIVERY_DISTANCE_KM),
    })


@router.get(
    "/api/service-areas",
    response_model=APIResponse[List[Dict[str, Any]]],
    summary="List Serviceable Delivery Areas",
    description="Lists regions, districts, and municipalities serviced by Veggo."
)
async def get_service_areas(db: AsyncIOMotorDatabase = Depends(get_database)):
    cursor = db.service_areas.find({"is_active": True})
    areas = await cursor.to_list(length=100)
    for a in areas:
        a["id"] = str(a["_id"])
        del a["_id"]
    return APIResponse(data=areas)


@router.post(
    "/api/service-areas",
    response_model=APIResponse[Dict[str, Any]],
    status_code=status.HTTP_201_CREATED,
    summary="Create Service Area (Admin)",
    description="Admin registers a new delivery zone or district."
)
async def create_service_area(
    req: ServiceAreaCreate,
    current_user: Dict[str, Any] = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    doc = req.model_dump()
    doc["created_at"] = datetime.utcnow()
    res = await db.service_areas.insert_one(doc)
    doc["id"] = str(res.inserted_id)
    if "_id" in doc:
        del doc["_id"]
    return APIResponse(message="Service area created", data=doc)


@router.put(
    "/api/service-areas/{id}",
    response_model=APIResponse[Dict[str, Any]],
    summary="Update Service Area (Admin)",
    description="Admin updates delivery rate or parameters of a service area."
)
async def update_service_area(
    id: str,
    req: ServiceAreaUpdate,
    current_user: Dict[str, Any] = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    oid = validate_object_id(id)
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    res = await db.service_areas.find_one_and_update(
        {"_id": oid},
        {"$set": updates},
        return_document=True
    )
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service area not found")
    res["id"] = str(res["_id"])
    del res["_id"]
    return APIResponse(message="Service area updated", data=res)


@router.delete(
    "/api/service-areas/{id}",
    response_model=APIResponse[Dict[str, str]],
    summary="Delete Service Area (Admin)",
    description="Admin removes a service area."
)
async def delete_service_area(
    id: str,
    current_user: Dict[str, Any] = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    oid = validate_object_id(id)
    res = await db.service_areas.delete_one({"_id": oid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service area not found")
    return APIResponse(message="Service area deleted", data={"id": id, "status": "deleted"})
