from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.api import deps
from app.models import models
from app.schemas import analytics
from datetime import datetime, timedelta
from app.services.analytics_service import AnalyticsService
from app.schemas.analytics import (
    StudentAnalytics, CourseAnalytics,
    StudentProgressReport, AnalyticsRequest,
    MetricType, TimeFrame
)
from app.models.models import User, UserRole

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

@router.post("/track-activity")
async def track_learning_activity(
    *,
    db: Session = Depends(deps.get_db),
    student_id: int,
    course_id: int,
    activity_type: str,
    module_id: Optional[int] = None,
    duration: Optional[int] = None,
    score: Optional[float] = None,
    metadata: Optional[dict] = None,
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    Track a learning activity for analytics.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.TEACHER] and current_user.id != student_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    analytics_service = AnalyticsService(db)
    return await analytics_service.track_learning_activity(
        student_id=student_id,
        course_id=course_id,
        activity_type=activity_type,
        module_id=module_id,
        duration=duration,
        score=score,
        metadata=metadata
    )

@router.get("/student/{student_id}", response_model=StudentAnalytics)
async def get_student_analytics(
    student_id: int,
    course_id: Optional[int] = None,
    time_frame: TimeFrame = TimeFrame.ALL,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    Get comprehensive analytics for a student.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.TEACHER] and current_user.id != student_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    analytics_service = AnalyticsService(db)
    return await analytics_service.get_student_analytics(
        student_id=student_id,
        course_id=course_id,
        time_frame=time_frame
    )

@router.get("/course/{course_id}", response_model=CourseAnalytics)
async def get_course_analytics(
    course_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    Get comprehensive analytics for a course.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.TEACHER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    analytics_service = AnalyticsService(db)
    return await analytics_service.get_course_analytics(course_id)

@router.get("/progress-report/{student_id}", response_model=StudentProgressReport)
async def get_student_progress_report(
    student_id: int,
    time_frame: TimeFrame = TimeFrame.ALL,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    Generate a comprehensive progress report for a student.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.TEACHER] and current_user.id != student_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    analytics_service = AnalyticsService(db)
    return await analytics_service.generate_student_progress_report(
        student_id=student_id,
        time_frame=time_frame
    )

@router.get("/dashboard/overview")
async def get_dashboard_overview(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    Get overview statistics for the analytics dashboard.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.TEACHER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    analytics_service = AnalyticsService(db)
    
    # Get overall statistics
    total_students = await analytics_service.get_total_students()
    active_students = await analytics_service.get_active_students()
    course_completion_rates = await analytics_service.get_course_completion_rates()
    engagement_metrics = await analytics_service.get_overall_engagement_metrics()
    
    return {
        "total_students": total_students,
        "active_students": active_students,
        "course_completion_rates": course_completion_rates,
        "engagement_metrics": engagement_metrics,
        "updated_at": datetime.utcnow()
    }

@router.get("/dashboard/performance")
async def get_performance_metrics(
    course_id: Optional[int] = None,
    time_frame: TimeFrame = TimeFrame.ALL,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    Get detailed performance metrics for the analytics dashboard.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.TEACHER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    analytics_service = AnalyticsService(db)
    
    return await analytics_service.get_performance_metrics(
        course_id=course_id,
        time_frame=time_frame
    )

@router.get("/dashboard/engagement")
async def get_engagement_metrics(
    course_id: Optional[int] = None,
    time_frame: TimeFrame = TimeFrame.ALL,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    Get detailed engagement metrics for the analytics dashboard.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.TEACHER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    analytics_service = AnalyticsService(db)
    
    return await analytics_service.get_engagement_metrics(
        course_id=course_id,
        time_frame=time_frame
    ) 