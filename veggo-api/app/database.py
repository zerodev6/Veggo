import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, TEXT, IndexModel
from app.config import settings

logger = logging.getLogger("veggo.database")

class Database:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None

db_wrapper = Database()

async def get_database() -> AsyncIOMotorDatabase:
    """Dependency for obtaining database instance."""
    return db_wrapper.db

async def connect_to_mongo():
    """Initializes MongoDB connection and creates required indexes."""
    try:
        logger.info(f"Connecting to MongoDB at {settings.MONGO_URI} (db: {settings.DATABASE_NAME})...")
        db_wrapper.client = AsyncIOMotorClient(
            settings.MONGO_URI,
            serverSelectionTimeoutMS=5000
        )
        db_wrapper.db = db_wrapper.client[settings.DATABASE_NAME]
        
        # Test connection ping
        await db_wrapper.client.admin.command('ping')
        logger.info("Successfully connected to MongoDB!")
        
        # Create Indexes
        await create_indexes()
    except Exception as e:
        logger.warning(f"Could not connect to live MongoDB: {e}. (Will retry on queries or run with in-memory test driver if testing).")

async def close_mongo_connection():
    """Closes MongoDB connection on shutdown."""
    if db_wrapper.client:
        logger.info("Closing MongoDB connection...")
        db_wrapper.client.close()
        logger.info("MongoDB connection closed.")

async def create_indexes():
    """Creates required indexes across collections."""
    if db_wrapper.db is None:
        return
    try:
        db = db_wrapper.db
        
        # Users indexes
        await db.users.create_index([("email", ASCENDING)], unique=True, sparse=True)
        await db.users.create_index([("phone", ASCENDING)], unique=True, sparse=True)
        await db.users.create_index([("google_id", ASCENDING)], unique=True, sparse=True)
        
        # Products indexes
        await db.products.create_index([("slug", ASCENDING)], unique=True)
        await db.products.create_index([("name", TEXT), ("description", TEXT)])
        await db.products.create_index([("category_id", ASCENDING)])
        await db.products.create_index([("is_available", ASCENDING), ("is_featured", ASCENDING)])
        await db.products.create_index([("price_per_kg", ASCENDING)])
        
        # Categories indexes
        await db.categories.create_index([("slug", ASCENDING)], unique=True)
        await db.categories.create_index([("is_active", ASCENDING)])
        
        # Orders indexes
        await db.orders.create_index([("order_number", ASCENDING)], unique=True)
        await db.orders.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        await db.orders.create_index([("order_status", ASCENDING)])
        await db.orders.create_index([("delivery_agent_id", ASCENDING)])
        
        # Coupons index
        await db.coupons.create_index([("code", ASCENDING)], unique=True)
        
        # Reviews indexes
        await db.reviews.create_index([("product_id", ASCENDING)])
        await db.reviews.create_index([("user_id", ASCENDING), ("product_id", ASCENDING)], unique=True)
        
        # Notifications indexes
        await db.notifications.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        
        # Favorites indexes
        await db.favorites.create_index([("user_id", ASCENDING), ("product_id", ASCENDING)], unique=True)

        # Service areas
        await db.service_areas.create_index([("name", ASCENDING)], unique=True)
        
        # Audit logs
        await db.audit_logs.create_index([("timestamp", DESCENDING)])

        logger.info("MongoDB database indexes successfully verified and initialized.")
    except Exception as e:
        logger.error(f"Error creating database indexes: {e}")
