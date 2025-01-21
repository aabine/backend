from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from fastapi import HTTPException, Request
from app.models.models import (
    User, AuditLog, AuditActionType,
    UserRole, School
)
from app.schemas.admin import (
    AdminUserCreate, AdminUserUpdate, UserRoleUpdate,
    UserPermissionCheck, AdminSchoolCreate, AdminSchoolUpdate,
    AdminSchoolResponse, UserSuspension, UserDeletion,
    SchoolSuspension, SchoolDeletion
)
from app.core.security import get_password_hash
import logging
import json
import secrets

logger = logging.getLogger(__name__)

class AdminService:
    def __init__(self, db: Session):
        self.db = db

    async def create_audit_log(
        self,
        user_id: int,
        action: AuditActionType,
        entity_type: str,
        entity_id: int,
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None,
        request: Optional[Request] = None
    ) -> AuditLog:
        """Create an audit log entry."""
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None
        )
        self.db.add(audit_log)
        await self.db.commit()
        return audit_log

    async def get_audit_logs(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        user_id: Optional[int] = None,
        action: Optional[AuditActionType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        """Get audit logs with filters."""
        query = self.db.query(AuditLog)

        if entity_type:
            query = query.filter(AuditLog.entity_type == entity_type)
        if entity_id:
            query = query.filter(AuditLog.entity_id == entity_id)
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if action:
            query = query.filter(AuditLog.action == action)
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)

        return query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()

    # User Management Methods
    async def create_user(
        self,
        data: AdminUserCreate,
        admin_id: int,
        request: Optional[Request] = None
    ) -> User:
        """Create a new user."""
        # Check if email already exists
        if self.db.query(User).filter(User.email == data.email).first():
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # If school_id is provided, verify it exists
        if data.school_id:
            school = self.db.query(School).filter(School.id == data.school_id).first()
            if not school:
                raise HTTPException(status_code=404, detail="School not found")
        
        user = User(
            email=data.email,
            hashed_password=get_password_hash(data.password),
            full_name=data.full_name,
            role=data.role,
            school_id=data.school_id,
            is_active=data.is_active,
            permissions=data.permissions or {}
        )
        self.db.add(user)
        
        await self.create_audit_log(
            user_id=admin_id,
            action=AuditActionType.CREATE,
            entity_type="user",
            entity_id=user.id,
            new_values=data.dict(exclude={'password'}),
            request=request
        )
        
        await self.db.commit()
        return user

    async def update_user(
        self,
        user_id: int,
        data: AdminUserUpdate,
        admin_id: int,
        request: Optional[Request] = None
    ) -> User:
        """Update user details."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        old_values = {
            field: getattr(user, field)
            for field in data.dict(exclude_unset=True).keys()
        }

        # If updating email, check it's not already taken
        if data.email and data.email != user.email:
            if self.db.query(User).filter(User.email == data.email).first():
                raise HTTPException(status_code=400, detail="Email already registered")

        # If updating school_id, verify it exists
        if data.school_id:
            school = self.db.query(School).filter(School.id == data.school_id).first()
            if not school:
                raise HTTPException(status_code=404, detail="School not found")

        for field, value in data.dict(exclude_unset=True).items():
            setattr(user, field, value)

        await self.create_audit_log(
            user_id=admin_id,
            action=AuditActionType.UPDATE,
            entity_type="user",
            entity_id=user_id,
            old_values=old_values,
            new_values=data.dict(exclude_unset=True),
            request=request
        )

        await self.db.commit()
        return user

    async def update_user_role(
        self,
        user_id: int,
        data: UserRoleUpdate,
        admin_id: int,
        request: Optional[Request] = None
    ) -> User:
        """Update user role and permissions."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        old_values = {
            "role": user.role,
            "permissions": user.permissions
        }

        user.role = data.role
        if data.permissions:
            user.permissions = data.permissions

        await self.create_audit_log(
            user_id=admin_id,
            action=AuditActionType.ROLE_CHANGE,
            entity_type="user",
            entity_id=user_id,
            old_values=old_values,
            new_values={
                "role": data.role,
                "permissions": data.permissions
            },
            request=request
        )

        await self.db.commit()
        return user

    async def check_permission(
        self,
        data: UserPermissionCheck
    ) -> bool:
        """Check if a user has a specific permission."""
        user = self.db.query(User).filter(User.id == data.user_id).first()
        if not user:
            return False

        # Admins have all permissions
        if user.role == UserRole.ADMIN:
            return True

        # Check user's permissions
        permissions = user.permissions.get(data.resource_type, []) if user.permissions else []
        
        # Check specific resource permission
        if data.resource_id:
            resource_permissions = user.permissions.get(
                f"{data.resource_type}_{data.resource_id}",
                []
            ) if user.permissions else []
            permissions.extend(resource_permissions)

        return data.permission in permissions

    # School Management Methods
    async def create_school(
        self,
        data: AdminSchoolCreate,
        admin_id: int,
        request: Optional[Request] = None
    ) -> School:
        """Create a new school with admin settings."""
        school = School(
            name=data.name,
            description=data.description,
            subscription_type=data.subscription_type,
            max_users=data.max_users,
            features_enabled=data.features_enabled,
            contact_email=data.contact_email,
            contact_phone=data.contact_phone,
            address=data.address,
            settings=data.settings,
            configuration=data.configuration,
            api_key=secrets.token_urlsafe(32),
            subscription_expires_at=datetime.utcnow() + timedelta(days=data.subscription_duration_days)
        )
        self.db.add(school)
        
        await self.create_audit_log(
            user_id=admin_id,
            action=AuditActionType.CREATE,
            entity_type="school",
            entity_id=school.id,
            new_values=data.dict(),
            request=request
        )
        
        await self.db.commit()
        return school

    async def update_school(
        self,
        school_id: int,
        data: AdminSchoolUpdate,
        admin_id: int,
        request: Optional[Request] = None
    ) -> School:
        """Update school with admin privileges."""
        school = self.db.query(School).filter(School.id == school_id).first()
        if not school:
            raise HTTPException(status_code=404, detail="School not found")

        old_values = {
            field: getattr(school, field)
            for field in data.dict(exclude_unset=True).keys()
        }

        for field, value in data.dict(exclude_unset=True).items():
            setattr(school, field, value)

        await self.create_audit_log(
            user_id=admin_id,
            action=AuditActionType.UPDATE,
            entity_type="school",
            entity_id=school_id,
            old_values=old_values,
            new_values=data.dict(exclude_unset=True),
            request=request
        )

        await self.db.commit()
        return school

    async def get_school_details(
        self,
        school_id: int
    ) -> AdminSchoolResponse:
        """Get detailed school information including usage statistics."""
        school = self.db.query(School).filter(School.id == school_id).first()
        if not school:
            raise HTTPException(status_code=404, detail="School not found")

        # Get current users count
        current_users_count = self.db.query(func.count(User.id))\
            .filter(User.school_id == school_id)\
            .scalar()

        return AdminSchoolResponse(
            **school.__dict__,
            current_users_count=current_users_count
        )

    async def suspend_user(
        self,
        user_id: int,
        data: UserSuspension,
        admin_id: int,
        request: Optional[Request] = None
    ) -> User:
        """Suspend a user temporarily or indefinitely."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.role == UserRole.ADMIN:
            raise HTTPException(status_code=400, detail="Cannot suspend admin users")

        old_values = {
            "is_active": user.is_active,
            "suspended_until": getattr(user, "suspended_until", None)
        }

        user.is_active = False
        user.suspended_until = data.suspended_until

        await self.create_audit_log(
            user_id=admin_id,
            action=AuditActionType.UPDATE,
            entity_type="user",
            entity_id=user_id,
            old_values=old_values,
            new_values={
                "is_active": False,
                "suspended_until": data.suspended_until,
                "suspension_reason": data.reason
            },
            request=request
        )

        # TODO: If data.notify_user is True, send notification

        await self.db.commit()
        return user

    async def delete_user(
        self,
        user_id: int,
        data: UserDeletion,
        admin_id: int,
        request: Optional[Request] = None
    ) -> None:
        """Delete a user (soft delete by default)."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.role == UserRole.ADMIN:
            raise HTTPException(status_code=400, detail="Cannot delete admin users")

        if data.permanent:
            # Permanent deletion
            await self.create_audit_log(
                user_id=admin_id,
                action=AuditActionType.DELETE,
                entity_type="user",
                entity_id=user_id,
                old_values={"email": user.email, "role": user.role},
                new_values={"deletion_reason": data.reason},
                request=request
            )
            await self.db.delete(user)
        else:
            # Soft deletion
            old_values = {
                "is_active": user.is_active,
                "deleted_at": getattr(user, "deleted_at", None)
            }
            user.is_active = False
            user.deleted_at = datetime.utcnow()
            user.email = f"deleted_{user.id}_{user.email}"  # Preserve unique constraint

            await self.create_audit_log(
                user_id=admin_id,
                action=AuditActionType.DELETE,
                entity_type="user",
                entity_id=user_id,
                old_values=old_values,
                new_values={
                    "is_active": False,
                    "deleted_at": user.deleted_at,
                    "deletion_reason": data.reason
                },
                request=request
            )

        # TODO: If data.notify_user is True, send notification

        await self.db.commit()

    async def suspend_school(
        self,
        school_id: int,
        data: SchoolSuspension,
        admin_id: int,
        request: Optional[Request] = None
    ) -> School:
        """Suspend a school temporarily or indefinitely."""
        school = self.db.query(School).filter(School.id == school_id).first()
        if not school:
            raise HTTPException(status_code=404, detail="School not found")

        old_values = {
            "is_active": school.is_active,
            "suspended_until": getattr(school, "suspended_until", None)
        }

        school.is_active = False
        school.suspended_until = data.suspended_until
        school.allow_data_access = data.allow_data_access

        # If not allowing data access, deactivate all non-admin users
        if not data.allow_data_access:
            users_to_suspend = self.db.query(User).filter(
                User.school_id == school_id,
                User.role != UserRole.ADMIN
            ).all()
            for user in users_to_suspend:
                user.is_active = False
                user.suspended_until = data.suspended_until

        await self.create_audit_log(
            user_id=admin_id,
            action=AuditActionType.UPDATE,
            entity_type="school",
            entity_id=school_id,
            old_values=old_values,
            new_values={
                "is_active": False,
                "suspended_until": data.suspended_until,
                "suspension_reason": data.reason,
                "allow_data_access": data.allow_data_access
            },
            request=request
        )

        # TODO: If data.notify_users is True, send notifications

        await self.db.commit()
        return school

    async def delete_school(
        self,
        school_id: int,
        data: SchoolDeletion,
        admin_id: int,
        request: Optional[Request] = None
    ) -> None:
        """Delete a school and optionally its associated data."""
        school = self.db.query(School).filter(School.id == school_id).first()
        if not school:
            raise HTTPException(status_code=404, detail="School not found")

        if data.permanent:
            # Schedule permanent deletion after retention period
            school.is_active = False
            school.deleted_at = datetime.utcnow()
            school.permanent_deletion_date = datetime.utcnow() + timedelta(days=data.data_retention_days)
            
            # Deactivate all associated users
            users = self.db.query(User).filter(User.school_id == school_id).all()
            for user in users:
                user.is_active = False
                user.deleted_at = datetime.utcnow()
                if user.email:
                    user.email = f"deleted_{user.id}_{user.email}"

            await self.create_audit_log(
                user_id=admin_id,
                action=AuditActionType.DELETE,
                entity_type="school",
                entity_id=school_id,
                old_values={"name": school.name, "is_active": True},
                new_values={
                    "deletion_reason": data.reason,
                    "permanent_deletion_date": school.permanent_deletion_date
                },
                request=request
            )
        else:
            # Soft deletion
            school.is_active = False
            school.deleted_at = datetime.utcnow()
            
            # Deactivate all non-admin users
            users = self.db.query(User).filter(
                User.school_id == school_id,
                User.role != UserRole.ADMIN
            ).all()
            for user in users:
                user.is_active = False
                user.suspended_until = datetime.utcnow() + timedelta(days=365)  # 1 year suspension

            await self.create_audit_log(
                user_id=admin_id,
                action=AuditActionType.DELETE,
                entity_type="school",
                entity_id=school_id,
                old_values={"is_active": True},
                new_values={
                    "is_active": False,
                    "deleted_at": school.deleted_at,
                    "deletion_reason": data.reason
                },
                request=request
            )

        # TODO: If data.notify_users is True, send notifications

        await self.db.commit() 