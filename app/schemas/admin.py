from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.enums import AuditActionType, UserRole, SchoolSubscriptionType

class AuditLogBase(BaseModel):
    action: AuditActionType
    entity_type: str
    entity_id: int
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class AuditLog(AuditLogBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# User Management Schemas
class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole
    school_id: Optional[int] = None
    is_active: bool = True
    permissions: Optional[Dict[str, List[str]]] = None

    @validator('password')
    def password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

class AdminUserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    school_id: Optional[int] = None
    permissions: Optional[Dict[str, List[str]]] = None
    require_password_change: Optional[bool] = None

class UserRoleUpdate(BaseModel):
    role: UserRole
    permissions: Optional[Dict[str, List[str]]] = None

class UserPermissionCheck(BaseModel):
    user_id: int
    permission: str
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None

class UserSuspension(BaseModel):
    suspended_until: Optional[datetime] = None
    reason: str
    notify_user: bool = True

class UserDeletion(BaseModel):
    permanent: bool = False
    reason: str
    notify_user: bool = True

# School Management Schemas for Admin
class AdminSchoolCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    subscription_type: SchoolSubscriptionType
    max_users: int = Field(..., gt=0)
    features_enabled: Dict[str, bool] = {}
    contact_email: EmailStr
    contact_phone: Optional[str] = None
    address: Optional[Dict[str, str]] = None
    settings: Dict[str, Any] = {}
    configuration: Dict[str, Any] = {}
    subscription_duration_days: int = Field(365, gt=0)

class AdminSchoolUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    subscription_type: Optional[SchoolSubscriptionType] = None
    max_users: Optional[int] = Field(None, gt=0)
    features_enabled: Optional[Dict[str, bool]] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    address: Optional[Dict[str, str]] = None
    settings: Optional[Dict[str, Any]] = None
    configuration: Optional[Dict[str, Any]] = None
    subscription_expires_at: Optional[datetime] = None
    is_active: Optional[bool] = None

class SchoolSuspension(BaseModel):
    suspended_until: Optional[datetime] = None
    reason: str
    notify_users: bool = True
    allow_data_access: bool = False

class SchoolDeletion(BaseModel):
    permanent: bool = False
    reason: str
    notify_users: bool = True
    data_retention_days: int = Field(30, ge=0)

class AdminSchoolResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    subscription_type: SchoolSubscriptionType
    max_users: int
    current_users_count: int
    features_enabled: Dict[str, bool]
    contact_email: EmailStr
    contact_phone: Optional[str] = None
    address: Optional[Dict[str, str]] = None
    settings: Dict[str, Any]
    configuration: Dict[str, Any]
    api_key: str
    subscription_expires_at: datetime
    is_active: bool
    suspended_until: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True 