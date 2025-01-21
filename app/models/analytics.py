from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base
from app.schemas.analytics import MetricType, TimeFrame

class StudentProgress(Base):
    __tablename__ = "student_progress"

    student_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("course.id"), nullable=False)
    completed_items = Column(Integer, default=0)
    total_items = Column(Integer, default=0)
    completion_rate = Column(Float, default=0.0)
    last_activity = Column(DateTime, default=datetime.utcnow)
    current_module = Column(String)
    time_spent = Column(Integer, default=0)  # in minutes

    # Relationships
    student = relationship("User", back_populates="progress_metrics")
    course = relationship("Course", back_populates="student_progress")

class PerformanceMetrics(Base):
    __tablename__ = "performance_metrics"

    student_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("course.id"), nullable=False)
    average_score = Column(Float, default=0.0)
    highest_score = Column(Float, default=0.0)
    lowest_score = Column(Float, default=0.0)
    assessments_taken = Column(Integer, default=0)
    improvement_rate = Column(Float)
    strengths = Column(JSON, default=list)
    areas_for_improvement = Column(JSON, default=list)

    # Relationships
    student = relationship("User", back_populates="performance_metrics")
    course = relationship("Course", back_populates="performance_metrics")

class EngagementMetrics(Base):
    __tablename__ = "engagement_metrics"

    student_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("course.id"), nullable=False)
    login_frequency = Column(Integer, default=0)
    average_session_duration = Column(Integer, default=0)  # in minutes
    content_interactions = Column(Integer, default=0)
    discussion_participation = Column(Integer, default=0)
    last_login = Column(DateTime, default=datetime.utcnow)
    activity_streak = Column(Integer, default=0)
    completion_rate = Column(Float, default=0.0)

    # Relationships
    student = relationship("User", back_populates="engagement_metrics")
    course = relationship("Course", back_populates="engagement_metrics")

class LearningActivity(Base):
    __tablename__ = "learning_activity"

    student_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("course.id"), nullable=False)
    activity_type = Column(String, nullable=False)  # e.g., "content_view", "assessment", "discussion"
    module_id = Column(Integer, ForeignKey("module.id"))
    duration = Column(Integer, default=0)  # in minutes
    score = Column(Float)
    activity_data = Column(JSON)

    # Relationships
    student = relationship("User", back_populates="learning_activities")
    course = relationship("Course", back_populates="learning_activities")
    module = relationship("Module", back_populates="learning_activities") 