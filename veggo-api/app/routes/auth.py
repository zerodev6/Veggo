from typing import Any, Dict
from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_database
from app.schemas.auth import (
    GoogleAuthRequest,
    GoogleLinkRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenData,
    UserResponse,
)
from app.schemas.common import APIResponse
from app.services.auth_service import AuthService, get_current_user
from app.utils.security import create_access_token

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=APIResponse[TokenData],
    status_code=status.HTTP_201_CREATED,
    summary="Register Customer Account",
    description="Registers a new customer account using Name, Sri Lankan mobile phone, Email, and Password."
)
async def register(req: RegisterRequest, db: AsyncIOMotorDatabase = Depends(get_database)):
    data = await AuthService.register_user(db, req)
    return APIResponse(message="Account registered successfully", data=data)


@router.post(
    "/login",
    response_model=APIResponse[TokenData],
    summary="Customer / Staff Login",
    description="Authenticate with Email or Sri Lankan mobile number + Password. Returns Veggo JWT token."
)
async def login(req: LoginRequest, db: AsyncIOMotorDatabase = Depends(get_database)):
    data = await AuthService.authenticate_user(db, req)
    return APIResponse(message="Login successful", data=data)


@router.post(
    "/google",
    response_model=APIResponse[TokenData],
    summary="Google Sign-In",
    description="Authenticate with verified Google ID Token from Android / Web client."
)
async def google_auth(req: GoogleAuthRequest, db: AsyncIOMotorDatabase = Depends(get_database)):
    data = await AuthService.authenticate_google(db, req)
    return APIResponse(message="Google authentication successful", data=data)


@router.post(
    "/google/link",
    response_model=APIResponse[Dict[str, Any]],
    summary="Link Google Account",
    description="Links a Google account to the currently authenticated Veggo user."
)
async def link_google(
    req: GoogleLinkRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    res = await AuthService.link_google_account(db, current_user, req)
    return APIResponse(message=res["message"], data=res)


@router.post(
    "/google/unlink",
    response_model=APIResponse[Dict[str, Any]],
    summary="Unlink Google Account",
    description="Unlinks Google identity from the current user account if password login is enabled."
)
async def unlink_google(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    res = await AuthService.unlink_google_account(db, current_user)
    return APIResponse(message=res["message"], data=res)


@router.post(
    "/refresh",
    response_model=APIResponse[Dict[str, str]],
    summary="Refresh Session Token",
    description="Renews the active Veggo JWT token."
)
async def refresh_token(current_user: Dict[str, Any] = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    role = current_user.get("role", "USER")
    new_token = create_access_token({"sub": user_id, "role": role})
    return APIResponse(message="Token refreshed successfully", data={"access_token": new_token, "token_type": "bearer"})


@router.post(
    "/logout",
    response_model=APIResponse[Dict[str, str]],
    summary="User Logout",
    description="Logs out the authenticated user session."
)
async def logout(current_user: Dict[str, Any] = Depends(get_current_user)):
    return APIResponse(message="Logged out successfully", data={"status": "logged_out"})


@router.get(
    "/me",
    response_model=APIResponse[UserResponse],
    summary="Get Authenticated User",
    description="Retrieves profile information for current authenticated user."
)
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    user_resp = UserResponse(
        id=str(current_user["_id"]),
        name=current_user["name"],
        phone=current_user.get("phone"),
        email=current_user.get("email"),
        role=current_user.get("role", "USER"),
        auth_provider=current_user.get("auth_provider", "password"),
        profile_image=current_user.get("profile_image"),
        language=current_user.get("language", "en"),
        notification_enabled=current_user.get("notification_enabled", True),
        created_at=current_user.get("created_at")
    )
    return APIResponse(data=user_resp)
