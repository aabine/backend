from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, JSON, Enum, DateTime, Float
from sqlalchemy.orm import relationship
import enum
from .base import Base
from datetime import datetime

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"
    PARENT = "parent"

class User(Base):
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    role = Column(Enum(UserRole), nullable=False)
    is_active = Column(Boolean, default=True)
    school_id = Column(Integer, ForeignKey("school.id"))
    
    school = relationship("School", back_populates="users")
    courses = relationship("Course", back_populates="teacher")
    student_courses = relationship("StudentCourse", back_populates="student")
    audit_logs = relationship("AuditLog", back_populates="user")
    permissions = Column(JSON, default=lambda: {})
    last_login = Column(DateTime)
    login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime)
    password_changed_at = Column(DateTime)
    require_password_change = Column(Boolean, default=False)
    suspended_until = Column(DateTime)
    suspension_reason = Column(String)
    deleted_at = Column(DateTime)
    deletion_reason = Column(String)

class School(Base):
    name = Column(String, nullable=False)
    description = Column(Text)
    configuration = Column(JSON)
    api_key = Column(String, unique=True)
    subscription_type = Column(String)
    subscription_expires_at = Column(DateTime)
    max_users = Column(Integer)
    features_enabled = Column(JSON, default=lambda: {})
    contact_email = Column(String)
    contact_phone = Column(String)
    address = Column(JSON)
    settings = Column(JSON, default=lambda: {})
    is_active = Column(Boolean, default=True)
    suspended_until = Column(DateTime)
    suspension_reason = Column(String)
    allow_data_access = Column(Boolean, default=True)
    deleted_at = Column(DateTime)
    deletion_reason = Column(String)
    permanent_deletion_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    users = relationship("User", back_populates="school")
    courses = relationship("Course", back_populates="school")
    ai_modules = relationship("AIModule", back_populates="school")

class Course(Base):
    name = Column(String, nullable=False)
    description = Column(Text)
    teacher_id = Column(Integer, ForeignKey("user.id"))
    school_id = Column(Integer, ForeignKey("school.id"))
    
    teacher = relationship("User", back_populates="courses")
    school = relationship("School", back_populates="courses")
    students = relationship("StudentCourse", back_populates="course")
    learning_materials = relationship("LearningMaterial", back_populates="course")
    modules = relationship("Module", back_populates="course")
    assessments = relationship("Assessment", back_populates="course")

class StudentCourse(Base):
    student_id = Column(Integer, ForeignKey("user.id"))
    course_id = Column(Integer, ForeignKey("course.id"))
    progress = Column(JSON)
    
    student = relationship("User", back_populates="student_courses")
    course = relationship("Course", back_populates="students")

class LearningMaterial(Base):
    title = Column(String, nullable=False)
    content = Column(Text)
    material_type = Column(String)
    course_id = Column(Integer, ForeignKey("course.id"))
    ai_enhanced = Column(Boolean, default=False)
    
    course = relationship("Course", back_populates="learning_materials")

class AIModule(Base):
    name = Column(String, nullable=False)
    description = Column(Text)
    module_type = Column(String)
    configuration = Column(JSON)
    school_id = Column(Integer, ForeignKey("school.id"))
    is_active = Column(Boolean, default=True)
    
    school = relationship("School", back_populates="ai_modules")

class Module(Base):
    __tablename__ = "module"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    course_id = Column(Integer, ForeignKey("course.id"), nullable=False)
    order = Column(Integer)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    course = relationship("Course", back_populates="modules")
    learning_activities = relationship("LearningActivity", back_populates="module")

class LearningActivity(Base):
    __tablename__ = "learning_activity"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    module_id = Column(Integer, ForeignKey("module.id"), nullable=False)
    activity_type = Column(String, nullable=False)
    activity_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")
    module = relationship("Module", back_populates="learning_activities")

class StudentProgress(Base):
    __tablename__ = "student_progress"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("course.id"), nullable=False)
    completion_rate = Column(Integer, default=0)
    last_activity = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    student = relationship("User")
    course = relationship("Course")

class PerformanceMetrics(Base):
    __tablename__ = "performance_metrics"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("course.id"), nullable=False)
    average_score = Column(Integer, default=0)
    assessments_completed = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    student = relationship("User")
    course = relationship("Course")

class EngagementMetrics(Base):
    __tablename__ = "engagement_metrics"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("course.id"), nullable=False)
    content_interactions = Column(Integer, default=0)
    average_session_duration = Column(Integer, default=0)  # in seconds
    last_login = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    student = relationship("User")
    course = relationship("Course")

class Notification(Base):
    __tablename__ = "notification"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text)
    notification_type = Column(String, nullable=False)  # e.g., "message", "forum", "classroom"
    reference_id = Column(Integer)  # ID of the related item (message, post, etc.)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="notifications")

class DiscussionForum(Base):
    __tablename__ = "discussion_forum"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    course_id = Column(Integer, ForeignKey("course.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("user.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    course = relationship("Course", back_populates="forums")
    creator = relationship("User")
    posts = relationship("ForumPost", back_populates="forum")

class ForumPost(Base):
    __tablename__ = "forum_post"

    id = Column(Integer, primary_key=True, index=True)
    forum_id = Column(Integer, ForeignKey("discussion_forum.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("forum_post.id"))  # For replies
    content = Column(Text, nullable=False)
    created_by = Column(Integer, ForeignKey("user.id"), nullable=False)
    is_pinned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    forum = relationship("DiscussionForum", back_populates="posts")
    creator = relationship("User")
    parent = relationship("ForumPost", remote_side=[id], back_populates="replies")
    replies = relationship("ForumPost", back_populates="parent")

class Message(Base):
    __tablename__ = "message"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])

class VirtualClassroom(Base):
    __tablename__ = "virtual_classroom"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("course.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    meeting_url = Column(String)  # URL for the virtual meeting
    scheduled_start = Column(DateTime, nullable=False)
    scheduled_end = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("user.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    course = relationship("Course", back_populates="virtual_classrooms")
    creator = relationship("User")
    participants = relationship("ClassroomParticipant", back_populates="classroom")
    chat_messages = relationship("ClassroomChat", back_populates="classroom")

class ClassroomParticipant(Base):
    __tablename__ = "classroom_participant"

    id = Column(Integer, primary_key=True, index=True)
    classroom_id = Column(Integer, ForeignKey("virtual_classroom.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)
    left_at = Column(DateTime)
    is_present = Column(Boolean, default=True)

    # Relationships
    classroom = relationship("VirtualClassroom", back_populates="participants")
    user = relationship("User")

class ClassroomChat(Base):
    __tablename__ = "classroom_chat"

    id = Column(Integer, primary_key=True, index=True)
    classroom_id = Column(Integer, ForeignKey("virtual_classroom.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    classroom = relationship("VirtualClassroom", back_populates="chat_messages")
    user = relationship("User")

class AssessmentType(str, enum.Enum):
    QUIZ = "quiz"
    EXAM = "exam"
    ASSIGNMENT = "assignment"

class QuestionType(str, enum.Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"
    FILE_UPLOAD = "file_upload"

class Assessment(Base):
    __tablename__ = "assessment"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    course_id = Column(Integer, ForeignKey("course.id"), nullable=False)
    assessment_type = Column(Enum(AssessmentType), nullable=False)
    total_points = Column(Integer, default=100)
    passing_score = Column(Integer)
    due_date = Column(DateTime)
    requires_peer_review = Column(Boolean, default=False)
    peer_reviews_required = Column(Integer, default=0)
    created_by = Column(Integer, ForeignKey("user.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    course = relationship("Course")
    creator = relationship("User", foreign_keys=[created_by])
    questions = relationship("Question", back_populates="assessment")
    submissions = relationship("AssessmentSubmission", back_populates="assessment")

class Question(Base):
    __tablename__ = "question"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessment.id"), nullable=False)
    question_type = Column(Enum(QuestionType), nullable=False)
    content = Column(Text, nullable=False)
    options = Column(JSON)  # For multiple choice questions
    correct_answer = Column(Text)  # For auto-gradable questions
    points = Column(Integer, default=1)
    order = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    assessment = relationship("Assessment", back_populates="questions")
    answers = relationship("Answer", back_populates="question")

class AssessmentSubmission(Base):
    __tablename__ = "assessment_submission"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessment.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    status = Column(String, default="submitted")  # submitted, graded, peer_review_pending
    score = Column(Float)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    graded_at = Column(DateTime)
    graded_by = Column(Integer, ForeignKey("user.id"))
    feedback = Column(Text)

    # Relationships
    assessment = relationship("Assessment", back_populates="submissions")
    student = relationship("User", foreign_keys=[student_id])
    grader = relationship("User", foreign_keys=[graded_by])
    answers = relationship("Answer", back_populates="submission")
    peer_reviews = relationship("PeerReview", back_populates="submission")

class Answer(Base):
    __tablename__ = "answer"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("assessment_submission.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("question.id"), nullable=False)
    answer_content = Column(Text)
    file_url = Column(String)  # For file upload questions
    points_earned = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    submission = relationship("AssessmentSubmission", back_populates="answers")
    question = relationship("Question", back_populates="answers")

class PeerReview(Base):
    __tablename__ = "peer_review"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("assessment_submission.id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    score = Column(Float)
    feedback = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    submission = relationship("AssessmentSubmission", back_populates="peer_reviews")
    reviewer = relationship("User")

class AuditActionType(str, enum.Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    ROLE_CHANGE = "role_change"
    PERMISSION_CHANGE = "permission_change"
    SETTINGS_CHANGE = "settings_change"

class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    action = Column(Enum(AuditActionType), nullable=False)
    entity_type = Column(String, nullable=False)  # e.g., "user", "school", "course"
    entity_id = Column(Integer)
    old_values = Column(JSON)
    new_values = Column(JSON)
    ip_address = Column(String)
    user_agent = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="audit_logs") 