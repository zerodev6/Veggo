from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"
    DELIVERY_AGENT = "DELIVERY_AGENT"


class AuthProvider(str, Enum):
    PASSWORD = "password"
    GOOGLE = "google"
    GOOGLE_PASSWORD = "google_password"


class UserInDB(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    name: str
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    password_hash: Optional[str] = None
    role: UserRole = UserRole.USER
    auth_provider: AuthProvider = AuthProvider.PASSWORD
    google_id: Optional[str] = None
    profile_image: Optional[str] = None
    language: str = "en"
    notification_enabled: bool = True
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
