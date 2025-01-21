from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum

class MetricType(str, Enum):
    PROGRESS = "progress"
    PERFORMANCE = "performance"
    ENGAGEMENT = "engagement"
    COMPLETION = "completion"

class TimeFrame(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    ALL = "all"

class ProgressMetric(BaseModel):
    completed_items: int
    total_items: int
    completion_rate: float
    last_activity: datetime
    current_module: str
    time_spent: int  # in minutes

class PerformanceMetric(BaseModel):
    average_score: float
    highest_score: float
    lowest_score: float
    assessments_taken: int
    improvement_rate: Optional[float] = None
    strengths: List[str]
    areas_for_improvement: List[str]

class EngagementMetric(BaseModel):
    login_frequency: int
    average_session_duration: int  # in minutes
    content_interactions: int
    discussion_participation: int
    last_login: datetime
    activity_streak: int
    completion_rate: float

class StudentAnalytics(BaseModel):
    student_id: int
    course_id: int
    progress: ProgressMetric
    performance: PerformanceMetric
    engagement: EngagementMetric
    updated_at: datetime

    class Config:
        from_attributes = True

class AnalyticsRequest(BaseModel):
    student_id: Optional[int] = None
    course_id: Optional[int] = None
    metric_type: Optional[MetricType] = None
    time_frame: TimeFrame = TimeFrame.ALL
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class CourseAnalytics(BaseModel):
    course_id: int
    total_students: int
    active_students: int
    average_progress: float
    average_performance: float
    average_engagement: float
    completion_rate: float
    at_risk_students: int
    top_performing_students: int
    updated_at: datetime

    class Config:
        from_attributes = True

class LearningPathProgress(BaseModel):
    module_id: int
    module_name: str
    completed_lessons: int
    total_lessons: int
    average_score: float
    time_spent: int  # in minutes
    status: str  # "not_started", "in_progress", "completed"

class StudentProgressReport(BaseModel):
    student_id: int
    student_name: str
    enrollment_date: datetime
    courses: List[Dict[str, Any]]
    overall_progress: float
    overall_performance: float
    learning_paths: List[LearningPathProgress]
    recent_activities: List[Dict[str, Any]]
    recommendations: List[str]

    class Config:
        from_attributes = True

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