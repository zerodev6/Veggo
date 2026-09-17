from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ReviewInDB(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    product_id: str
    user_id: str
    user_name: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = ""
    order_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
