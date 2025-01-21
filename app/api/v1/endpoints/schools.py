from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api import deps
from app.models import models
from app.schemas import school
from app.core.security import get_password_hash
import secrets
from datetime import datetime, timedelta

router = APIRouter()

@router.post("/", response_model=school.School)
def create_school(
    *,
    db: Session = Depends(deps.get_db),
    school_in: school.SchoolCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new school with subscription details.
    """
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Set subscription expiry based on type
    subscription_expires_at = datetime.utcnow() + timedelta(days=365)  # Default 1 year
    
    school_obj = models.School(
        name=school_in.name,
        description=school_in.description,
        subscription_type=school_in.subscription_type,
        max_users=school_in.max_users,
        features_enabled=school_in.features_enabled or {},
        contact_email=school_in.contact_email,
        contact_phone=school_in.contact_phone,
        address=school_in.address,
        settings=school_in.settings or {},
        configuration=school_in.configuration or {},
        api_key=secrets.token_urlsafe(32),
        subscription_expires_at=subscription_expires_at
    )
    db.add(school_obj)
    db.commit()
    db.refresh(school_obj)
    return school_obj

@router.get("/", response_model=List[school.School])
def read_schools(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve schools.
    """
    if current_user.role == models.UserRole.ADMIN:
        schools = db.query(models.School).offset(skip).limit(limit).all()
    else:
        schools = [current_user.school]
    return schools

@router.get("/{school_id}", response_model=school.School)
def read_school(
    *,
    db: Session = Depends(deps.get_db),
    school_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get school by ID.
    """
    school_obj = db.query(models.School).filter(models.School.id == school_id).first()
    if not school_obj:
        raise HTTPException(status_code=404, detail="School not found")
    if current_user.role != models.UserRole.ADMIN and current_user.school_id != school_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return school_obj

@router.put("/{school_id}", response_model=school.School)
def update_school(
    *,
    db: Session = Depends(deps.get_db),
    school_id: int,
    school_in: school.SchoolUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update school details including subscription and settings.
    """
    school_obj = db.query(models.School).filter(models.School.id == school_id).first()
    if not school_obj:
        raise HTTPException(status_code=404, detail="School not found")
    if current_user.role != models.UserRole.ADMIN and current_user.school_id != school_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    update_data = school_in.dict(exclude_unset=True)
    
    # Validate max_users if provided
    if "max_users" in update_data and update_data["max_users"] is not None:
        if update_data["max_users"] < 1:
            raise HTTPException(status_code=400, detail="Maximum users must be greater than 0")
    
    for field, value in update_data.items():
        setattr(school_obj, field, value)
    
    db.add(school_obj)
    db.commit()
    db.refresh(school_obj)
    return school_obj

@router.post("/{school_id}/regenerate-api-key", response_model=school.SchoolAPIKey)
def regenerate_api_key(
    *,
    db: Session = Depends(deps.get_db),
    school_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Regenerate school API key.
    """
    if current_user.role != models.UserRole.ADMIN and current_user.school_id != school_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    school_obj = db.query(models.School).filter(models.School.id == school_id).first()
    if not school_obj:
        raise HTTPException(status_code=404, detail="School not found")
    
    school_obj.api_key = secrets.token_urlsafe(32)
    db.add(school_obj)
    db.commit()
    db.refresh(school_obj)
    return {"api_key": school_obj.api_key} 