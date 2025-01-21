from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api import deps
from app.models import models
from app.schemas import course, learning_material

router = APIRouter()

@router.post("/", response_model=course.Course)
def create_course(
    *,
    db: Session = Depends(deps.get_db),
    course_in: course.CourseCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new course.
    """
    if current_user.role not in [models.UserRole.ADMIN, models.UserRole.TEACHER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    course_obj = models.Course(
        name=course_in.name,
        description=course_in.description,
        teacher_id=current_user.id,
        school_id=current_user.school_id,
    )
    db.add(course_obj)
    db.commit()
    db.refresh(course_obj)
    return course_obj

@router.get("/", response_model=List[course.Course])
def read_courses(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve courses.
    """
    if current_user.role == models.UserRole.ADMIN:
        courses = db.query(models.Course).offset(skip).limit(limit).all()
    elif current_user.role == models.UserRole.TEACHER:
        courses = (
            db.query(models.Course)
            .filter(models.Course.teacher_id == current_user.id)
            .offset(skip)
            .limit(limit)
            .all()
        )
    else:
        courses = [enrollment.course for enrollment in current_user.student_courses]
    return courses

@router.post("/{course_id}/materials", response_model=learning_material.LearningMaterial)
def create_learning_material(
    *,
    db: Session = Depends(deps.get_db),
    course_id: int,
    material_in: learning_material.LearningMaterialCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new learning material.
    """
    course_obj = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course_obj:
        raise HTTPException(status_code=404, detail="Course not found")
    if current_user.role != models.UserRole.ADMIN and course_obj.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    material = models.LearningMaterial(
        title=material_in.title,
        content=material_in.content,
        material_type=material_in.material_type,
        course_id=course_id,
        ai_enhanced=material_in.ai_enhanced,
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return material

@router.get("/{course_id}/materials", response_model=List[learning_material.LearningMaterial])
def read_learning_materials(
    *,
    db: Session = Depends(deps.get_db),
    course_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get all learning materials for a course.
    """
    course_obj = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course_obj:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Check if user has access to the course
    if current_user.role == models.UserRole.STUDENT:
        enrollment = (
            db.query(models.StudentCourse)
            .filter(
                models.StudentCourse.student_id == current_user.id,
                models.StudentCourse.course_id == course_id
            )
            .first()
        )
        if not enrollment:
            raise HTTPException(status_code=403, detail="Not enrolled in this course")
    
    return course_obj.learning_materials

@router.post("/{course_id}/enroll", response_model=course.CourseEnrollment)
def enroll_student(
    *,
    db: Session = Depends(deps.get_db),
    course_id: int,
    student_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Enroll a student in a course.
    """
    if current_user.role not in [models.UserRole.ADMIN, models.UserRole.TEACHER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    course_obj = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course_obj:
        raise HTTPException(status_code=404, detail="Course not found")
    
    student = db.query(models.User).filter(
        models.User.id == student_id,
        models.User.role == models.UserRole.STUDENT
    ).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    enrollment = models.StudentCourse(
        student_id=student_id,
        course_id=course_id,
        progress={}
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment 