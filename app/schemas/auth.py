from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime
from app.models.enums import UserRole, AuthProvider

class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = True
    role: Optional[UserRole] = UserRole.STUDENT

class UserCreate(UserBase):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str
    role: UserRole = UserRole.STUDENT

    @validator("password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v

class UserUpdate(UserBase):
    password: Optional[str] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None

    @validator("password")
    def validate_password(cls, v):
        if v is not None:
            if len(v) < 8:
                raise ValueError("Password must be at least 8 characters long")
            if not any(c.isupper() for c in v):
                raise ValueError("Password must contain at least one uppercase letter")
            if not any(c.islower() for c in v):
                raise ValueError("Password must contain at least one lowercase letter")
            if not any(c.isdigit() for c in v):
                raise ValueError("Password must contain at least one number")
        return v

class User(UserBase):
    id: int
    email: EmailStr
    is_active: bool
    is_superuser: bool
    role: UserRole
    auth_provider: AuthProvider
    is_2fa_enabled: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]
    avatar_url: Optional[str]
    bio: Optional[str]
    phone_number: Optional[str]

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str
    requires_2fa: Optional[bool] = None
    temp_token: Optional[str] = None

class TokenPayload(BaseModel):
    sub: int
    exp: int
    type: str = "access"

class PasswordReset(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

    @validator("new_password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v

class TwoFactorSetup(BaseModel):
    secret: str
    provisioning_uri: str
    backup_codes: List[str]

class TwoFactorVerify(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)

class SocialLogin(BaseModel):
    provider: AuthProvider
    access_token: str
    id_token: Optional[str] = None 