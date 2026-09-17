import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from bson import ObjectId
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_database
from app.models.user import AuthProvider, UserInDB, UserRole
from app.schemas.auth import (
    GoogleAuthRequest,
    GoogleLinkRequest,
    LoginRequest,
    RegisterRequest,
    UserResponse,
)
from app.utils.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_google_id_token,
    verify_password,
)

logger = logging.getLogger("veggo.auth_service")

security_bearer = HTTPBearer(auto_error=False)


class AuthService:
    @staticmethod
    async def register_user(db: AsyncIOMotorDatabase, req: RegisterRequest) -> Dict[str, Any]:
        """Registers a new Veggo customer with validated email, phone, and hashed password."""
        # Check duplicate email
        if await db.users.find_one({"email": req.email.lower()}):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "message": "An account with this email already exists", "error_code": "EMAIL_EXISTS"}
            )

        # Check duplicate phone
        if await db.users.find_one({"phone": req.phone}):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "message": "An account with this phone number already exists", "error_code": "PHONE_EXISTS"}
            )

        # Hash password securely
        pwd_hash = hash_password(req.password)

        new_user = {
            "name": req.name.strip(),
            "phone": req.phone,
            "email": req.email.lower(),
            "password_hash": pwd_hash,
            "role": UserRole.USER.value,
            "auth_provider": AuthProvider.PASSWORD.value,
            "google_id": None,
            "profile_image": "",
            "language": "en",
            "notification_enabled": True,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        result = await db.users.insert_one(new_user)
        user_id = str(result.inserted_id)

        # Create access token
        token = create_access_token({"sub": user_id, "role": UserRole.USER.value})

        user_resp = UserResponse(
            id=user_id,
            name=new_user["name"],
            phone=new_user["phone"],
            email=new_user["email"],
            role=UserRole.USER,
            auth_provider=AuthProvider.PASSWORD,
            profile_image=new_user["profile_image"],
            language=new_user["language"],
            notification_enabled=new_user["notification_enabled"],
            created_at=new_user["created_at"]
        )

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": user_resp.model_dump()
        }

    @staticmethod
    async def authenticate_user(db: AsyncIOMotorDatabase, req: LoginRequest) -> Dict[str, Any]:
        """Authenticates user via email OR phone number + password."""
        login_str = req.login.strip()
        is_email = "@" in login_str

        query = {"email": login_str.lower()} if is_email else {"phone": login_str}
        user = await db.users.find_one(query)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"success": False, "message": "Invalid email/phone or password", "error_code": "INVALID_CREDENTIALS"}
            )

        if not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"success": False, "message": "Account has been deactivated. Please contact support.", "error_code": "ACCOUNT_DEACTIVATED"}
            )

        pwd_hash = user.get("password_hash")
        if not pwd_hash or not verify_password(req.password, pwd_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"success": False, "message": "Invalid email/phone or password", "error_code": "INVALID_CREDENTIALS"}
            )

        user_id = str(user["_id"])
        token = create_access_token({"sub": user_id, "role": user.get("role", "USER")})

        user_resp = UserResponse(
            id=user_id,
            name=user["name"],
            phone=user.get("phone"),
            email=user.get("email"),
            role=UserRole(user.get("role", "USER")),
            auth_provider=AuthProvider(user.get("auth_provider", "password")),
            profile_image=user.get("profile_image"),
            language=user.get("language", "en"),
            notification_enabled=user.get("notification_enabled", True),
            created_at=user.get("created_at", datetime.utcnow())
        )

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": user_resp.model_dump()
        }

    @staticmethod
    async def authenticate_google(db: AsyncIOMotorDatabase, req: GoogleAuthRequest) -> Dict[str, Any]:
        """
        Authenticates via verified Google ID Token claims.
        Handles auto-account creation and identity linking.
        """
        claims = await verify_google_id_token(req.id_token)
        google_id = claims["sub"]
        email = claims.get("email", "").lower()
        name = claims.get("name", "Veggo Customer")
        picture = claims.get("picture", "")

        # 1. Find user by google_id
        user = await db.users.find_one({"google_id": google_id})

        if user:
            # Existing Google user
            user_id = str(user["_id"])
        else:
            # 2. Check if email matches existing account to safely link
            user = await db.users.find_one({"email": email}) if email else None
            if user:
                # Link Google identity to existing account
                await db.users.update_one(
                    {"_id": user["_id"]},
                    {
                        "$set": {
                            "google_id": google_id,
                            "auth_provider": AuthProvider.GOOGLE_PASSWORD.value if user.get("password_hash") else AuthProvider.GOOGLE.value,
                            "profile_image": user.get("profile_image") or picture,
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
                user_id = str(user["_id"])
            else:
                # 3. Create fresh user
                new_user = {
                    "name": name,
                    "phone": None,
                    "email": email,
                    "password_hash": None,
                    "role": UserRole.USER.value,
                    "auth_provider": AuthProvider.GOOGLE.value,
                    "google_id": google_id,
                    "profile_image": picture,
                    "language": "en",
                    "notification_enabled": True,
                    "is_active": True,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                res = await db.users.insert_one(new_user)
                user = new_user
                user_id = str(res.inserted_id)

        if not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"success": False, "message": "Account has been deactivated.", "error_code": "ACCOUNT_DEACTIVATED"}
            )

        token = create_access_token({"sub": user_id, "role": user.get("role", "USER")})

        user_resp = UserResponse(
            id=user_id,
            name=user.get("name", name),
            phone=user.get("phone"),
            email=user.get("email", email),
            role=UserRole(user.get("role", "USER")),
            auth_provider=AuthProvider(user.get("auth_provider", "google")),
            profile_image=user.get("profile_image") or picture,
            language=user.get("language", "en"),
            notification_enabled=user.get("notification_enabled", True),
            created_at=user.get("created_at", datetime.utcnow())
        )

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": user_resp.model_dump()
        }

    @staticmethod
    async def link_google_account(db: AsyncIOMotorDatabase, current_user: Dict[str, Any], req: GoogleLinkRequest) -> Dict[str, Any]:
        """Links Google identity to currently logged-in account."""
        claims = await verify_google_id_token(req.id_token)
        google_id = claims["sub"]

        # Check if already linked to another account
        existing_owner = await db.users.find_one({"google_id": google_id})
        if existing_owner and str(existing_owner["_id"]) != str(current_user["_id"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "message": "This Google account is already linked to another user.", "error_code": "GOOGLE_ALREADY_LINKED"}
            )

        await db.users.update_one(
            {"_id": current_user["_id"]},
            {
                "$set": {
                    "google_id": google_id,
                    "auth_provider": AuthProvider.GOOGLE_PASSWORD.value if current_user.get("password_hash") else AuthProvider.GOOGLE.value,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        return {"success": True, "message": "Google account linked successfully"}

    @staticmethod
    async def unlink_google_account(db: AsyncIOMotorDatabase, current_user: Dict[str, Any]) -> Dict[str, Any]:
        """Safely unlinks Google account if password authentication exists."""
        if not current_user.get("password_hash"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "message": "Cannot unlink Google because you do not have a password set. Set a password first.",
                    "error_code": "CANNOT_UNLINK_ONLY_AUTH_METHOD"
                }
            )

        await db.users.update_one(
            {"_id": current_user["_id"]},
            {
                "$set": {
                    "google_id": None,
                    "auth_provider": AuthProvider.PASSWORD.value,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        return {"success": True, "message": "Google account unlinked successfully"}


async def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> Dict[str, Any]:
    """Dependency that extracts and validates the authenticated user from the Bearer token."""
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "message": "Authentication required. Please provide a Bearer token.", "error_code": "UNAUTHORIZED"}
        )

    payload = decode_access_token(auth.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "message": "Invalid or expired session token.", "error_code": "TOKEN_INVALID"}
        )

    user_id = payload["sub"]
    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "message": "Malformed token subject.", "error_code": "TOKEN_INVALID"}
        )

    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "message": "User account not found.", "error_code": "USER_NOT_FOUND"}
        )

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"success": False, "message": "Account has been suspended.", "error_code": "ACCOUNT_DISABLED"}
        )

    return user


def require_role(allowed_roles: List[UserRole]):
    """Role-based authorization dependency generator."""
    async def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = current_user.get("role", "USER")
        if user_role not in [r.value for r in allowed_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"success": False, "message": f"Access denied. Requires one of {allowed_roles}", "error_code": "FORBIDDEN"}
            )
        return current_user
    return role_checker


require_admin = require_role([UserRole.ADMIN])
require_agent = require_role([UserRole.DELIVERY_AGENT, UserRole.ADMIN])
require_customer_or_admin = require_role([UserRole.USER, UserRole.ADMIN])
