from typing import Any, Dict
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_database
from app.routes.categories import serialize_category
from app.routes.products import serialize_product
from app.schemas.common import APIResponse

router = APIRouter(prefix="/api/home", tags=["Home"])


@router.get(
    "",
    response_model=APIResponse[Dict[str, Any]],
    summary="Home Screen Aggregation API",
    description="Aggregates banners, categories, featured products, popular products, new arrivals, and offers for the mobile client."
)
async def get_home_data(db: AsyncIOMotorDatabase = Depends(get_database)):
    # 1. Banners
    banner_cursor = db.banners.find({"is_active": True}).sort("priority", 1).limit(5)
    raw_banners = await banner_cursor.to_list(length=5)
    banners = [
        {
            "id": str(b["_id"]),
            "title": b.get("title"),
            "subtitle": b.get("subtitle", ""),
            "image": b.get("image", ""),
            "product_ids": b.get("product_ids", []),
            "category_id": b.get("category_id")
        }
        for b in raw_banners
    ]

    # 2. Categories
    cat_cursor = db.categories.find({"is_active": True}).sort("display_order", 1).limit(12)
    raw_cats = await cat_cursor.to_list(length=12)
    categories = [serialize_category(c).model_dump() for c in raw_cats]

    # 3. Featured Products
    feat_cursor = db.products.find({"is_featured": True, "is_available": True}).limit(8)
    raw_feat = await feat_cursor.to_list(length=8)
    featured = [serialize_product(p).model_dump() for p in raw_feat]

    # 4. Popular Products
    pop_cursor = db.products.find({"is_popular": True, "is_available": True}).limit(8)
    raw_pop = await pop_cursor.to_list(length=8)
    popular = [serialize_product(p).model_dump() for p in raw_pop]

    # 5. New Products
    new_cursor = db.products.find({"is_available": True}).sort("created_at", -1).limit(8)
    raw_new = await new_cursor.to_list(length=8)
    new_products = [serialize_product(p).model_dump() for p in raw_new]

    # 6. Active coupons / offers
    coupon_cursor = db.coupons.find({"is_active": True}).limit(5)
    raw_coupons = await coupon_cursor.to_list(length=5)
    offers = [
        {
            "code": c["code"],
            "discount_type": c.get("discount_type"),
            "discount_value": c.get("discount_value"),
            "minimum_order": c.get("minimum_order")
        }
        for c in raw_coupons
    ]

    # 7. Recommended (combining high ratings)
    rec_cursor = db.products.find({"is_available": True, "average_rating": {"$gte": 4.0}}).limit(6)
    raw_rec = await rec_cursor.to_list(length=6)
    recommended = [serialize_product(p).model_dump() for p in (raw_rec if raw_rec else raw_feat[:4])]

    return APIResponse(data={
        "banners": banners,
        "categories": categories,
        "featured_products": featured,
        "popular_products": popular,
        "new_products": new_products,
        "offers": offers,
        "recommended_products": recommended
    })
