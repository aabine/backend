from pydantic import BaseModel
from typing import List, Dict, Any

class SchoolOverview(BaseModel):
    total_students: int
    total_teachers: int
    total_courses: int
    total_ai_modules: int

class CourseProgress(BaseModel):
    course_id: int
    course_name: str
    progress: Dict[str, Any]

class StudentProgress(BaseModel):
    student_id: int
    course_progress: List[CourseProgress]

class CoursePerformance(BaseModel):
    course_id: int
    total_enrolled: int
    progress_data: List[Dict[str, Any]]

class ModuleStats(BaseModel):
    module_id: int
    module_name: str
    module_type: str
    configuration: Dict[str, Any]

class AIUsageStats(BaseModel):
    ai_enhanced_materials: int
    active_modules: int
    module_stats: List[ModuleStats] 