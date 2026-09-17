from datetime import datetime
from typing import Any, Dict, List
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_database
from app.models.order import OrderStatus
from app.schemas.common import APIResponse
from app.schemas.review import ReviewCreate, ReviewResponse
from app.services.auth_service import get_current_user
from app.utils.validators import validate_object_id

router = APIRouter(prefix="/api/products/{id}/reviews", tags=["Reviews"])


@router.get(
    "",
    response_model=APIResponse[List[ReviewResponse]],
    summary="Get Product Reviews",
    description="Lists all customer reviews and ratings for a product."
)
async def get_product_reviews(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    p_oid = validate_object_id(id)
    cursor = db.reviews.find({"product_id": id}).sort("created_at", -1).limit(50)
    revs = await cursor.to_list(length=50)

    data = [
        ReviewResponse(
            id=str(r["_id"]),
            product_id=r["product_id"],
            user_id=r["user_id"],
            user_name=r.get("user_name", "Customer"),
            rating=r["rating"],
            comment=r.get("comment", ""),
            created_at=r["created_at"]
        )
        for r in revs
    ]
    return APIResponse(data=data)


@router.post(
    "",
    response_model=APIResponse[ReviewResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Submit Product Review",
    description="Submits a 1-5 star review. Requires verified purchase history of the product."
)
async def create_product_review(
    id: str,
    req: ReviewCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    user_id = str(current_user["_id"])
    p_oid = validate_object_id(id)
    product = await db.products.find_one({"_id": p_oid})

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "message": "Product not found", "error_code": "PRODUCT_NOT_FOUND"}
        )

    # 1. Verify user actually purchased this product in a completed/placed order
    has_purchased = await db.orders.find_one({
        "user_id": user_id,
        "items.product_id": id,
        "order_status": {"$ne": OrderStatus.CANCELLED.value}
    })

    if not has_purchased and current_user.get("role") != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "message": "You can only review products you have purchased.", "error_code": "PURCHASE_REQUIRED"}
        )

    # 2. Check for existing review by this user
    existing_review = await db.reviews.find_one({"product_id": id, "user_id": user_id})
    if existing_review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "message": "You have already reviewed this product.", "error_code": "DUPLICATE_REVIEW"}
        )

    now = datetime.utcnow()
    doc = {
        "product_id": id,
        "user_id": user_id,
        "user_name": current_user.get("name", "Customer"),
        "rating": req.rating,
        "comment": req.comment or "",
        "order_id": str(has_purchased["_id"]) if has_purchased else None,
        "created_at": now
    }
    res = await db.reviews.insert_one(doc)
    doc["_id"] = res.inserted_id

    # 3. Recalculate product average rating
    pipeline = [
        {"$match": {"product_id": id}},
        {"$group": {"_id": "$product_id", "avg_rating": {"$avg": "$rating"}, "count": {"$sum": 1}}}
    ]
    agg_res = await db.reviews.aggregate(pipeline).to_list(length=1)
    if agg_res:
        new_avg = round(float(agg_res[0]["avg_rating"]), 1)
        total_revs = int(agg_res[0]["count"])
        await db.products.update_one(
            {"_id": p_oid},
            {"$set": {"average_rating": new_avg, "total_reviews": total_revs}}
        )

    return APIResponse(
        message="Review submitted successfully",
        data=ReviewResponse(
            id=str(doc["_id"]),
            product_id=id,
            user_id=user_id,
            user_name=doc["user_name"],
            rating=doc["rating"],
            comment=doc["comment"],
            created_at=now
        )
    )
