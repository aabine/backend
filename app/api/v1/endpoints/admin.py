from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.api import deps
from app.services.admin_service import AdminService
from app.schemas.admin import (
    AuditLog, UserRoleUpdate,
    UserPermissionCheck, AuditActionType,
    AdminUserCreate, AdminUserUpdate,
    AdminSchoolCreate, AdminSchoolUpdate,
    AdminSchoolResponse, UserSuspension,
    UserDeletion, SchoolSuspension,
    SchoolDeletion
)
from app.models.enums import UserRole
from app.schemas.user import User  # Pydantic model for response serialization
from datetime import datetime

router = APIRouter()

# Audit Log Endpoints
@router.get("/audit-logs", response_model=List[AuditLog])
async def get_audit_logs(
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    user_id: Optional[int] = None,
    action: Optional[AuditActionType] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """Get audit logs with filters."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    service = AdminService(db)
    return await service.get_audit_logs(
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        action=action,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit
    )

# User Management Endpoints
@router.post("/users", response_model=User)
async def create_user(
    *,
    user_in: AdminUserCreate,
    request: Request,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """Create a new user with admin privileges."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    service = AdminService(db)
    return await service.create_user(user_in, current_user.id, request)

@router.put("/users/{user_id}", response_model=User)
async def update_user(
    *,
    user_id: int,
    user_in: AdminUserUpdate,
    request: Request,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """Update user details with admin privileges."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    service = AdminService(db)
    return await service.update_user(user_id, user_in, current_user.id, request)

@router.put("/users/{user_id}/role", response_model=User)
async def update_user_role(
    user_id: int,
    role_update: UserRoleUpdate,
    request: Request,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """Update user role and permissions."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    service = AdminService(db)
    return await service.update_user_role(user_id, role_update, current_user.id, request)

@router.post("/permissions/check")
async def check_permission(
    permission_check: UserPermissionCheck,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """Check if a user has a specific permission."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    service = AdminService(db)
    return await service.check_permission(permission_check)

# School Management Endpoints
@router.post("/schools", response_model=AdminSchoolResponse)
async def create_school(
    *,
    school_in: AdminSchoolCreate,
    request: Request,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """Create a new school with admin settings."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    service = AdminService(db)
    return await service.create_school(school_in, current_user.id, request)

@router.put("/schools/{school_id}", response_model=AdminSchoolResponse)
async def update_school(
    *,
    school_id: int,
    school_in: AdminSchoolUpdate,
    request: Request,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """Update school settings with admin privileges."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    service = AdminService(db)
    return await service.update_school(school_id, school_in, current_user.id, request)

@router.get("/schools/{school_id}", response_model=AdminSchoolResponse)
async def get_school_details(
    *,
    school_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """Get detailed school information including usage statistics."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    service = AdminService(db)
    return await service.get_school_details(school_id)

# User Suspension and Deletion
@router.post("/users/{user_id}/suspend", response_model=User)
async def suspend_user(
    *,
    user_id: int,
    suspension: UserSuspension,
    request: Request,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """Suspend a user temporarily or indefinitely."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    service = AdminService(db)
    return await service.suspend_user(user_id, suspension, current_user.id, request)

@router.delete("/users/{user_id}")
async def delete_user(
    *,
    user_id: int,
    deletion: UserDeletion,
    request: Request,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """Delete a user (soft delete by default)."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    service = AdminService(db)
    await service.delete_user(user_id, deletion, current_user.id, request)
    return {"message": "User deleted successfully"}

# School Suspension and Deletion
@router.post("/schools/{school_id}/suspend", response_model=AdminSchoolResponse)
async def suspend_school(
    *,
    school_id: int,
    suspension: SchoolSuspension,
    request: Request,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """Suspend a school temporarily or indefinitely."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    service = AdminService(db)
    return await service.suspend_school(school_id, suspension, current_user.id, request)

@router.delete("/schools/{school_id}")
async def delete_school(
    *,
    school_id: int,
    deletion: SchoolDeletion,
    request: Request,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """Delete a school and optionally its associated data."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    service = AdminService(db)
    await service.delete_school(school_id, deletion, current_user.id, request)
    return {"message": "School deleted successfully"} 