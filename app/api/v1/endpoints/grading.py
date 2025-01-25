from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api import deps
from app.services.grading_service import GradingService
from app.models.models import User, UserRole, AssessmentType
from app.schemas.grading import (
    CourseGradeBook,
    GradeScale, GradeScaleCreate,
    GradeWeight, GradeWeightCreate
)

router = APIRouter()

@router.get("/courses/{course_id}/gradebook", response_model=CourseGradeBook)
async def get_course_gradebook(
    course_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """Get the complete gradebook for a course."""
    if current_user.role not in [UserRole.ADMIN, UserRole.TEACHER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    service = GradingService(db)
    return await service.get_course_gradebook(course_id)

@router.get("/courses/{course_id}/students/{student_id}/grades")
async def get_student_course_grades(
    course_id: int,
    student_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """Get detailed grade information for a student in a course."""
    # Check permissions
    if (current_user.role not in [UserRole.ADMIN, UserRole.TEACHER] and 
        current_user.id != student_id):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    service = GradingService(db)
    return await service.get_student_course_grade(student_id, course_id)

@router.post("/grade-scales", response_model=GradeScale)
async def create_grade_scale(
    grade_scale: GradeScaleCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """Create a new grade scale."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    service = GradingService(db)
    return await service.create_grade_scale(grade_scale)

@router.put("/courses/{course_id}/grade-weights", response_model=List[GradeWeight])
async def update_grade_weights(
    course_id: int,
    weights: Dict[AssessmentType, float],
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """Update grade weights for different assessment types in a course."""
    if current_user.role not in [UserRole.ADMIN, UserRole.TEACHER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    service = GradingService(db)
    return await service.update_grade_weights(course_id, weights)

@router.get("/courses/{course_id}/grade-distribution")
async def get_grade_distribution(
    course_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """Get grade distribution statistics for a course."""
    if current_user.role not in [UserRole.ADMIN, UserRole.TEACHER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    service = GradingService(db)
    gradebook = await service.get_course_gradebook(course_id)
    return {
        "distribution": gradebook.grade_distribution,
        "class_average": gradebook.class_average
    } 