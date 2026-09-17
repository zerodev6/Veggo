from datetime import datetime
from typing import Any, Dict, List, Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_database
from app.schemas.cart import CartItemAdd, CartItemResponse, CartItemUpdate, CartResponse
from app.schemas.common import APIResponse
from app.services.auth_service import get_current_user
from app.services.delivery_service import delivery_service
from app.services.pricing_service import pricing_service
from app.utils.validators import validate_object_id

router = APIRouter(prefix="/api/cart", tags=["Cart"])


async def recalculate_user_cart(db: AsyncIOMotorDatabase, user_id: str) -> Dict[str, Any]:
    """Helper to recalculate cart items, prices, and totals from fresh product state."""
    cart = await db.carts.find_one({"user_id": user_id})
    if not cart:
        cart = {
            "user_id": user_id,
            "items": [],
            "subtotal": 0.0,
            "estimated_delivery_fee": 150.0,
            "discount": 0.0,
            "coupon_code": None,
            "total": 0.0,
            "updated_at": datetime.utcnow()
        }
        await db.carts.insert_one(cart)
        return cart

    raw_items = cart.get("items", [])
    updated_items = []
    subtotal = 0.0

    for item in raw_items:
        p_id = item["product_id"]
        product = await db.products.find_one({"_id": ObjectId(p_id)})
        
        if not product:
            continue  # Product was deleted
            
        is_available = product.get("is_available", True)
        
        try:
            unit_price, line_price = pricing_service.calculate_line_item_price(
                unit_type=product.get("unit_type", "WEIGHT"),
                price_per_kg=product.get("price_per_kg"),
                price_per_piece=product.get("price_per_piece"),
                quantity=item["quantity"],
                unit=item["unit"]
            )
        except Exception:
            unit_price = item.get("unit_price", 0.0)
            line_price = 0.0

        if is_available:
            subtotal += line_price

        updated_items.append({
            "product_id": p_id,
            "product_name": product["name"],
            "product_image": product.get("images", [""])[0] if product.get("images") else "",
            "unit_type": product.get("unit_type", "WEIGHT"),
            "quantity": item["quantity"],
            "unit": item["unit"],
            "unit_price": unit_price,
            "calculated_price": line_price,
            "is_available": is_available,
            "added_at": item.get("added_at", datetime.utcnow())
        })

    subtotal = round(subtotal, 2)
    
    # Check coupon
    coupon_code = cart.get("coupon_code")
    discount = 0.0
    if coupon_code:
        valid, disc, _ = await pricing_service.validate_coupon(db, coupon_code, subtotal, user_id)
        if valid:
            discount = disc
        else:
            coupon_code = None

    # Delivery estimate
    deliv = await delivery_service.estimate_delivery_fee(db, subtotal)
    delivery_fee = float(deliv.get("delivery_fee", 150.0))
    total = round(max(0.0, (subtotal - discount) + delivery_fee), 2)

    now = datetime.utcnow()
    await db.carts.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "items": updated_items,
                "subtotal": subtotal,
                "estimated_delivery_fee": delivery_fee,
                "discount": discount,
                "coupon_code": coupon_code,
                "total": total,
                "updated_at": now
            }
        }
    )

    cart["items"] = updated_items
    cart["subtotal"] = subtotal
    cart["estimated_delivery_fee"] = delivery_fee
    cart["discount"] = discount
    cart["coupon_code"] = coupon_code
    cart["total"] = total
    return cart


@router.get(
    "",
    response_model=APIResponse[CartResponse],
    summary="Get User Cart",
    description="Retrieves current authenticated user's cart with updated prices and weights."
)
async def get_cart(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    cart = await recalculate_user_cart(db, str(current_user["_id"]))
    items = [CartItemResponse(**item) for item in cart.get("items", [])]
    data = CartResponse(
        items=items,
        items_count=len(items),
        subtotal=cart.get("subtotal", 0.0),
        estimated_delivery_fee=cart.get("estimated_delivery_fee", 150.0),
        discount=cart.get("discount", 0.0),
        coupon_code=cart.get("coupon_code"),
        total=cart.get("total", 0.0),
        currency="LKR"
    )
    return APIResponse(data=data)


@router.post(
    "/items",
    response_model=APIResponse[CartResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add Item to Cart",
    description="Adds a vegetable or grocery item with custom grams (e.g. 750g) or pieces. Price is computed on server."
)
async def add_item_to_cart(
    req: CartItemAdd,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    user_id = str(current_user["_id"])
    p_oid = validate_object_id(req.product_id)
    product = await db.products.find_one({"_id": p_oid})

    if not product or not product.get("is_available", True):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "message": "Product is unavailable or does not exist", "error_code": "PRODUCT_NOT_FOUND"}
        )

    # Server price verification
    unit_price, line_price = pricing_service.calculate_line_item_price(
        unit_type=product.get("unit_type", "WEIGHT"),
        price_per_kg=product.get("price_per_kg"),
        price_per_piece=product.get("price_per_piece"),
        quantity=req.quantity,
        unit=req.unit
    )

    cart = await db.carts.find_one({"user_id": user_id})
    if not cart:
        cart = {"user_id": user_id, "items": []}
        await db.carts.insert_one(cart)

    items = cart.get("items", [])
    found = False

    for item in items:
        if item["product_id"] == req.product_id and item["unit"].lower() == req.unit.lower():
            # Update quantity
            item["quantity"] += req.quantity
            _, updated_line = pricing_service.calculate_line_item_price(
                unit_type=product.get("unit_type", "WEIGHT"),
                price_per_kg=product.get("price_per_kg"),
                price_per_piece=product.get("price_per_piece"),
                quantity=item["quantity"],
                unit=item["unit"]
            )
            item["calculated_price"] = updated_line
            found = True
            break

    if not found:
        items.append({
            "product_id": req.product_id,
            "product_name": product["name"],
            "product_image": product.get("images", [""])[0] if product.get("images") else "",
            "unit_type": product.get("unit_type", "WEIGHT"),
            "quantity": req.quantity,
            "unit": req.unit,
            "unit_price": unit_price,
            "calculated_price": line_price,
            "is_available": True,
            "added_at": datetime.utcnow()
        })

    await db.carts.update_one({"user_id": user_id}, {"$set": {"items": items}})
    updated_cart = await recalculate_user_cart(db, user_id)

    resp_items = [CartItemResponse(**it) for it in updated_cart.get("items", [])]
    return APIResponse(
        message="Item added to cart",
        data=CartResponse(
            items=resp_items,
            items_count=len(resp_items),
            subtotal=updated_cart.get("subtotal", 0.0),
            estimated_delivery_fee=updated_cart.get("estimated_delivery_fee", 150.0),
            discount=updated_cart.get("discount", 0.0),
            coupon_code=updated_cart.get("coupon_code"),
            total=updated_cart.get("total", 0.0),
            currency="LKR"
        )
    )


@router.put(
    "/items/{product_id}",
    response_model=APIResponse[CartResponse],
    summary="Update Cart Item Quantity",
    description="Updates the quantity or unit for a product in the cart."
)
async def update_cart_item(
    product_id: str,
    req: CartItemUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    user_id = str(current_user["_id"])
    cart = await db.carts.find_one({"user_id": user_id})
    if not cart or not cart.get("items"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "message": "Cart is empty", "error_code": "ITEM_NOT_FOUND"}
        )

    items = cart.get("items", [])
    found = False

    for item in items:
        if item["product_id"] == product_id:
            item["quantity"] = req.quantity
            if req.unit:
                item["unit"] = req.unit
            found = True
            break

    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "message": "Item not found in cart", "error_code": "ITEM_NOT_FOUND"}
        )

    await db.carts.update_one({"user_id": user_id}, {"$set": {"items": items}})
    updated_cart = await recalculate_user_cart(db, user_id)
    resp_items = [CartItemResponse(**it) for it in updated_cart.get("items", [])]

    return APIResponse(
        message="Cart item updated",
        data=CartResponse(
            items=resp_items,
            items_count=len(resp_items),
            subtotal=updated_cart.get("subtotal", 0.0),
            estimated_delivery_fee=updated_cart.get("estimated_delivery_fee", 150.0),
            discount=updated_cart.get("discount", 0.0),
            coupon_code=updated_cart.get("coupon_code"),
            total=updated_cart.get("total", 0.0),
            currency="LKR"
        )
    )


@router.delete(
    "/items/{product_id}",
    response_model=APIResponse[CartResponse],
    summary="Remove Item from Cart",
    description="Removes a specific product from the cart."
)
async def remove_cart_item(
    product_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    user_id = str(current_user["_id"])
    await db.carts.update_one(
        {"user_id": user_id},
        {"$pull": {"items": {"product_id": product_id}}}
    )
    updated_cart = await recalculate_user_cart(db, user_id)
    resp_items = [CartItemResponse(**it) for it in updated_cart.get("items", [])]

    return APIResponse(
        message="Item removed from cart",
        data=CartResponse(
            items=resp_items,
            items_count=len(resp_items),
            subtotal=updated_cart.get("subtotal", 0.0),
            estimated_delivery_fee=updated_cart.get("estimated_delivery_fee", 150.0),
            discount=updated_cart.get("discount", 0.0),
            coupon_code=updated_cart.get("coupon_code"),
            total=updated_cart.get("total", 0.0),
            currency="LKR"
        )
    )


@router.delete(
    "",
    response_model=APIResponse[Dict[str, str]],
    summary="Clear Cart",
    description="Clears all items and coupons from user's active cart."
)
async def clear_cart(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    user_id = str(current_user["_id"])
    await db.carts.update_one(
        {"user_id": user_id},
        {"$set": {"items": [], "subtotal": 0.0, "discount": 0.0, "coupon_code": None, "total": 0.0, "updated_at": datetime.utcnow()}}
    )
    return APIResponse(message="Cart cleared successfully", data={"status": "cleared"})
