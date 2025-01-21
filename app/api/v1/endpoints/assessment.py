from typing import List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api import deps
from app.services.assessment_service import AssessmentService
from app.schemas.assessment import (
    Assessment, AssessmentCreate,
    AssessmentSubmission, SubmissionCreate,
    PeerReview, PeerReviewCreate
)
from app.models.models import User, UserRole

router = APIRouter()

@router.post("/", response_model=Assessment)
async def create_assessment(
    assessment: AssessmentCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """Create a new assessment."""
    if current_user.role not in [UserRole.ADMIN, UserRole.TEACHER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    service = AssessmentService(db)
    return await service.create_assessment(assessment, current_user.id)

@router.get("/{assessment_id}", response_model=Assessment)
async def get_assessment(
    assessment_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """Get assessment by ID."""
    service = AssessmentService(db)
    return await service.get_assessment(assessment_id)

@router.post("/{assessment_id}/submit", response_model=AssessmentSubmission)
async def submit_assessment(
    assessment_id: int,
    submission: SubmissionCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """Submit an assessment."""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can submit assessments")
    
    service = AssessmentService(db)
    return await service.submit_assessment(assessment_id, submission, current_user.id)

@router.post("/submissions/{submission_id}/peer-review", response_model=PeerReview)
async def create_peer_review(
    submission_id: int,
    review: PeerReviewCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """Create a peer review for a submission."""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can create peer reviews")
    
    service = AssessmentService(db)
    return await service.create_peer_review(submission_id, review, current_user.id)

@router.post("/submissions/{submission_id}/grade")
async def grade_submission(
    submission_id: int,
    answers_scores: Dict[int, float],
    feedback: Optional[str] = None,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """Grade a submission manually."""
    if current_user.role not in [UserRole.ADMIN, UserRole.TEACHER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    service = AssessmentService(db)
    return await service.grade_submission(submission_id, answers_scores, feedback, current_user.id) 