from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.models.models import (
    User, Course, Module, LearningActivity,
    StudentProgress, PerformanceMetrics,
    EngagementMetrics
)
from app.schemas.analytics import (
    StudentAnalytics, CourseAnalytics,
    StudentProgressReport, AnalyticsRequest,
    MetricType, TimeFrame
)
import logging

logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    async def track_learning_activity(
        self,
        student_id: int,
        course_id: int,
        activity_type: str,
        module_id: Optional[int] = None,
        duration: Optional[int] = None,
        score: Optional[float] = None,
        metadata: Optional[Dict] = None
    ) -> LearningActivity:
        """Track a learning activity and update related metrics."""
        try:
            # Create activity record
            activity = LearningActivity(
                student_id=student_id,
                course_id=course_id,
                activity_type=activity_type,
                module_id=module_id,
                duration=duration,
                score=score,
                metadata=metadata
            )
            self.db.add(activity)

            # Update engagement metrics
            engagement = self.db.query(EngagementMetrics).filter(
                EngagementMetrics.student_id == student_id,
                EngagementMetrics.course_id == course_id
            ).first()

            if not engagement:
                engagement = EngagementMetrics(
                    student_id=student_id,
                    course_id=course_id
                )
                self.db.add(engagement)

            engagement.content_interactions += 1
            engagement.last_login = datetime.utcnow()
            if duration:
                engagement.average_session_duration = (
                    (engagement.average_session_duration * engagement.content_interactions + duration) /
                    (engagement.content_interactions + 1)
                )

            # Update progress metrics if applicable
            if activity_type in ["content_view", "assessment_complete"]:
                await self._update_progress_metrics(student_id, course_id)

            # Update performance metrics if score is provided
            if score is not None:
                await self._update_performance_metrics(student_id, course_id, score)

            await self.db.commit()
            return activity

        except Exception as e:
            logger.error(f"Error tracking learning activity: {str(e)}")
            await self.db.rollback()
            raise

    async def get_student_analytics(
        self,
        student_id: int,
        course_id: Optional[int] = None,
        time_frame: TimeFrame = TimeFrame.ALL
    ) -> StudentAnalytics:
        """Get comprehensive analytics for a student."""
        try:
            filters = [StudentProgress.student_id == student_id]
            if course_id:
                filters.append(StudentProgress.course_id == course_id)

            progress = self.db.query(StudentProgress).filter(*filters).first()
            performance = self.db.query(PerformanceMetrics).filter(*filters).first()
            engagement = self.db.query(EngagementMetrics).filter(*filters).first()

            if not all([progress, performance, engagement]):
                raise ValueError("Analytics data not found for student")

            return StudentAnalytics(
                student_id=student_id,
                course_id=course_id,
                progress=progress,
                performance=performance,
                engagement=engagement,
                updated_at=datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"Error getting student analytics: {str(e)}")
            raise

    async def get_course_analytics(self, course_id: int) -> CourseAnalytics:
        """Get comprehensive analytics for a course."""
        try:
            # Get basic metrics
            total_students = self.db.query(func.count(StudentProgress.student_id))\
                .filter(StudentProgress.course_id == course_id).scalar()

            active_students = self.db.query(func.count(EngagementMetrics.student_id))\
                .filter(
                    EngagementMetrics.course_id == course_id,
                    EngagementMetrics.last_login >= datetime.utcnow() - timedelta(days=30)
                ).scalar()

            # Calculate averages
            avg_progress = self.db.query(func.avg(StudentProgress.completion_rate))\
                .filter(StudentProgress.course_id == course_id).scalar() or 0.0

            avg_performance = self.db.query(func.avg(PerformanceMetrics.average_score))\
                .filter(PerformanceMetrics.course_id == course_id).scalar() or 0.0

            avg_engagement = self.db.query(func.avg(EngagementMetrics.completion_rate))\
                .filter(EngagementMetrics.course_id == course_id).scalar() or 0.0

            # Identify at-risk and top-performing students
            at_risk = self.db.query(func.count(PerformanceMetrics.student_id))\
                .filter(
                    PerformanceMetrics.course_id == course_id,
                    PerformanceMetrics.average_score < 60
                ).scalar()

            top_performing = self.db.query(func.count(PerformanceMetrics.student_id))\
                .filter(
                    PerformanceMetrics.course_id == course_id,
                    PerformanceMetrics.average_score >= 90
                ).scalar()

            return CourseAnalytics(
                course_id=course_id,
                total_students=total_students,
                active_students=active_students,
                average_progress=avg_progress,
                average_performance=avg_performance,
                average_engagement=avg_engagement,
                completion_rate=avg_progress,
                at_risk_students=at_risk,
                top_performing_students=top_performing,
                updated_at=datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"Error getting course analytics: {str(e)}")
            raise

    async def generate_student_progress_report(
        self,
        student_id: int,
        time_frame: TimeFrame = TimeFrame.ALL
    ) -> StudentProgressReport:
        """Generate a comprehensive progress report for a student."""
        try:
            # Get student information
            student = self.db.query(User).filter(User.id == student_id).first()
            if not student:
                raise ValueError("Student not found")

            # Get course progress
            courses = []
            for enrollment in student.enrollments:
                progress = self.db.query(StudentProgress)\
                    .filter(
                        StudentProgress.student_id == student_id,
                        StudentProgress.course_id == enrollment.course_id
                    ).first()

                performance = self.db.query(PerformanceMetrics)\
                    .filter(
                        PerformanceMetrics.student_id == student_id,
                        PerformanceMetrics.course_id == enrollment.course_id
                    ).first()

                if progress and performance:
                    courses.append({
                        "course_id": enrollment.course_id,
                        "course_name": enrollment.course.name,
                        "progress": progress.completion_rate,
                        "performance": performance.average_score,
                        "last_activity": progress.last_activity
                    })

            # Get learning paths progress
            learning_paths = []
            # Implementation for learning paths...

            # Get recent activities
            recent_activities = self.db.query(LearningActivity)\
                .filter(LearningActivity.student_id == student_id)\
                .order_by(LearningActivity.created_at.desc())\
                .limit(10)\
                .all()

            activities = [{
                "type": activity.activity_type,
                "course": activity.course.name,
                "timestamp": activity.created_at,
                "details": activity.metadata
            } for activity in recent_activities]

            # Generate recommendations
            recommendations = await self._generate_recommendations(student_id)

            return StudentProgressReport(
                student_id=student_id,
                student_name=f"{student.first_name} {student.last_name}",
                enrollment_date=student.created_at,
                courses=courses,
                overall_progress=sum(c["progress"] for c in courses) / len(courses) if courses else 0,
                overall_performance=sum(c["performance"] for c in courses) / len(courses) if courses else 0,
                learning_paths=learning_paths,
                recent_activities=activities,
                recommendations=recommendations
            )

        except Exception as e:
            logger.error(f"Error generating student progress report: {str(e)}")
            raise

    async def _update_progress_metrics(self, student_id: int, course_id: int):
        """Update progress metrics for a student in a course."""
        progress = self.db.query(StudentProgress)\
            .filter(
                StudentProgress.student_id == student_id,
                StudentProgress.course_id == course_id
            ).first()

        if not progress:
            progress = StudentProgress(
                student_id=student_id,
                course_id=course_id
            )
            self.db.add(progress)

        # Update metrics based on completed activities
        completed_items = self.db.query(func.count(LearningActivity.id))\
            .filter(
                LearningActivity.student_id == student_id,
                LearningActivity.course_id == course_id,
                LearningActivity.activity_type.in_(["content_view", "assessment_complete"])
            ).scalar()

        total_items = self.db.query(func.count(Module.id))\
            .join(Course)\
            .filter(Course.id == course_id)\
            .scalar()

        progress.completed_items = completed_items
        progress.total_items = total_items
        progress.completion_rate = (completed_items / total_items) if total_items > 0 else 0
        progress.last_activity = datetime.utcnow()

    async def _update_performance_metrics(self, student_id: int, course_id: int, new_score: float):
        """Update performance metrics for a student in a course."""
        performance = self.db.query(PerformanceMetrics)\
            .filter(
                PerformanceMetrics.student_id == student_id,
                PerformanceMetrics.course_id == course_id
            ).first()

        if not performance:
            performance = PerformanceMetrics(
                student_id=student_id,
                course_id=course_id,
                highest_score=new_score,
                lowest_score=new_score,
                average_score=new_score,
                assessments_taken=1
            )
            self.db.add(performance)
        else:
            performance.highest_score = max(performance.highest_score, new_score)
            performance.lowest_score = min(performance.lowest_score, new_score)
            performance.average_score = (
                (performance.average_score * performance.assessments_taken + new_score) /
                (performance.assessments_taken + 1)
            )
            performance.assessments_taken += 1

    async def _generate_recommendations(self, student_id: int) -> List[str]:
        """Generate personalized learning recommendations for a student."""
        recommendations = []
        # Implementation for generating recommendations...
        return recommendations 