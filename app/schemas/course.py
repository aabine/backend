from pydantic import BaseModel
from typing import Optional, Dict, Any

class CourseBase(BaseModel):
    name: str
    description: Optional[str] = None

class CourseCreate(CourseBase):
    pass

class CourseUpdate(CourseBase):
    pass

class Course(CourseBase):
    id: int
    teacher_id: int
    school_id: int

    class Config:
        from_attributes = True

class CourseEnrollment(BaseModel):
    student_id: int
    course_id: int
    progress: Dict[str, Any] = {}

    class Config:
        from_attributes = True 