from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class AssessmentType(str, Enum):
    QUIZ = "quiz"
    EXAM = "exam"
    ASSIGNMENT = "assignment"

class QuestionType(str, Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"
    FILE_UPLOAD = "file_upload"

class QuestionBase(BaseModel):
    question_type: QuestionType
    content: str = Field(..., min_length=1)
    options: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    points: int = Field(1, ge=1)
    order: Optional[int] = None

    @validator("options")
    def validate_options(cls, v, values):
        if values.get("question_type") == QuestionType.MULTIPLE_CHOICE and not v:
            raise ValueError("Multiple choice questions must have options")
        return v

class QuestionCreate(QuestionBase):
    pass

class Question(QuestionBase):
    id: int
    assessment_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AssessmentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    course_id: int
    assessment_type: AssessmentType
    total_points: int = Field(100, ge=0)
    passing_score: Optional[int] = None
    due_date: Optional[datetime] = None
    requires_peer_review: bool = False
    peer_reviews_required: int = Field(0, ge=0)

class AssessmentCreate(AssessmentBase):
    questions: List[QuestionCreate]

class Assessment(AssessmentBase):
    id: int
    created_by: int
    created_at: datetime
    updated_at: datetime
    questions: List[Question]

    class Config:
        from_attributes = True

class AnswerBase(BaseModel):
    question_id: int
    answer_content: Optional[str] = None
    file_url: Optional[str] = None

class AnswerCreate(AnswerBase):
    pass

class Answer(AnswerBase):
    id: int
    submission_id: int
    points_earned: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True

class SubmissionBase(BaseModel):
    assessment_id: int
    answers: List[AnswerCreate]

class SubmissionCreate(SubmissionBase):
    pass

class AssessmentSubmission(SubmissionBase):
    id: int
    student_id: int
    status: str
    score: Optional[float] = None
    submitted_at: datetime
    graded_at: Optional[datetime] = None
    graded_by: Optional[int] = None
    feedback: Optional[str] = None
    answers: List[Answer]

    class Config:
        from_attributes = True

class PeerReviewBase(BaseModel):
    score: float = Field(..., ge=0)
    feedback: str = Field(..., min_length=1)

class PeerReviewCreate(PeerReviewBase):
    pass

class PeerReview(PeerReviewBase):
    id: int
    submission_id: int
    reviewer_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True 