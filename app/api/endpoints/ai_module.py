from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api import deps
from app.models import models
from app.schemas import ai_module
from app.services.ai_service import AIService
from app.services.batch_service import BatchService
from app.core.config import settings

router = APIRouter()

# ... existing endpoints ...

@router.post("/batch/enhance-materials", response_model=ai_module.BatchTaskResponse)
async def batch_enhance_materials(
    *,
    db: Session = Depends(deps.get_db),
    batch_request: ai_module.BatchEnhanceRequest,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Enhance multiple learning materials in batch.
    """
    if current_user.role not in [models.UserRole.ADMIN, models.UserRole.TEACHER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    school = db.query(models.School).filter(models.School.id == batch_request.school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")

    try:
        batch_service = BatchService(db)
        task = await batch_service.enhance_materials_batch(
            materials=batch_request.materials,
            school_config=school.configuration
        )
        return task
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch/analyze-progress", response_model=ai_module.BatchTaskResponse)
async def batch_analyze_progress(
    *,
    db: Session = Depends(deps.get_db),
    batch_request: ai_module.BatchAnalysisRequest,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Analyze progress for multiple students or courses in batch.
    """
    if current_user.role not in [models.UserRole.ADMIN, models.UserRole.TEACHER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        batch_service = BatchService(db)
        task = await batch_service.analyze_progress_batch(
            courses=batch_request.courses,
            timeframe=batch_request.timeframe
        )
        return task
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/batch/task/{task_id}", response_model=ai_module.BatchTaskResult)
async def get_batch_task_status(
    *,
    task_id: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get the status and results of a batch processing task.
    """
    if current_user.role not in [models.UserRole.ADMIN, models.UserRole.TEACHER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        batch_service = BatchService(db)
        result = await batch_service.get_task_result(task_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch/generate-feedback", response_model=ai_module.BatchTaskResponse)
async def batch_generate_feedback(
    *,
    db: Session = Depends(deps.get_db),
    batch_request: ai_module.BatchFeedbackRequest,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Generate feedback for multiple student submissions in batch.
    """
    if current_user.role not in [models.UserRole.ADMIN, models.UserRole.TEACHER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        batch_service = BatchService(db)
        task = await batch_service.generate_feedback_batch(
            submissions=batch_request.submissions,
            feedback_type=batch_request.feedback_type
        )
        return task
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 