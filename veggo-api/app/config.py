import os
from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # MongoDB
    MONGO_URI: str = Field(default="mongodb://localhost:27017")
    DATABASE_NAME: str = Field(default="veggo")

    # Security & JWT
    JWT_SECRET: str = Field(default="veggo_super_secret_jwt_key_sri_lanka_2026")
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440)

    # Google Authentication
    GOOGLE_WEB_CLIENT_ID: str = Field(default="")
    GOOGLE_ANDROID_CLIENT_ID: str = Field(default="")

    # Server & CORS
    ALLOWED_ORIGINS: Union[str, List[str]] = Field(default="*")
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)

    # Business & Store Defaults (Sri Lanka)
    STORE_NAME: str = Field(default="Veggo")
    CURRENCY: str = Field(default="LKR")
    STORE_PHONE: str = Field(default="+94771234567")
    STORE_EMAIL: str = Field(default="support@veggo.lk")
    STORE_ADDRESS: str = Field(default="No. 45, Nuwara Eliya Road, Kandy, Sri Lanka")

    # Delivery Configuration
    BASE_DELIVERY_FEE: float = Field(default=150.0)
    FREE_DELIVERY_THRESHOLD: float = Field(default=5000.0)
    PER_KM_DELIVERY_FEE: float = Field(default=50.0)
    MAX_DELIVERY_DISTANCE_KM: float = Field(default=25.0)

    # Store Hours & Status
    OPENING_TIME: str = Field(default="06:30")
    CLOSING_TIME: str = Field(default="21:00")
    ORDER_ACCEPTANCE_ENABLED: bool = Field(default=True)
    MAINTENANCE_MODE: bool = Field(default=False)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @field_validator("PORT", mode="before")
    @classmethod
    def parse_port(cls, v):
        if isinstance(v, str) and v.isdigit():
            return int(v)
        return v or 8000

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            if v == "*":
                return ["*"]
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


settings = Settings()
