import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.models.user import UserRole, AuthProvider


def clean_sl_phone(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return None
    cleaned = re.sub(r"[^\d+]", "", phone.strip())
    if cleaned.startswith("+94"):
        cleaned = "0" + cleaned[3:]
    elif cleaned.startswith("94"):
        cleaned = "0" + cleaned[2:]
    elif len(cleaned) == 9 and not cleaned.startswith("0"):
        cleaned = "0" + cleaned
    
    # Sri Lankan mobile format: 07XXXXXXXX (10 digits)
    if not re.match(r"^07[01245678]\d{7}$", cleaned):
        raise ValueError("Invalid Sri Lankan mobile phone number (e.g., 0771234567 or +94771234567)")
    return cleaned


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., description="Sri Lankan mobile phone number (07XXXXXXXX)")
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        return clean_sl_phone(v)


class LoginRequest(BaseModel):
    login: str = Field(..., description="Email address or Sri Lankan phone number")
    password: str = Field(..., min_length=1)


class GoogleAuthRequest(BaseModel):
    id_token: str = Field(..., min_length=10, description="Google ID token verified on backend")


class GoogleLinkRequest(BaseModel):
    id_token: str = Field(..., min_length=10)


class UserResponse(BaseModel):
    id: str
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    role: UserRole
    auth_provider: AuthProvider
    profile_image: Optional[str] = None
    language: str = "en"
    notification_enabled: bool = True
    created_at: datetime

    class Config:
        populate_by_name = True


class TokenData(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: Optional[str] = None
