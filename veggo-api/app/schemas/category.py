from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    slug: Optional[str] = None
    image: Optional[str] = ""
    description: Optional[str] = ""
    is_active: bool = True
    display_order: int = 0


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    image: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None


class CategoryResponse(BaseModel):
    id: str
    name: str
    slug: str
    image: Optional[str] = ""
    description: Optional[str] = ""
    is_active: bool
    display_order: int
    created_at: datetime
