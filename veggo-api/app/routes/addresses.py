from datetime import datetime
from typing import Any, Dict, List
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_database
from app.schemas.address import AddressCreate, AddressResponse, AddressUpdate
from app.schemas.common import APIResponse
from app.services.auth_service import get_current_user
from app.utils.validators import validate_object_id

router = APIRouter(prefix="/api/addresses", tags=["Addresses"])


def serialize_address(doc: Dict[str, Any]) -> AddressResponse:
    return AddressResponse(
        id=str(doc["_id"]),
        user_id=str(doc["user_id"]),
        name=doc["name"],
        phone=doc["phone"],
        address_line=doc["address_line"],
        city=doc["city"],
        district=doc["district"],
        province=doc["province"],
        postal_code=doc.get("postal_code", ""),
        latitude=doc.get("latitude"),
        longitude=doc.get("longitude"),
        delivery_note=doc.get("delivery_note", ""),
        is_default=doc.get("is_default", False),
        created_at=doc.get("created_at", datetime.utcnow())
    )


@router.get(
    "",
    response_model=APIResponse[List[AddressResponse]],
    summary="List Customer Saved Addresses",
    description="Returns all saved Sri Lankan delivery addresses for current customer."
)
async def get_my_addresses(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    user_id = str(current_user["_id"])
    cursor = db.addresses.find({"user_id": user_id}).sort("is_default", -1)
    addresses = await cursor.to_list(length=20)
    return APIResponse(data=[serialize_address(a) for a in addresses])


@router.post(
    "",
    response_model=APIResponse[AddressResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Save New Delivery Address",
    description="Saves a new Sri Lankan delivery address with province, district, city, coordinates, and delivery notes."
)
async def create_address(
    req: AddressCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    user_id = str(current_user["_id"])

    # If setting this as default, unset previous default
    if req.is_default:
        await db.addresses.update_many({"user_id": user_id}, {"$set": {"is_default": False}})

    # Check if this is the user's first address
    count = await db.addresses.count_documents({"user_id": user_id})
    is_default = req.is_default or (count == 0)

    doc = {
        "user_id": user_id,
        "name": req.name.strip(),
        "phone": req.phone,
        "address_line": req.address_line.strip(),
        "city": req.city.strip(),
        "district": req.district.strip(),
        "province": req.province.strip(),
        "postal_code": req.postal_code or "",
        "latitude": req.latitude,
        "longitude": req.longitude,
        "delivery_note": req.delivery_note or "",
        "is_default": is_default,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    res = await db.addresses.insert_one(doc)
    doc["_id"] = res.inserted_id
    return APIResponse(message="Address saved successfully", data=serialize_address(doc))


@router.put(
    "/{id}",
    response_model=APIResponse[AddressResponse],
    summary="Update Delivery Address",
    description="Updates an existing delivery address."
)
async def update_address(
    id: str,
    req: AddressUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    oid = validate_object_id(id)
    user_id = str(current_user["_id"])

    if req.is_default:
        await db.addresses.update_many({"user_id": user_id}, {"$set": {"is_default": False}})

    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if updates:
        updates["updated_at"] = datetime.utcnow()
        res = await db.addresses.find_one_and_update(
            {"_id": oid, "user_id": user_id},
            {"$set": updates},
            return_document=True
        )
    else:
        res = await db.addresses.find_one({"_id": oid, "user_id": user_id})

    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "message": "Address not found", "error_code": "ADDRESS_NOT_FOUND"}
        )

    return APIResponse(message="Address updated", data=serialize_address(res))


@router.delete(
    "/{id}",
    response_model=APIResponse[Dict[str, str]],
    summary="Delete Delivery Address",
    description="Deletes a saved delivery address."
)
async def delete_address(
    id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    oid = validate_object_id(id)
    user_id = str(current_user["_id"])

    res = await db.addresses.delete_one({"_id": oid, "user_id": user_id})
    if res.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "message": "Address not found", "error_code": "ADDRESS_NOT_FOUND"}
        )

    return APIResponse(message="Address deleted", data={"id": id, "status": "deleted"})
