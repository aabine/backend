from datetime import datetime, timedelta
import json
import pyotp
import secrets
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
)
from app.models.user import User, AuthProvider
from app.services.email_service import EmailService

class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.email_service = EmailService()
        
        # Initialize OAuth
        self.oauth = OAuth()
        self.oauth.register(
            name='google',
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            client_kwargs={'scope': 'openid email profile'}
        )
        self.oauth.register(
            name='microsoft',
            server_metadata_url='https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration',
            client_id=settings.MICROSOFT_CLIENT_ID,
            client_secret=settings.MICROSOFT_CLIENT_SECRET,
            client_kwargs={'scope': 'openid email profile'}
        )

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user with email and password."""
        user = self.db.query(User).filter(User.email == email).first()
        if not user or not verify_password(password, user.hashed_password):
            return None
        return user

    async def create_user(self, user_data: Dict[str, Any], auth_provider: AuthProvider = AuthProvider.LOCAL) -> User:
        """Create a new user."""
        # Check if user exists
        existing_user = self.db.query(User).filter(User.email == user_data["email"]).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Create user
        db_user = User(
            email=user_data["email"],
            full_name=user_data.get("full_name", ""),
            hashed_password=get_password_hash(user_data["password"]) if auth_provider == AuthProvider.LOCAL else None,
            auth_provider=auth_provider,
            social_id=user_data.get("social_id"),
            is_verified=auth_provider != AuthProvider.LOCAL,  # Auto-verify social auth users
        )

        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)

        # Send verification email for local users
        if auth_provider == AuthProvider.LOCAL:
            await self.send_verification_email(db_user)

        return db_user

    async def handle_social_auth(self, provider: str, token_response: Dict[str, Any]) -> Dict[str, Any]:
        """Handle social authentication response."""
        if provider not in ["google", "microsoft"]:
            raise HTTPException(status_code=400, detail="Invalid provider")

        oauth_client = getattr(self.oauth, provider)
        user_info = await oauth_client.parse_id_token(token_response)
        
        # Check if user exists
        user = self.db.query(User).filter(
            User.email == user_info["email"],
            User.auth_provider == getattr(AuthProvider, provider.upper())
        ).first()

        if not user:
            # Create new user
            user = await self.create_user({
                "email": user_info["email"],
                "full_name": user_info.get("name"),
                "social_id": user_info["sub"]
            }, auth_provider=getattr(AuthProvider, provider.upper()))

        # Update last login
        user.last_login = datetime.utcnow()
        self.db.commit()

        # Generate tokens
        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

    async def setup_2fa(self, user: User) -> Dict[str, str]:
        """Set up 2FA for a user."""
        if user.is_2fa_enabled:
            raise HTTPException(status_code=400, detail="2FA is already enabled")

        # Generate secret
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        
        # Generate backup codes
        backup_codes = [secrets.token_hex(4) for _ in range(10)]
        
        # Save to user
        user.twofa_secret = secret
        user.backup_codes = json.dumps(backup_codes)
        user.is_2fa_enabled = True
        
        self.db.commit()

        # Generate QR code provisioning URI
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name=settings.PROJECT_NAME
        )

        return {
            "secret": secret,
            "provisioning_uri": provisioning_uri,
            "backup_codes": backup_codes
        }

    async def verify_2fa(self, user: User, code: str) -> bool:
        """Verify 2FA code."""
        if not user.is_2fa_enabled:
            return True

        # Check if it's a backup code
        if user.backup_codes:
            backup_codes = json.loads(user.backup_codes)
            if code in backup_codes:
                # Remove used backup code
                backup_codes.remove(code)
                user.backup_codes = json.dumps(backup_codes)
                self.db.commit()
                return True

        # Verify TOTP code
        totp = pyotp.TOTP(user.twofa_secret)
        return totp.verify(code)

    async def initiate_password_reset(self, email: str) -> None:
        """Initiate password reset process."""
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            return  # Don't reveal if user exists

        # Generate token
        token = secrets.token_urlsafe(32)
        user.password_reset_token = token
        user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
        
        self.db.commit()

        # Send reset email
        await self.email_service.send_password_reset_email(user.email, token)

    async def reset_password(self, token: str, new_password: str) -> None:
        """Reset password using reset token."""
        user = self.db.query(User).filter(
            User.password_reset_token == token,
            User.password_reset_expires > datetime.utcnow()
        ).first()

        if not user:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")

        # Update password
        user.hashed_password = get_password_hash(new_password)
        user.password_reset_token = None
        user.password_reset_expires = None
        
        self.db.commit()

    async def send_verification_email(self, user: User) -> None:
        """Send email verification."""
        token = secrets.token_urlsafe(32)
        user.verification_token = token
        user.verification_expires = datetime.utcnow() + timedelta(hours=24)
        
        self.db.commit()

        await self.email_service.send_verification_email(user.email, token)

    async def verify_email(self, token: str) -> None:
        """Verify email using verification token."""
        user = self.db.query(User).filter(
            User.verification_token == token,
            User.verification_expires > datetime.utcnow()
        ).first()

        if not user:
            raise HTTPException(status_code=400, detail="Invalid or expired verification token")

        user.is_verified = True
        user.verification_token = None
        user.verification_expires = None
        
        self.db.commit()

    async def update_profile(self, user: User, profile_data: Dict[str, Any]) -> User:
        """Update user profile."""
        for field, value in profile_data.items():
            if hasattr(user, field) and field not in ["id", "email", "is_active", "is_superuser"]:
                setattr(user, field, value)
        
        self.db.commit()
        self.db.refresh(user)
        
        return user 