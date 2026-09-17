from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class InventoryEventType(str, Enum):
    STOCK_ADDED = "STOCK_ADDED"
    ORDER_RESERVED = "ORDER_RESERVED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    STOCK_ADJUSTED = "STOCK_ADJUSTED"
    ORDER_RETURNED = "ORDER_RETURNED"


class InventoryLog(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    product_id: str
    event_type: InventoryEventType
    quantity_change: float
    previous_stock: float
    new_stock: float
    reference_id: Optional[str] = None  # e.g., order_id or user_id
    note: Optional[str] = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class PriceHistory(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    product_id: str
    old_price: float
    new_price: float
    changed_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
