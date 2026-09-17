from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.models.user import UserRole
from app.schemas.auth import clean_sl_phone


class UserProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    profile_image: Optional[str] = None
    language: Optional[str] = Field(None, pattern="^(en|si|ta)$")
    notification_enabled: Optional[bool] = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        if v is not None:
            return clean_sl_phone(v)
        return v


class AdminUserUpdate(BaseModel):
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
