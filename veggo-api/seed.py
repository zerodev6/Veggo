import asyncio
import logging
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
from app.models.coupon import DiscountType
from app.models.product import UnitType
from app.models.user import AuthProvider, UserRole
from app.utils.security import hash_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("veggo.seed")


async def seed_database():
    logger.info(f"Connecting to MongoDB at {settings.MONGO_URI} (db: {settings.DATABASE_NAME})...")
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.DATABASE_NAME]

    now = datetime.utcnow()

    # 1. Seed Users (Admin, Delivery Agent, Customer)
    logger.info("Seeding Users...")
    users = [
        {
            "name": "Veggo Admin",
            "email": "admin@veggo.lk",
            "phone": "0771112233",
            "password_hash": hash_password("Admin@123456"),
            "role": UserRole.ADMIN.value,
            "auth_provider": AuthProvider.PASSWORD.value,
            "is_active": True,
            "profile_image": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200",
            "created_at": now,
            "updated_at": now
        },
        {
            "name": "Kamal Delivery Rider",
            "email": "agent@veggo.lk",
            "phone": "0774445566",
            "password_hash": hash_password("Agent@123456"),
            "role": UserRole.DELIVERY_AGENT.value,
            "auth_provider": AuthProvider.PASSWORD.value,
            "is_active": True,
            "profile_image": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200",
            "created_at": now,
            "updated_at": now
        },
        {
            "name": "Nimal Perera",
            "email": "customer@veggo.lk",
            "phone": "0778889900",
            "password_hash": hash_password("Customer@123"),
            "role": UserRole.USER.value,
            "auth_provider": AuthProvider.PASSWORD.value,
            "is_active": True,
            "profile_image": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=200",
            "created_at": now,
            "updated_at": now
        }
    ]

    for u in users:
        await db.users.update_one({"email": u["email"]}, {"$set": u}, upsert=True)
    logger.info("Users seeded: admin@veggo.lk / agent@veggo.lk / customer@veggo.lk")

    # 2. Seed Categories
    logger.info("Seeding Categories...")
    categories_data = [
        {"name": "Vegetables", "slug": "vegetables", "display_order": 1, "image": "https://images.unsplash.com/photo-1566385101042-1a0aa0c1268c?w=400", "description": "Farm-fresh high country and low country vegetables"},
        {"name": "Fruits", "slug": "fruits", "display_order": 2, "image": "https://images.unsplash.com/photo-1619566636858-adf3ef46400b?w=400", "description": "Naturally ripened sweet Sri Lankan tropical fruits"},
        {"name": "Leafy Vegetables", "slug": "leafy-vegetables", "display_order": 3, "image": "https://images.unsplash.com/photo-1576045057995-568f588f82fb?w=400", "description": "Gotukola, Mukunuwenna, Kankun and organic greens"},
        {"name": "Betel Leaves", "slug": "betel-leaves", "display_order": 4, "image": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400", "description": "Fresh premium Sinhala Bulath (betel leaves)"},
        {"name": "Rice", "slug": "rice", "display_order": 5, "image": "https://images.unsplash.com/photo-1586201375761-83865001e31c?w=400", "description": "Samba, Keeri Samba, Nadu, and Red Rice"},
        {"name": "Groceries", "slug": "groceries", "display_order": 6, "image": "https://images.unsplash.com/photo-1542838132-92c53300491e?w=400", "description": "Daily pantry essentials, spices, and pulses"},
        {"name": "Dairy", "slug": "dairy", "display_order": 7, "image": "https://images.unsplash.com/photo-1550583724-b2692b85b150?w=400", "description": "Fresh curd, milk, butter, and cheese"},
        {"name": "Eggs", "slug": "eggs", "display_order": 8, "image": "https://images.unsplash.com/photo-1582722872445-44dc5f7e3c8f?w=400", "description": "Farm brown and white eggs"}
    ]

    cat_id_map = {}
    for c in categories_data:
        c["is_active"] = True
        c["updated_at"] = now
        res = await db.categories.find_one_and_update(
            {"slug": c["slug"]},
            {"$set": c, "$setOnInsert": {"created_at": now}},
            upsert=True,
            return_document=True
        )
        cat_id_map[c["slug"]] = str(res["_id"])

    logger.info(f"Seeded {len(categories_data)} categories.")

    # 3. Seed Products with Custom Gram Weights
    logger.info("Seeding Products...")
    products_data = [
        {
            "name": "Carrot (Nuwara Eliya)",
            "slug": "carrot-nuwara-eliya",
            "description": "Crisp and sweet farm-fresh Nuwara Eliya carrots, harvest-fresh.",
            "category_slug": "vegetables",
            "images": ["https://images.unsplash.com/photo-1598170845058-32b9d6a5c317?w=600"],
            "unit_type": UnitType.WEIGHT.value,
            "price_per_kg": 450.0,
            "price_per_piece": None,
            "available_units": ["100g", "250g", "500g", "750g", "1kg", "2kg"],
            "stock": 150.0,
            "minimum_order": 100.0,
            "maximum_order": 10000.0,
            "is_available": True,
            "is_featured": True,
            "is_popular": True,
            "average_rating": 4.8,
            "total_reviews": 24
        },
        {
            "name": "Leeks",
            "slug": "leeks",
            "description": "Crispy highland tender leeks, perfect for curries and soups.",
            "category_slug": "vegetables",
            "images": ["https://images.unsplash.com/photo-1588879462569-80e9275e7a9b?w=600"],
            "unit_type": UnitType.WEIGHT.value,
            "price_per_kg": 380.0,
            "stock": 80.0,
            "minimum_order": 100.0,
            "maximum_order": 5000.0,
            "is_available": True,
            "is_featured": True,
            "average_rating": 4.6,
            "total_reviews": 12
        },
        {
            "name": "Green Beans (Bochi)",
            "slug": "green-beans",
            "description": "Tender stringless green beans handpicked daily.",
            "category_slug": "vegetables",
            "images": ["https://images.unsplash.com/photo-1559856977-90c74900a6f8?w=600"],
            "unit_type": UnitType.WEIGHT.value,
            "price_per_kg": 420.0,
            "stock": 95.0,
            "minimum_order": 100.0,
            "is_available": True,
            "is_featured": False,
            "is_popular": True,
            "average_rating": 4.7,
            "total_reviews": 18
        },
        {
            "name": "Ripe Tomato",
            "slug": "ripe-tomato",
            "description": "Juicy red salad and curry tomatoes grown in Dambulla.",
            "category_slug": "vegetables",
            "images": ["https://images.unsplash.com/photo-1592924357228-91a4daadcfea?w=600"],
            "unit_type": UnitType.WEIGHT.value,
            "price_per_kg": 320.0,
            "stock": 120.0,
            "minimum_order": 100.0,
            "is_available": True,
            "is_featured": True,
            "is_popular": True,
            "average_rating": 4.9,
            "total_reviews": 31
        },
        {
            "name": "Nuwara Eliya Potato",
            "slug": "nuwara-eliya-potato",
            "description": "Famous hill-country red soil table potatoes with rich buttery flavor.",
            "category_slug": "vegetables",
            "images": ["https://images.unsplash.com/photo-1518977676601-b53f82aba655?w=600"],
            "unit_type": UnitType.WEIGHT.value,
            "price_per_kg": 390.0,
            "stock": 200.0,
            "minimum_order": 250.0,
            "is_available": True,
            "is_featured": True,
            "is_popular": True,
            "average_rating": 4.8,
            "total_reviews": 19
        },
        {
            "name": "Cabbage",
            "slug": "cabbage",
            "description": "Fresh whole green cabbage heads.",
            "category_slug": "vegetables",
            "images": ["https://images.unsplash.com/photo-1594282486552-05b4d80fbb9f?w=600"],
            "unit_type": UnitType.WEIGHT.value,
            "price_per_kg": 240.0,
            "stock": 90.0,
            "minimum_order": 250.0,
            "is_available": True,
            "average_rating": 4.5,
            "total_reviews": 8
        },
        {
            "name": "Sinhala Betel Leaves (Bulath)",
            "slug": "sinhala-betel-leaves",
            "description": "Fresh traditional bundle of hand-selected betel leaves for functions and hospitality.",
            "category_slug": "betel-leaves",
            "images": ["https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=600"],
            "unit_type": UnitType.BUNDLE.value,
            "price_per_piece": 180.0,
            "available_units": ["1 bundle (40 leaves)", "2 bundles", "5 bundles"],
            "stock": 50.0,
            "minimum_order": 1.0,
            "maximum_order": 20.0,
            "is_available": True,
            "is_featured": True,
            "average_rating": 5.0,
            "total_reviews": 14
        },
        {
            "name": "Keeri Samba Rice (5kg Bag)",
            "slug": "keeri-samba-rice-5kg",
            "description": "Premium aged polished aromatic Keeri Samba rice.",
            "category_slug": "rice",
            "images": ["https://images.unsplash.com/photo-1586201375761-83865001e31c?w=600"],
            "unit_type": UnitType.PACK.value,
            "price_per_piece": 1350.0,
            "available_units": ["1 bag (5kg)", "2 bags (10kg)"],
            "stock": 40.0,
            "minimum_order": 1.0,
            "is_available": True,
            "is_featured": True,
            "average_rating": 4.9,
            "total_reviews": 27
        },
        {
            "name": "Farm Fresh Brown Eggs (Pack of 10)",
            "slug": "farm-fresh-brown-eggs-10",
            "description": "High-protein graded farm fresh eggs.",
            "category_slug": "eggs",
            "images": ["https://images.unsplash.com/photo-1582722872445-44dc5f7e3c8f?w=600"],
            "unit_type": UnitType.PACK.value,
            "price_per_piece": 420.0,
            "available_units": ["Pack of 10", "Pack of 30"],
            "stock": 60.0,
            "minimum_order": 1.0,
            "is_available": True,
            "is_popular": True,
            "average_rating": 4.8,
            "total_reviews": 15
        },
        {
            "name": "Ambewela Fresh Milk (1L)",
            "slug": "ambewela-fresh-milk-1l",
            "description": "100% pure pasteurized highland cow milk from Ambewela farms.",
            "category_slug": "dairy",
            "images": ["https://images.unsplash.com/photo-1550583724-b2692b85b150?w=600"],
            "unit_type": UnitType.PIECE.value,
            "price_per_piece": 480.0,
            "available_units": ["1 bottle (1L)", "2 bottles", "4 bottles"],
            "stock": 50.0,
            "minimum_order": 1.0,
            "is_available": True,
            "is_featured": True,
            "average_rating": 4.9,
            "total_reviews": 22
        }
    ]

    for p in products_data:
        cat_slug = p.pop("category_slug", "vegetables")
        p["category_id"] = cat_id_map.get(cat_slug, "")
        p["category_name"] = cat_slug.replace("-", " ").capitalize()
        p["updated_at"] = now

        await db.products.update_one(
            {"slug": p["slug"]},
            {"$set": p, "$setOnInsert": {"created_at": now}},
            upsert=True
        )

    logger.info(f"Seeded {len(products_data)} products.")

    # 4. Seed Coupons
    logger.info("Seeding Promotional Coupons...")
    coupons = [
        {
            "code": "VEGGO100",
            "discount_type": DiscountType.FIXED.value,
            "discount_value": 100.0,
            "minimum_order": 1000.0,
            "maximum_discount": 100.0,
            "usage_limit": 500,
            "used_count": 5,
            "expires_at": now + timedelta(days=60),
            "is_active": True,
            "created_at": now
        },
        {
            "code": "FRESH20",
            "discount_type": DiscountType.PERCENTAGE.value,
            "discount_value": 20.0,
            "minimum_order": 2000.0,
            "maximum_discount": 600.0,
            "usage_limit": 200,
            "used_count": 12,
            "expires_at": now + timedelta(days=30),
            "is_active": True,
            "created_at": now
        }
    ]
    for cp in coupons:
        await db.coupons.update_one({"code": cp["code"]}, {"$set": cp}, upsert=True)

    # 5. Seed Service Areas (Sri Lanka)
    logger.info("Seeding Service Areas...")
    areas = [
        {"name": "Nuwara Eliya Hub", "district": "Nuwara Eliya", "city": "Nuwara Eliya", "delivery_fee": 150.0, "minimum_order": 500.0, "is_active": True},
        {"name": "Kandy City", "district": "Kandy", "city": "Kandy", "delivery_fee": 200.0, "minimum_order": 750.0, "is_active": True},
        {"name": "Colombo Central", "district": "Colombo", "city": "Colombo", "delivery_fee": 250.0, "minimum_order": 1000.0, "is_active": True},
        {"name": "Galle Fort & Town", "district": "Galle", "city": "Galle", "delivery_fee": 220.0, "minimum_order": 800.0, "is_active": True}
    ]
    for a in areas:
        await db.service_areas.update_one({"name": a["name"]}, {"$set": a}, upsert=True)

    # 6. Seed Banners
    logger.info("Seeding Promotional Banners...")
    banners = [
        {
            "title": "Fresh From Nuwara Eliya Farms",
            "subtitle": "Harvested at dawn, delivered to your door in hours",
            "image": "https://images.unsplash.com/photo-1540420773420-3366772f4999?w=1200",
            "product_ids": [],
            "category_id": cat_id_map.get("vegetables"),
            "is_active": True,
            "priority": 1,
            "created_at": now
        },
        {
            "title": "Special 20% Off With Coupon FRESH20",
            "subtitle": "On all orders above Rs. 2,000 this week!",
            "image": "https://images.unsplash.com/photo-1610348725531-843dff563e2c?w=1200",
            "product_ids": [],
            "category_id": cat_id_map.get("fruits"),
            "is_active": True,
            "priority": 2,
            "created_at": now
        }
    ]
    for b in banners:
        await db.banners.update_one({"title": b["title"]}, {"$set": b}, upsert=True)

    logger.info("✅ Veggo Sri Lanka database successfully seeded!")
    client.close()


if __name__ == "__main__":
    asyncio.run(seed_database())
