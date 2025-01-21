from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from app.models.enums import SchoolSubscriptionType

class SchoolBase(BaseModel):
    name: str
    description: Optional[str] = None
    subscription_type: Optional[SchoolSubscriptionType] = None
    max_users: Optional[int] = None
    features_enabled: Optional[Dict[str, bool]] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    address: Optional[Dict[str, str]] = None
    settings: Optional[Dict[str, Any]] = None
    configuration: Optional[Dict[str, Any]] = None

class SchoolCreate(SchoolBase):
    name: str
    subscription_type: SchoolSubscriptionType
    contact_email: EmailStr

class SchoolUpdate(SchoolBase):
    pass

class School(SchoolBase):
    id: int
    api_key: str
    subscription_expires_at: Optional[str] = None

    class Config:
        from_attributes = True

class SchoolAPIKey(BaseModel):
    api_key: str 