from pydantic import BaseModel, Field, validator
from typing import Dict, Optional, List, Any
from datetime import datetime
from app.models.models import AssessmentType

class GradeScaleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    scale_type: str = Field(..., pattern="^(letter|numeric|custom)$")
    ranges: Dict[str, Dict[str, float]]

    @validator('ranges')
    def validate_ranges(cls, v, values):
        if not v:
            raise ValueError("Ranges cannot be empty")
        if values.get('scale_type') == 'letter':
            valid_grades = {'A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F'}
            if not all(grade in valid_grades for grade in v.keys()):
                raise ValueError("Invalid letter grades")
        return v

class GradeScaleCreate(GradeScaleBase):
    school_id: int

class GradeScale(GradeScaleBase):
    id: int
    school_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class GradeWeightBase(BaseModel):
    assessment_type: AssessmentType
    weight: float = Field(..., ge=0, le=100)

class GradeWeightCreate(GradeWeightBase):
    course_id: int

class GradeWeight(GradeWeightBase):
    id: int
    course_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CourseGradeSettings(BaseModel):
    grade_scale_id: int
    grade_weights: List[GradeWeightCreate]

    @validator('grade_weights')
    def validate_weights(cls, v):
        total_weight = sum(weight.weight for weight in v)
        if total_weight != 100:
            raise ValueError("Grade weights must sum to 100%")
        return v

class StudentGrade(BaseModel):
    student_id: int
    course_id: int
    assessment_type: AssessmentType
    raw_score: float
    weighted_score: float
    letter_grade: Optional[str]
    numeric_grade: float
    assessment_id: int
    graded_at: datetime
    graded_by: int

class GradeBookEntry(BaseModel):
    student_id: int
    student_name: str
    assessments: Dict[str, float]  # assessment_name: score
    weighted_average: float
    final_grade: str
    last_graded: datetime

class CourseGradeBook(BaseModel):
    course_id: int
    course_name: str
    grade_scale: GradeScale
    grade_weights: List[GradeWeight]
    student_grades: List[GradeBookEntry]
    class_average: float
    grade_distribution: Dict[str, int]  # grade: count 