from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AddressInDB(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    user_id: str
    name: str
    phone: str
    address_line: str
    city: str
    district: str
    province: str
    postal_code: Optional[str] = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    delivery_note: Optional[str] = ""
    is_default: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
