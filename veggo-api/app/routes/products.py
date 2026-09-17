from datetime import datetime
from typing import Any, Dict, List, Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_database
from app.models.product import UnitType
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.services.auth_service import require_admin
from app.services.inventory_service import inventory_service
from app.utils.pagination import build_paginated_response, parse_pagination
from app.utils.validators import validate_object_id

router = APIRouter(prefix="/api/products", tags=["Products"])


def serialize_product(doc: Dict[str, Any]) -> ProductResponse:
    return ProductResponse(
        id=str(doc["_id"]),
        name=doc["name"],
        slug=doc.get("slug", doc["name"].lower().replace(" ", "-")),
        description=doc.get("description", ""),
        category_id=str(doc.get("category_id", "")),
        category_name=doc.get("category_name"),
        images=doc.get("images", []),
        unit_type=UnitType(doc.get("unit_type", "WEIGHT")),
        price_per_kg=doc.get("price_per_kg"),
        price_per_piece=doc.get("price_per_piece"),
        available_units=doc.get("available_units", ["100g", "250g", "500g", "750g", "1kg", "2kg"]),
        stock=float(doc.get("stock", 0.0)),
        minimum_order=float(doc.get("minimum_order", 100.0)),
        maximum_order=float(doc.get("maximum_order", 10000.0)),
        is_available=doc.get("is_available", True),
        is_featured=doc.get("is_featured", False),
        is_popular=doc.get("is_popular", False),
        average_rating=float(doc.get("average_rating", 0.0)),
        total_reviews=int(doc.get("total_reviews", 0)),
        created_at=doc.get("created_at", datetime.utcnow()),
        updated_at=doc.get("updated_at", datetime.utcnow())
    )


@router.get(
    "",
    response_model=PaginatedResponse[ProductResponse],
    summary="List Products with Filtering & Sorting",
    description="Lists catalog products with category, price range, availability filters, and price/newest sorting."
)
async def get_products(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None, description="Category slug or ObjectId"),
    search: Optional[str] = Query(None, description="Search term across name/description"),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    available: Optional[bool] = Query(None),
    sort: Optional[str] = Query("newest", description="'price_asc', 'price_desc', 'newest', 'popular'"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    skip, limit, page = parse_pagination(page, limit)
    query: Dict[str, Any] = {}

    if available is not None:
        query["is_available"] = available

    if category:
        if ObjectId.is_valid(category):
            query["category_id"] = category
        else:
            cat = await db.categories.find_one({"slug": category.lower()})
            if cat:
                query["category_id"] = str(cat["_id"])
            else:
                query["category_id"] = category

    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]

    # Price range filter
    price_cond = {}
    if min_price is not None:
        price_cond["$gte"] = min_price
    if max_price is not None:
        price_cond["$lte"] = max_price
    if price_cond:
        query["$or"] = [
            {"price_per_kg": price_cond},
            {"price_per_piece": price_cond}
        ]

    # Sort options
    sort_criteria = [("created_at", -1)]
    if sort == "price_asc":
        sort_criteria = [("price_per_kg", 1), ("price_per_piece", 1)]
    elif sort == "price_desc":
        sort_criteria = [("price_per_kg", -1), ("price_per_piece", -1)]
    elif sort == "popular":
        sort_criteria = [("is_popular", -1), ("average_rating", -1)]

    total = await db.products.count_documents(query)
    cursor = db.products.find(query).sort(sort_criteria).skip(skip).limit(limit)
    raw_products = await cursor.to_list(length=limit)

    items = [serialize_product(p).model_dump() for p in raw_products]
    return build_paginated_response(items, total, page, limit)


@router.get(
    "/featured",
    response_model=APIResponse[List[ProductResponse]],
    summary="Get Featured Products",
    description="Retrieves spotlighted products curated for Sri Lankan shoppers."
)
async def get_featured_products(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    cursor = db.products.find({"is_featured": True, "is_available": True}).limit(limit)
    items = await cursor.to_list(length=limit)
    return APIResponse(data=[serialize_product(p) for p in items])


@router.get(
    "/popular",
    response_model=APIResponse[List[ProductResponse]],
    summary="Get Popular Products",
    description="Retrieves top trending and fast-selling vegetables and groceries."
)
async def get_popular_products(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    cursor = db.products.find({"is_popular": True, "is_available": True}).limit(limit)
    items = await cursor.to_list(length=limit)
    return APIResponse(data=[serialize_product(p) for p in items])


@router.get(
    "/{id}",
    response_model=APIResponse[ProductResponse],
    summary="Get Product by ID or Slug",
    description="Retrieves detailed product info including available weight increments (100g, 250g, 500g, 1kg) and stock."
)
async def get_product(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    if ObjectId.is_valid(id):
        product = await db.products.find_one({"_id": ObjectId(id)})
    else:
        product = await db.products.find_one({"slug": id.lower()})

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "message": "Product not found", "error_code": "PRODUCT_NOT_FOUND"}
        )
    return APIResponse(data=serialize_product(product))


@router.post(
    "",
    response_model=APIResponse[ProductResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Product (Admin)",
    description="Admin creates a new vegetable or grocery item with custom gram weights."
)
async def create_product(
    req: ProductCreate,
    current_user: Dict[str, Any] = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    slug = req.slug or req.name.lower().replace(" ", "-")
    existing = await db.products.find_one({"slug": slug})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "message": "A product with this slug already exists", "error_code": "SLUG_EXISTS"}
        )

    # Find category name
    cat_name = None
    if ObjectId.is_valid(req.category_id):
        cat = await db.categories.find_one({"_id": ObjectId(req.category_id)})
        if cat:
            cat_name = cat.get("name")

    doc = {
        "name": req.name.strip(),
        "slug": slug,
        "description": req.description,
        "category_id": req.category_id,
        "category_name": cat_name,
        "images": req.images,
        "unit_type": req.unit_type.value,
        "price_per_kg": req.price_per_kg,
        "price_per_piece": req.price_per_piece,
        "available_units": req.available_units,
        "stock": req.stock,
        "minimum_order": req.minimum_order,
        "maximum_order": req.maximum_order,
        "is_available": req.is_available,
        "is_featured": req.is_featured,
        "is_popular": req.is_popular,
        "average_rating": 0.0,
        "total_reviews": 0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    res = await db.products.insert_one(doc)
    doc["_id"] = res.inserted_id

    # Log initial price
    price = req.price_per_kg if req.unit_type == UnitType.WEIGHT else req.price_per_piece
    if price:
        await inventory_service.log_price_change(
            db=db,
            product_id=str(doc["_id"]),
            old_price=0.0,
            new_price=float(price),
            changed_by=str(current_user["_id"])
        )

    return APIResponse(message="Product created successfully", data=serialize_product(doc))


@router.put(
    "/{id}",
    response_model=APIResponse[ProductResponse],
    summary="Update Product (Admin)",
    description="Admin updates details, prices, or stock of a product."
)
async def update_product(
    id: str,
    req: ProductUpdate,
    current_user: Dict[str, Any] = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    oid = validate_object_id(id)
    old_product = await db.products.find_one({"_id": oid})
    if not old_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "message": "Product not found", "error_code": "PRODUCT_NOT_FOUND"}
        )

    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if "unit_type" in updates and updates["unit_type"] is not None:
        updates["unit_type"] = updates["unit_type"].value

    if updates:
        updates["updated_at"] = datetime.utcnow()
        res = await db.products.find_one_and_update(
            {"_id": oid},
            {"$set": updates},
            return_document=True
        )
    else:
        res = old_product

    # Check for price changes to record audit history
    if req.price_per_kg is not None and req.price_per_kg != old_product.get("price_per_kg"):
        await inventory_service.log_price_change(
            db, id, float(old_product.get("price_per_kg", 0)), float(req.price_per_kg), str(current_user["_id"])
        )
    elif req.price_per_piece is not None and req.price_per_piece != old_product.get("price_per_piece"):
        await inventory_service.log_price_change(
            db, id, float(old_product.get("price_per_piece", 0)), float(req.price_per_piece), str(current_user["_id"])
        )

    return APIResponse(message="Product updated successfully", data=serialize_product(res))


@router.delete(
    "/{id}",
    response_model=APIResponse[Dict[str, str]],
    summary="Delete Product (Admin)",
    description="Admin deletes a product from the catalog."
)
async def delete_product(
    id: str,
    current_user: Dict[str, Any] = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    oid = validate_object_id(id)
    res = await db.products.delete_one({"_id": oid})
    if res.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "message": "Product not found", "error_code": "PRODUCT_NOT_FOUND"}
        )
    return APIResponse(message="Product deleted successfully", data={"id": id, "status": "deleted"})
