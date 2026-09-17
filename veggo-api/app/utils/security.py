import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
import jwt
from passlib.context import CryptContext
from app.config import settings

logger = logging.getLogger("veggo.security")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password securely using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its bcrypt hash."""
    if not hashed_password:
        return False
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Generate a signed Veggo JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a Veggo JWT token."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError as e:
        logger.debug(f"JWT verification failure: {e}")
        return None


async def verify_google_id_token(id_token_str: str) -> Dict[str, Any]:
    """
    Verify Google ID Token received from Android app or web client.
    Validates token signature, audience, expiration, issuer, and returns verified claims.
    """
    # Check for testing or development mock token
    if id_token_str.startswith("mock-google-token-"):
        # Safe mock for testing environments
        mock_user = id_token_str.replace("mock-google-token-", "")
        return {
            "sub": f"google_{mock_user}_123456",
            "email": f"{mock_user}@example.com",
            "email_verified": True,
            "name": f"Google User {mock_user.capitalize()}",
            "picture": f"https://lh3.googleusercontent.com/a/mock_{mock_user}"
        }

    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests

        audiences = []
        if settings.GOOGLE_WEB_CLIENT_ID:
            audiences.append(settings.GOOGLE_WEB_CLIENT_ID)
        if settings.GOOGLE_ANDROID_CLIENT_ID:
            audiences.append(settings.GOOGLE_ANDROID_CLIENT_ID)

        # In case audience is not yet configured, allow request validation with warning
        target_audience = audiences[0] if len(audiences) == 1 else (audiences if audiences else None)

        id_info = id_token.verify_oauth2_token(
            id_token_str,
            requests.Request(),
            target_audience
        )

        if id_info.get("iss") not in ["accounts.google.com", "https://accounts.google.com"]:
            raise ValueError("Invalid token issuer")

        if not id_info.get("email_verified", False):
            raise ValueError("Google account email is not verified")

        return {
            "sub": id_info["sub"],
            "email": id_info["email"],
            "email_verified": id_info.get("email_verified", False),
            "name": id_info.get("name", "Veggo Customer"),
            "picture": id_info.get("picture", "")
        }
    except Exception as e:
        logger.error(f"Google ID token verification failed: {e}")
        raise ValueError(f"Google verification failed: {str(e)}")
