import logging
from datetime import datetime
from typing import Any, Dict, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger("veggo.notification")


class NotificationService:
    @staticmethod
    async def create_notification(
        db: AsyncIOMotorDatabase,
        user_id: str,
        title: str,
        message: str,
        notification_type: str = "ORDER_UPDATE",
        data: Optional[Dict[str, Any]] = None
    ):
        """Creates an in-app notification record and prepares for push dispatch."""
        try:
            doc = {
                "user_id": str(user_id),
                "title": title,
                "message": message,
                "type": notification_type,
                "is_read": False,
                "data": data or {},
                "created_at": datetime.utcnow()
            }
            await db.notifications.insert_one(doc)
            logger.info(f"Notification sent to user {user_id}: {title}")
        except Exception as e:
            logger.error(f"Failed to create notification: {e}")


notification_service = NotificationService()
