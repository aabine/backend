from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.api import deps
from app.models import models
from app.schemas import analytics
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/school/overview", response_model=analytics.SchoolOverview)
def get_school_overview(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get school overview statistics.
    """
    if current_user.role not in [models.UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Get counts
    total_students = (
        db.query(func.count(models.User.id))
        .filter(
            models.User.school_id == current_user.school_id,
            models.User.role == models.UserRole.STUDENT
        )
        .scalar()
    )
    
    total_teachers = (
        db.query(func.count(models.User.id))
        .filter(
            models.User.school_id == current_user.school_id,
            models.User.role == models.UserRole.TEACHER
        )
        .scalar()
    )
    
    total_courses = (
        db.query(func.count(models.Course.id))
        .filter(models.Course.school_id == current_user.school_id)
        .scalar()
    )
    
    total_ai_modules = (
        db.query(func.count(models.AIModule.id))
        .filter(models.AIModule.school_id == current_user.school_id)
        .scalar()
    )
    
    return {
        "total_students": total_students,
        "total_teachers": total_teachers,
        "total_courses": total_courses,
        "total_ai_modules": total_ai_modules
    }

@router.get("/course/{course_id}/performance", response_model=analytics.CoursePerformance)
def get_course_performance(
    course_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get course performance analytics.
    """
    if current_user.role not in [models.UserRole.ADMIN, models.UserRole.TEACHER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    if current_user.role == models.UserRole.TEACHER and course.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Get enrollment statistics
    total_enrolled = (
        db.query(func.count(models.StudentCourse.student_id))
        .filter(models.StudentCourse.course_id == course_id)
        .scalar()
    )
    
    # Get progress statistics
    enrollments = (
        db.query(models.StudentCourse)
        .filter(models.StudentCourse.course_id == course_id)
        .all()
    )
    
    progress_data = []
    for enrollment in enrollments:
        if enrollment.progress:
            progress_data.append(enrollment.progress)
    
    return {
        "course_id": course_id,
        "total_enrolled": total_enrolled,
        "progress_data": progress_data
    }

@router.get("/student/{student_id}/progress", response_model=analytics.StudentProgress)
def get_student_progress(
    student_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get student progress across all courses.
    """
    if current_user.role == models.UserRole.STUDENT and current_user.id != student_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    student = (
        db.query(models.User)
        .filter(
            models.User.id == student_id,
            models.User.role == models.UserRole.STUDENT
        )
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Get all course enrollments and progress
    enrollments = (
        db.query(models.StudentCourse)
        .filter(models.StudentCourse.student_id == student_id)
        .all()
    )
    
    course_progress = []
    for enrollment in enrollments:
        course_progress.append({
            "course_id": enrollment.course_id,
            "course_name": enrollment.course.name,
            "progress": enrollment.progress
        })
    
    return {
        "student_id": student_id,
        "course_progress": course_progress
    }

@router.get("/ai-usage", response_model=analytics.AIUsageStats)
def get_ai_usage_stats(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get AI usage statistics for the school.
    """
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Get AI-enhanced content count
    ai_enhanced_materials = (
        db.query(func.count(models.LearningMaterial.id))
        .join(models.Course)
        .filter(
            models.Course.school_id == current_user.school_id,
            models.LearningMaterial.ai_enhanced == True
        )
        .scalar()
    )
    
    # Get active AI modules
    active_modules = (
        db.query(models.AIModule)
        .filter(
            models.AIModule.school_id == current_user.school_id,
            models.AIModule.is_active == True
        )
        .all()
    )
    
    module_stats = []
    for module in active_modules:
        module_stats.append({
            "module_id": module.id,
            "module_name": module.name,
            "module_type": module.module_type,
            "configuration": module.configuration
        })
    
    return {
        "ai_enhanced_materials": ai_enhanced_materials,
        "active_modules": len(active_modules),
        "module_stats": module_stats
    } 