from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CategoryInDB(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    name: str
    slug: str
    image: Optional[str] = ""
    description: Optional[str] = ""
    is_active: bool = True
    display_order: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
