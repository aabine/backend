from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from fastapi import HTTPException
from app.models.models import (
    Assessment, Question, AssessmentSubmission, Answer, PeerReview,
    User, Course, AssessmentType, QuestionType
)
from app.schemas.assessment import (
    AssessmentCreate, QuestionCreate, SubmissionCreate,
    PeerReviewCreate
)
import logging

logger = logging.getLogger(__name__)

class AssessmentService:
    def __init__(self, db: Session):
        self.db = db

    async def create_assessment(self, data: AssessmentCreate, user_id: int) -> Assessment:
        """Create a new assessment with questions."""
        # Create assessment
        assessment = Assessment(
            **data.dict(exclude={'questions'}),
            created_by=user_id
        )
        self.db.add(assessment)
        await self.db.commit()
        await self.db.refresh(assessment)

        # Create questions
        for i, question_data in enumerate(data.questions):
            question = Question(
                **question_data.dict(),
                assessment_id=assessment.id,
                order=i + 1
            )
            self.db.add(question)
        
        await self.db.commit()
        return assessment

    async def get_assessment(self, assessment_id: int) -> Assessment:
        """Get assessment by ID."""
        assessment = self.db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")
        return assessment

    async def submit_assessment(
        self,
        assessment_id: int,
        data: SubmissionCreate,
        student_id: int
    ) -> AssessmentSubmission:
        """Submit an assessment."""
        # Verify assessment exists and is not past due date
        assessment = await self.get_assessment(assessment_id)
        if assessment.due_date and datetime.utcnow() > assessment.due_date:
            raise HTTPException(status_code=400, detail="Assessment submission deadline has passed")

        # Create submission
        submission = AssessmentSubmission(
            assessment_id=assessment_id,
            student_id=student_id
        )
        self.db.add(submission)
        await self.db.commit()
        await self.db.refresh(submission)

        # Create answers
        for answer_data in data.answers:
            answer = Answer(
                submission_id=submission.id,
                **answer_data.dict()
            )
            self.db.add(answer)

        await self.db.commit()

        # Auto-grade if possible
        await self._auto_grade_submission(submission)
        return submission

    async def _auto_grade_submission(self, submission: AssessmentSubmission):
        """Auto-grade submission where possible."""
        total_points = 0
        questions_graded = 0

        for answer in submission.answers:
            question = answer.question
            if question.question_type in [QuestionType.MULTIPLE_CHOICE, QuestionType.TRUE_FALSE]:
                if answer.answer_content == question.correct_answer:
                    answer.points_earned = question.points
                    total_points += question.points
                else:
                    answer.points_earned = 0
                questions_graded += 1

        # Update submission if all questions were auto-gradable
        if questions_graded == len(submission.answers):
            submission.score = total_points
            submission.status = "graded"
            submission.graded_at = datetime.utcnow()
        elif submission.assessment.requires_peer_review:
            submission.status = "peer_review_pending"
        
        await self.db.commit()

    async def create_peer_review(
        self,
        submission_id: int,
        data: PeerReviewCreate,
        reviewer_id: int
    ) -> PeerReview:
        """Create a peer review for a submission."""
        # Verify submission exists and needs peer review
        submission = self.db.query(AssessmentSubmission)\
            .filter(AssessmentSubmission.id == submission_id)\
            .first()
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")
        
        if submission.status != "peer_review_pending":
            raise HTTPException(status_code=400, detail="Submission is not pending peer review")

        # Check if reviewer has already reviewed this submission
        existing_review = self.db.query(PeerReview)\
            .filter(
                and_(
                    PeerReview.submission_id == submission_id,
                    PeerReview.reviewer_id == reviewer_id
                )
            ).first()
        if existing_review:
            raise HTTPException(status_code=400, detail="You have already reviewed this submission")

        # Create peer review
        review = PeerReview(
            submission_id=submission_id,
            reviewer_id=reviewer_id,
            **data.dict()
        )
        self.db.add(review)
        await self.db.commit()
        await self.db.refresh(review)

        # Check if all required peer reviews are completed
        review_count = self.db.query(PeerReview)\
            .filter(PeerReview.submission_id == submission_id)\
            .count()
        
        if review_count >= submission.assessment.peer_reviews_required:
            # Calculate final score from peer reviews
            avg_score = self.db.query(func.avg(PeerReview.score))\
                .filter(PeerReview.submission_id == submission_id)\
                .scalar()
            
            submission.score = avg_score
            submission.status = "graded"
            submission.graded_at = datetime.utcnow()
            await self.db.commit()

        return review

    async def grade_submission(
        self,
        submission_id: int,
        answers_scores: Dict[int, float],
        feedback: Optional[str],
        grader_id: int
    ) -> AssessmentSubmission:
        """Grade a submission manually."""
        submission = self.db.query(AssessmentSubmission)\
            .filter(AssessmentSubmission.id == submission_id)\
            .first()
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        total_points = 0
        for answer in submission.answers:
            if answer.id in answers_scores:
                answer.points_earned = answers_scores[answer.id]
                total_points += answer.points_earned

        submission.score = total_points
        submission.status = "graded"
        submission.graded_at = datetime.utcnow()
        submission.graded_by = grader_id
        submission.feedback = feedback

        await self.db.commit()
        return submission 