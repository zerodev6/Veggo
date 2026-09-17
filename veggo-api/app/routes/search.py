from typing import Any, Dict
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_database
from app.routes.categories import serialize_category
from app.routes.products import serialize_product
from app.schemas.common import APIResponse

router = APIRouter(prefix="/api/search", tags=["Search"])


@router.get(
    "",
    response_model=APIResponse[Dict[str, Any]],
    summary="Global Store Search",
    description="Full-text and regex search across product names, descriptions, and category matches."
)
async def search_store(
    q: str = Query(..., min_length=1, description="Search keyword, e.g., 'carrot' or 'nuwara eliya'"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    search_term = q.strip()
    regex_pattern = {"$regex": search_term, "$options": "i"}

    # Search categories
    cat_cursor = db.categories.find({
        "is_active": True,
        "$or": [
            {"name": regex_pattern},
            {"description": regex_pattern}
        ]
    }).limit(10)
    matching_categories = await cat_cursor.to_list(length=10)

    # Search products
    prod_cursor = db.products.find({
        "is_available": True,
        "$or": [
            {"name": regex_pattern},
            {"description": regex_pattern},
            {"category_name": regex_pattern}
        ]
    }).limit(30)
    matching_products = await prod_cursor.to_list(length=30)

    data = {
        "products": [serialize_product(p).model_dump() for p in matching_products],
        "categories": [serialize_category(c).model_dump() for c in matching_categories],
        "total": len(matching_products)
    }

    return APIResponse(data=data)
