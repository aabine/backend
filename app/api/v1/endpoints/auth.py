from datetime import datetime
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api import deps
from app.core.security import create_access_token, create_refresh_token
from app.schemas.auth import (
    Token, TokenPayload, UserCreate, UserUpdate,
    PasswordReset, PasswordResetConfirm, TwoFactorSetup
)
from app.services.auth_service import AuthService
from app.schemas.user import User  # Pydantic model for response serialization
from app.models.user import UserRole, AuthProvider  # Core enums

router = APIRouter()

@router.post("/login", response_model=Token)
async def login(
    db: Session = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """Login with username/password."""
    auth_service = AuthService(db)
    user = await auth_service.authenticate_user(form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not verified"
        )

    # Handle 2FA if enabled
    if user.is_2fa_enabled and not form_data.scopes:  # scopes used for 2FA code
        return {
            "requires_2fa": True,
            "temp_token": create_access_token(user.id, expires_delta=300)  # 5 min token
        }

    if user.is_2fa_enabled and not await auth_service.verify_2fa(user, form_data.scopes[0]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid 2FA code"
        )

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()

    return {
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
        "token_type": "bearer"
    }

@router.post("/signup", response_model=Token)
async def signup(
    *,
    db: Session = Depends(deps.get_db),
    user_in: UserCreate
) -> Any:
    """Create new user."""
    auth_service = AuthService(db)
    return await auth_service.create_user(user_in.dict(), AuthProvider.LOCAL)

@router.get("/login/{provider}")
async def social_login(
    provider: str,
    request: Request,
    db: Session = Depends(deps.get_db)
) -> Any:
    """Initialize social login."""
    auth_service = AuthService(db)
    if provider not in ["google", "microsoft"]:
        raise HTTPException(status_code=400, detail="Invalid provider")
    
    oauth_client = getattr(auth_service.oauth, provider)
    redirect_uri = request.url_for(f'auth_{provider}_callback')
    return await oauth_client.authorize_redirect(request, redirect_uri)

@router.get("/login/{provider}/callback")
async def social_callback(
    provider: str,
    request: Request,
    db: Session = Depends(deps.get_db)
) -> Any:
    """Handle social login callback."""
    auth_service = AuthService(db)
    oauth_client = getattr(auth_service.oauth, provider)
    token = await oauth_client.authorize_access_token(request)
    return await auth_service.handle_social_auth(provider, token)

@router.post("/2fa/setup", response_model=TwoFactorSetup)
async def setup_2fa(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """Set up 2FA for user."""
    auth_service = AuthService(db)
    return await auth_service.setup_2fa(current_user)

@router.post("/2fa/verify")
async def verify_2fa(
    *,
    db: Session = Depends(deps.get_db),
    code: str,
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """Verify 2FA code."""
    auth_service = AuthService(db)
    if not await auth_service.verify_2fa(current_user, code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid 2FA code"
        )
    return {"message": "2FA verified successfully"}

@router.post("/password-reset")
async def request_password_reset(
    email: str,
    db: Session = Depends(deps.get_db)
) -> Any:
    """Request password reset."""
    auth_service = AuthService(db)
    await auth_service.initiate_password_reset(email)
    return {"message": "If your email is registered, you will receive a password reset link"}

@router.post("/reset-password")
async def reset_password(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(deps.get_db)
) -> Any:
    """Reset password using reset token."""
    auth_service = AuthService(db)
    await auth_service.reset_password(reset_data.token, reset_data.new_password)
    return {"message": "Password reset successfully"}

@router.get("/verify-email")
async def verify_email(
    token: str,
    db: Session = Depends(deps.get_db)
) -> Any:
    """Verify email address."""
    auth_service = AuthService(db)
    await auth_service.verify_email(token)
    return {"message": "Email verified successfully"}

@router.put("/profile", response_model=UserUpdate)
async def update_profile(
    *,
    db: Session = Depends(deps.get_db),
    profile_data: UserUpdate,
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """Update user profile."""
    auth_service = AuthService(db)
    return await auth_service.update_profile(current_user, profile_data.dict(exclude_unset=True)) 