from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.product import UnitType


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    slug: Optional[str] = None
    description: str = Field(..., min_length=5)
    category_id: str
    images: List[str] = []
    unit_type: UnitType = UnitType.WEIGHT
    price_per_kg: Optional[float] = Field(None, ge=0)
    price_per_piece: Optional[float] = Field(None, ge=0)
    available_units: List[str] = ["100g", "250g", "500g", "750g", "1kg", "2kg"]
    stock: float = Field(..., ge=0, description="In kg if WEIGHT, or units/pieces")
    minimum_order: float = Field(100.0, ge=1)
    maximum_order: float = Field(10000.0, ge=1)
    is_available: bool = True
    is_featured: bool = False
    is_popular: bool = False


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[str] = None
    images: Optional[List[str]] = None
    unit_type: Optional[UnitType] = None
    price_per_kg: Optional[float] = Field(None, ge=0)
    price_per_piece: Optional[float] = Field(None, ge=0)
    available_units: Optional[List[str]] = None
    stock: Optional[float] = Field(None, ge=0)
    minimum_order: Optional[float] = None
    maximum_order: Optional[float] = None
    is_available: Optional[bool] = None
    is_featured: Optional[bool] = None
    is_popular: Optional[bool] = None


class ProductResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: str
    category_id: str
    category_name: Optional[str] = None
    images: List[str] = []
    unit_type: UnitType
    price_per_kg: Optional[float] = None
    price_per_piece: Optional[float] = None
    available_units: List[str] = []
    stock: float
    minimum_order: float
    maximum_order: float
    is_available: bool
    is_featured: bool
    is_popular: bool
    average_rating: float
    total_reviews: int
    created_at: datetime
    updated_at: datetime
