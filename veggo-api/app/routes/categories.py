from datetime import datetime
from typing import Any, Dict, List, Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_database
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from app.schemas.common import APIResponse
from app.services.auth_service import require_admin
from app.utils.validators import validate_object_id

router = APIRouter(prefix="/api/categories", tags=["Categories"])


def serialize_category(doc: Dict[str, Any]) -> CategoryResponse:
    return CategoryResponse(
        id=str(doc["_id"]),
        name=doc["name"],
        slug=doc.get("slug", doc["name"].lower().replace(" ", "-")),
        image=doc.get("image", ""),
        description=doc.get("description", ""),
        is_active=doc.get("is_active", True),
        display_order=doc.get("display_order", 0),
        created_at=doc.get("created_at", datetime.utcnow())
    )


@router.get(
    "",
    response_model=APIResponse[List[CategoryResponse]],
    summary="Get All Active Categories",
    description="Lists all active product categories for browsing."
)
async def get_categories(
    all: bool = False,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    query = {} if all else {"is_active": True}
    cursor = db.categories.find(query).sort("display_order", 1)
    cats = await cursor.to_list(length=100)
    return APIResponse(data=[serialize_category(c) for c in cats])


@router.get(
    "/{id}",
    response_model=APIResponse[CategoryResponse],
    summary="Get Category by ID",
    description="Retrieves a single category by ObjectId or slug."
)
async def get_category(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    if ObjectId.is_valid(id):
        cat = await db.categories.find_one({"_id": ObjectId(id)})
    else:
        cat = await db.categories.find_one({"slug": id.lower()})

    if not cat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "message": "Category not found", "error_code": "CATEGORY_NOT_FOUND"}
        )
    return APIResponse(data=serialize_category(cat))


@router.post(
    "",
    response_model=APIResponse[CategoryResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Category (Admin)",
    description="Admin creates a new grocery category."
)
async def create_category(
    req: CategoryCreate,
    current_user: Dict[str, Any] = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    slug = req.slug or req.name.lower().replace(" ", "-")
    existing = await db.categories.find_one({"slug": slug})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "message": "Category slug already exists", "error_code": "SLUG_EXISTS"}
        )

    doc = {
        "name": req.name.strip(),
        "slug": slug,
        "image": req.image or "",
        "description": req.description or "",
        "is_active": req.is_active,
        "display_order": req.display_order,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    res = await db.categories.insert_one(doc)
    doc["_id"] = res.inserted_id
    return APIResponse(message="Category created successfully", data=serialize_category(doc))


@router.put(
    "/{id}",
    response_model=APIResponse[CategoryResponse],
    summary="Update Category (Admin)",
    description="Admin updates an existing category."
)
async def update_category(
    id: str,
    req: CategoryUpdate,
    current_user: Dict[str, Any] = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    oid = validate_object_id(id)
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        cat = await db.categories.find_one({"_id": oid})
        return APIResponse(data=serialize_category(cat))

    updates["updated_at"] = datetime.utcnow()
    res = await db.categories.find_one_and_update(
        {"_id": oid},
        {"$set": updates},
        return_document=True
    )
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "message": "Category not found", "error_code": "CATEGORY_NOT_FOUND"}
        )
    return APIResponse(message="Category updated successfully", data=serialize_category(res))


@router.delete(
    "/{id}",
    response_model=APIResponse[Dict[str, str]],
    summary="Delete Category (Admin)",
    description="Admin deletes a category."
)
async def delete_category(
    id: str,
    current_user: Dict[str, Any] = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    oid = validate_object_id(id)
    res = await db.categories.delete_one({"_id": oid})
    if res.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "message": "Category not found", "error_code": "CATEGORY_NOT_FOUND"}
        )
    return APIResponse(message="Category deleted successfully", data={"id": id, "status": "deleted"})
