from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from app.schemas.auth import clean_sl_phone


class AddressCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., description="Sri Lankan mobile phone")
    address_line: str = Field(..., min_length=5, max_length=200)
    city: str = Field(..., min_length=2, max_length=100)
    district: str = Field(..., min_length=2, max_length=100)
    province: str = Field(..., min_length=2, max_length=100)
    postal_code: Optional[str] = ""
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    delivery_note: Optional[str] = ""
    is_default: bool = False

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        return clean_sl_phone(v)


class AddressUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address_line: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    province: Optional[str] = None
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    delivery_note: Optional[str] = None
    is_default: Optional[bool] = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        if v is not None:
            return clean_sl_phone(v)
        return v


class AddressResponse(BaseModel):
    id: str
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
    is_default: bool
    created_at: datetime
