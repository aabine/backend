from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api import deps
from app.models import models
from app.schemas import ai_module
from app.services.ai_service import AIService
from app.core.config import settings

router = APIRouter()

@router.post("/", response_model=ai_module.AIModule)
def create_ai_module(
    *,
    db: Session = Depends(deps.get_db),
    module_in: ai_module.AIModuleCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new AI module.
    """
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    module = models.AIModule(
        name=module_in.name,
        description=module_in.description,
        module_type=module_in.module_type,
        configuration=module_in.configuration,
        school_id=current_user.school_id,
    )
    db.add(module)
    db.commit()
    db.refresh(module)
    return module

@router.get("/", response_model=List[ai_module.AIModule])
def read_ai_modules(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve AI modules.
    """
    if current_user.role not in [models.UserRole.ADMIN, models.UserRole.TEACHER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    query = db.query(models.AIModule)
    if current_user.role == models.UserRole.TEACHER:
        if not current_user.school_id:
            raise HTTPException(status_code=404, detail="No school associated with user")
        query = query.filter(models.AIModule.school_id == current_user.school_id)
    
    modules = query.offset(skip).limit(limit).all()
    return modules

@router.post("/enhance-content", response_model=ai_module.EnhancedContent)
async def enhance_learning_content(
    *,
    db: Session = Depends(deps.get_db),
    content_in: ai_module.ContentEnhanceRequest,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Enhance learning content using AI.
    """
    if current_user.role not in [models.UserRole.ADMIN, models.UserRole.TEACHER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Get the school's AI configuration
    school = db.query(models.School).filter(models.School.id == current_user.school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    # Create a mock learning material for enhancement
    material = models.LearningMaterial(
        content=content_in.content,
        material_type=content_in.content_type
    )
    
    try:
        ai_service = AIService(db)
        enhanced_content = await ai_service.enhance_learning_material(
            material=material,
            enhancement_type=content_in.enhancement_type,
            school_config=school.configuration
        )
        return {"enhanced_content": enhanced_content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze-progress", response_model=ai_module.ProgressAnalysis)
async def analyze_progress(
    *,
    db: Session = Depends(deps.get_db),
    analysis_request: ai_module.ProgressAnalysisRequest,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Analyze student progress using AI.
    """
    if current_user.role not in [models.UserRole.ADMIN, models.UserRole.TEACHER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    course = db.query(models.Course).filter(models.Course.id == analysis_request.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    try:
        ai_service = AIService(db)
        analysis_results = await ai_service.analyze_learning_patterns(
            course=course,
            timeframe="all"
        )
        return {"analysis_results": analysis_results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-assessment", response_model=ai_module.Assessment)
async def generate_assessment(
    *,
    db: Session = Depends(deps.get_db),
    assessment_request: ai_module.AssessmentRequest,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Generate an adaptive assessment for learning material.
    """
    if current_user.role not in [models.UserRole.ADMIN, models.UserRole.TEACHER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    material = (
        db.query(models.LearningMaterial)
        .filter(models.LearningMaterial.id == assessment_request.material_id)
        .first()
    )
    if not material:
        raise HTTPException(status_code=404, detail="Learning material not found")
    
    try:
        ai_service = AIService(db)
        assessment = await ai_service.generate_adaptive_assessment(
            material=material,
            student_level=assessment_request.student_level
        )
        return assessment
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/learning-insights/{student_id}", response_model=ai_module.LearningInsights)
async def get_learning_insights(
    *,
    db: Session = Depends(deps.get_db),
    student_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get AI-generated learning insights for a student.
    """
    if (current_user.role not in [models.UserRole.ADMIN, models.UserRole.TEACHER] and 
        current_user.id != student_id):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    student = db.query(models.User).filter(models.User.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    try:
        ai_service = AIService(db)
        insights = await ai_service.provide_learning_insights(
            student=student,
            timeframe="last_month"
        )
        return insights
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/curriculum-plan", response_model=ai_module.CurriculumPlan)
async def generate_curriculum_plan(
    *,
    db: Session = Depends(deps.get_db),
    plan_request: ai_module.CurriculumPlanRequest,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Generate a comprehensive curriculum plan using AI.
    """
    if current_user.role not in [models.UserRole.ADMIN, models.UserRole.TEACHER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    course = db.query(models.Course).filter(models.Course.id == plan_request.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    try:
        ai_service = AIService(db)
        curriculum_plan = await ai_service.generate_curriculum_plan(
            course=course,
            learning_objectives=plan_request.learning_objectives,
            duration_weeks=plan_request.duration_weeks,
            student_level=plan_request.student_level
        )
        return curriculum_plan
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/engagement-analysis", response_model=ai_module.EngagementAnalysis)
async def analyze_engagement(
    *,
    db: Session = Depends(deps.get_db),
    analysis_request: ai_module.EngagementAnalysisRequest,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Analyze student engagement patterns and provide improvement strategies.
    """
    if current_user.role not in [models.UserRole.ADMIN, models.UserRole.TEACHER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    course = db.query(models.Course).filter(models.Course.id == analysis_request.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    try:
        ai_service = AIService(db)
        engagement_analysis = await ai_service.analyze_student_engagement(
            course=course,
            timeframe=analysis_request.timeframe,
            include_recommendations=analysis_request.include_recommendations
        )
        return engagement_analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/automated-feedback", response_model=ai_module.AutomatedFeedback)
async def generate_feedback(
    *,
    db: Session = Depends(deps.get_db),
    feedback_request: ai_module.AutomatedFeedbackRequest,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Generate automated feedback for student submissions.
    """
    if current_user.role not in [models.UserRole.ADMIN, models.UserRole.TEACHER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    student = db.query(models.User).filter(models.User.id == feedback_request.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    material = (
        db.query(models.LearningMaterial)
        .filter(models.LearningMaterial.id == feedback_request.material_id)
        .first()
    )
    if not material:
        raise HTTPException(status_code=404, detail="Learning material not found")
    
    try:
        ai_service = AIService(db)
        feedback = await ai_service.generate_automated_feedback(
            student=student,
            material=material,
            submission_content=feedback_request.submission_content,
            feedback_type=feedback_request.feedback_type
        )
        return feedback
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/performance-prediction", response_model=ai_module.PerformancePrediction)
async def predict_performance(
    *,
    db: Session = Depends(deps.get_db),
    prediction_request: ai_module.PerformancePredictionRequest,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Predict student performance and identify intervention needs.
    """
    if current_user.role not in [models.UserRole.ADMIN, models.UserRole.TEACHER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    student = db.query(models.User).filter(models.User.id == prediction_request.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    course = db.query(models.Course).filter(models.Course.id == prediction_request.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    try:
        ai_service = AIService(db)
        prediction = await ai_service.predict_student_performance(
            student=student,
            course=course,
            prediction_horizon=prediction_request.prediction_horizon
        )
        return prediction
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/concept-map", response_model=ai_module.ConceptMap)
async def generate_concept_map(
    *,
    db: Session = Depends(deps.get_db),
    map_request: ai_module.ConceptMapRequest,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Generate a concept map for learning material.
    """
    if current_user.role not in [models.UserRole.ADMIN, models.UserRole.TEACHER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    material = (
        db.query(models.LearningMaterial)
        .filter(models.LearningMaterial.id == map_request.material_id)
        .first()
    )
    if not material:
        raise HTTPException(status_code=404, detail="Learning material not found")
    
    try:
        ai_service = AIService(db)
        concept_map = await ai_service.generate_concept_map(
            material=material,
            complexity_level=map_request.complexity_level
        )
        return concept_map
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 