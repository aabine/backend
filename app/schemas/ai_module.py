from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

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
    content: str
    content_type: str
    enhancement_type: str

class EnhancedContent(BaseModel):
    enhanced_content: str

class ProgressAnalysisRequest(BaseModel):
    course_id: int
    analysis_type: str

class ProgressAnalysis(BaseModel):
    analysis_results: Dict[str, Any]

class AssessmentRequest(BaseModel):
    material_id: int
    student_level: str = "intermediate"

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
    course_id: int
    learning_objectives: List[str]
    duration_weeks: int
    student_level: str = "intermediate"

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
    school_id: int
    materials: List[Dict[str, Any]] = Field(
        ...,
        description="List of materials to enhance, each containing 'content' and 'content_type'"
    )

class BatchAnalysisRequest(BaseModel):
    courses: List[int] = Field(
        ...,
        description="List of course IDs to analyze"
    )
    timeframe: str = Field(
        default="all",
        description="Time period for analysis (e.g., 'all', 'last_month', 'last_week')"
    )

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
    task_id: str = Field(
        ...,
        description="ID of the created batch processing task"
    )

class BatchTaskResult(BaseModel):
    task_id: str
    status: str = Field(
        ...,
        description="Status of the task (pending, processing, completed, failed)"
    )
    results: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Results of the batch processing task if completed"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if task failed"
    ) 