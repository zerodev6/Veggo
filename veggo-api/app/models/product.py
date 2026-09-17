from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class UnitType(str, Enum):
    WEIGHT = "WEIGHT"
    PIECE = "PIECE"
    PACK = "PACK"
    BUNDLE = "BUNDLE"


class ProductInDB(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    name: str
    slug: str
    description: str
    category_id: str
    category_name: Optional[str] = None
    images: List[str] = []
    unit_type: UnitType = UnitType.WEIGHT
    price_per_kg: Optional[float] = None
    price_per_piece: Optional[float] = None
    available_units: List[str] = ["100g", "250g", "500g", "750g", "1kg", "2kg"]
    stock: float = 0.0  # In kg if WEIGHT, or units/pieces
    minimum_order: float = 100.0  # In grams (e.g. 100g) or pieces
    maximum_order: float = 10000.0  # In grams (10kg) or pieces
    is_available: bool = True
    is_featured: bool = False
    is_popular: bool = False
    average_rating: float = 0.0
    total_reviews: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
