from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class NotificationInDB(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    user_id: str
    title: str
    message: str
    type: str = "ORDER_UPDATE"  # ORDER_PLACED, ORDER_CONFIRMED, ORDER_OUT, ORDER_DELIVERED, PROMO
    is_read: bool = False
    data: Optional[Dict[str, Any]] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
