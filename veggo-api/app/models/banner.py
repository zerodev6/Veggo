from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class BannerInDB(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    title: str
    subtitle: Optional[str] = ""
    image: str
    product_ids: List[str] = []
    category_id: Optional[str] = None
    is_active: bool = True
    priority: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
