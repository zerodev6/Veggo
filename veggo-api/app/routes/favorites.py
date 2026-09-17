from datetime import datetime
from typing import Any, Dict, List
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_database
from app.routes.products import serialize_product
from app.schemas.common import APIResponse
from app.schemas.product import ProductResponse
from app.services.auth_service import get_current_user
from app.utils.validators import validate_object_id

router = APIRouter(prefix="/api/favorites", tags=["Favorites"])


@router.get(
    "",
    response_model=APIResponse[List[ProductResponse]],
    summary="Get User Favorite Products",
    description="Retrieves the list of products bookmarked as favorites by current customer."
)
async def get_favorites(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    user_id = str(current_user["_id"])
    cursor = db.favorites.find({"user_id": user_id})
    favs = await cursor.to_list(length=100)
    product_ids = [ObjectId(f["product_id"]) for f in favs if ObjectId.is_valid(f["product_id"])]

    if not product_ids:
        return APIResponse(data=[])

    prod_cursor = db.products.find({"_id": {"$in": product_ids}, "is_available": True})
    products = await prod_cursor.to_list(length=100)
    return APIResponse(data=[serialize_product(p) for p in products])


@router.post(
    "/{product_id}",
    response_model=APIResponse[Dict[str, str]],
    summary="Add Product to Favorites",
    description="Adds a vegetable or grocery item to user's favorites list (idempotent)."
)
async def add_favorite(
    product_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    user_id = str(current_user["_id"])
    p_oid = validate_object_id(product_id)

    product = await db.products.find_one({"_id": p_oid})
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "message": "Product not found", "error_code": "PRODUCT_NOT_FOUND"}
        )

    # Upsert to prevent duplicates
    await db.favorites.update_one(
        {"user_id": user_id, "product_id": product_id},
        {"$setOnInsert": {"user_id": user_id, "product_id": product_id, "created_at": datetime.utcnow()}},
        upsert=True
    )
    return APIResponse(message="Added to favorites", data={"product_id": product_id, "status": "favorited"})


@router.delete(
    "/{product_id}",
    response_model=APIResponse[Dict[str, str]],
    summary="Remove Product from Favorites",
    description="Removes a product from customer's favorites."
)
async def remove_favorite(
    product_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    user_id = str(current_user["_id"])
    res = await db.favorites.delete_one({"user_id": user_id, "product_id": product_id})
    if res.deleted_count == 0:
        return APIResponse(message="Product was not in favorites", data={"product_id": product_id, "status": "not_found"})
    return APIResponse(message="Removed from favorites", data={"product_id": product_id, "status": "removed"})
