from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime

class AIModuleBase(BaseModel):
    name: str
    description: Optional[str] = None
    module_type: str
    configuration: Dict[str, Any] = {}

class AIModuleCreate(AIModuleBase):
    pass

class AIModuleUpdate(AIModuleBase):
    pass

class AIModule(AIModuleBase):
    id: int
    school_id: int
    is_active: bool

    class Config:
        from_attributes = True

class ContentEnhanceRequest(BaseModel):
    content: str = Field(..., min_length=10, max_length=10000)
    content_type: str = Field(..., pattern="^(text|video|audio|interactive)$")
    enhancement_type: str = Field(..., pattern="^(simplify|elaborate|interactive|differentiate)$")

    @validator('content')
    def validate_content(cls, v):
        if not v.strip():
            raise ValueError("Content cannot be empty or just whitespace")
        return v.strip()

class EnhancedContent(BaseModel):
    enhanced_content: str

class ProgressAnalysisRequest(BaseModel):
    course_id: int = Field(..., gt=0)
    analysis_type: str
    timeframe: str = Field(..., pattern="^(all|last_week|last_month|last_year)$")

class ProgressAnalysis(BaseModel):
    analysis_results: Dict[str, Any]

class AssessmentRequest(BaseModel):
    material_id: int = Field(..., gt=0)
    student_level: str = Field(..., pattern="^(beginner|intermediate|advanced)$")
    question_count: int = Field(..., ge=1, le=50)

class Assessment(BaseModel):
    material_id: int
    student_level: str
    assessment: str

class LearningInsights(BaseModel):
    student_id: int
    insights: str
    raw_data: List[Dict[str, Any]]
    timeframe: str

class RecommendationRequest(BaseModel):
    student_id: int
    course_id: int

class Recommendation(BaseModel):
    student_id: int
    course_id: int
    recommendations: str
    context: Dict[str, Any]

class CurriculumPlanRequest(BaseModel):
    course_id: int = Field(..., gt=0)
    learning_objectives: List[str] = Field(..., min_items=1, max_items=20)
    duration_weeks: int = Field(..., ge=1, le=52)
    student_level: str = Field(..., pattern="^(beginner|intermediate|advanced)$")

    @validator('learning_objectives')
    def validate_objectives(cls, v):
        if any(not obj.strip() for obj in v):
            raise ValueError("Learning objectives cannot be empty")
        return [obj.strip() for obj in v]

class CurriculumPlan(BaseModel):
    course_id: int
    curriculum_plan: str
    context: Dict[str, Any]

class EngagementAnalysisRequest(BaseModel):
    course_id: int
    timeframe: str = "last_month"
    include_recommendations: bool = True

class EngagementAnalysis(BaseModel):
    course_id: int
    engagement_analysis: str
    raw_data: List[Dict[str, Any]]
    timeframe: str

class AutomatedFeedbackRequest(BaseModel):
    student_id: int
    material_id: int
    submission_content: str
    feedback_type: str = "comprehensive"

class AutomatedFeedback(BaseModel):
    student_id: int
    material_id: int
    feedback: str
    feedback_type: str
    context: Dict[str, Any]

class PerformancePredictionRequest(BaseModel):
    student_id: int
    course_id: int
    prediction_horizon: str = "end_of_course"

class PerformancePrediction(BaseModel):
    student_id: int
    course_id: int
    prediction: str
    confidence_level: str
    prediction_horizon: str
    raw_data: Dict[str, Any]

class ConceptMapRequest(BaseModel):
    material_id: int
    complexity_level: str = "intermediate"

class ConceptMap(BaseModel):
    material_id: int
    concept_map: str
    complexity_level: str

class BatchEnhanceRequest(BaseModel):
    school_id: int = Field(..., gt=0)
    materials: List[Dict[str, Any]] = Field(..., min_items=1, max_items=100)

    @validator('materials')
    def validate_materials(cls, v):
        required_keys = {'id', 'content', 'content_type'}
        for item in v:
            if not all(key in item for key in required_keys):
                raise ValueError(f"Each material must contain: {required_keys}")
            if not item['content'].strip():
                raise ValueError("Material content cannot be empty")
        return v

class BatchAnalysisRequest(BaseModel):
    courses: List[int] = Field(..., min_items=1, max_items=50)
    timeframe: str = Field(..., pattern="^(all|last_week|last_month|last_year)$")

class BatchFeedbackRequest(BaseModel):
    submissions: List[Dict[str, Any]] = Field(
        ...,
        description="List of submissions to generate feedback for"
    )
    feedback_type: str = Field(
        default="comprehensive",
        description="Type of feedback to generate"
    )

class BatchTaskResponse(BaseModel):
    task_id: str
    status: str = Field(..., pattern="^(pending|processing|completed|failed)$")
    created_at: datetime

class BatchTaskResult(BaseModel):
    task_id: str
    status: str = Field(..., pattern="^(pending|processing|completed|failed)$")
    results: Optional[List[Dict[str, Any]]]
    error: Optional[str]
    completed_at: Optional[datetime]

class AIModule(BaseModel):
    id: int
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    module_type: str
    configuration: Dict[str, Any]
    school_id: int
    is_active: bool

    class Config:
        from_attributes = True

class AIModuleCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    module_type: str = Field(..., pattern="^(enhancement|analysis|assessment|recommendation)$")
    configuration: Dict[str, Any] = Field(default_factory=dict)

    @validator('configuration')
    def validate_configuration(cls, v):
        required_keys = {'model', 'temperature', 'max_tokens'}
        if not all(key in v for key in required_keys):
            raise ValueError(f"Configuration must contain: {required_keys}")
        return v 