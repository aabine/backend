from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from fastapi import HTTPException

from app.models.models import (
    Assessment, AssessmentSubmission, Answer,
    Course, User, GradeScale, GradeWeight,
    AssessmentType, StudentCourse
)
from app.schemas.grading import (
    GradeBookEntry, CourseGradeBook,
    StudentGrade
)

class GradingService:
    def __init__(self, db: Session):
        self.db = db

    async def calculate_grade(
        self,
        submission: AssessmentSubmission,
        grade_scale: GradeScale
    ) -> StudentGrade:
        """Calculate final grade for a submission using the course's grade scale."""
        # Calculate raw score
        total_points = sum(answer.points_earned or 0 for answer in submission.answers)
        max_points = submission.assessment.total_points
        raw_score = (total_points / max_points) * 100

        # Get grade weight for this assessment type
        weight = self.db.query(GradeWeight).filter(
            and_(
                GradeWeight.course_id == submission.assessment.course_id,
                GradeWeight.assessment_type == submission.assessment.assessment_type
            )
        ).first()

        weighted_score = raw_score * (weight.weight / 100) if weight else raw_score

        # Convert to letter grade based on scale
        letter_grade = None
        for grade, range_values in grade_scale.ranges.items():
            if range_values["min"] <= raw_score <= range_values["max"]:
                letter_grade = grade
                break

        return StudentGrade(
            student_id=submission.student_id,
            course_id=submission.assessment.course_id,
            assessment_type=submission.assessment.assessment_type,
            raw_score=raw_score,
            weighted_score=weighted_score,
            letter_grade=letter_grade,
            numeric_grade=raw_score,
            assessment_id=submission.assessment_id,
            graded_at=submission.graded_at or datetime.utcnow(),
            graded_by=submission.graded_by
        )

    async def get_course_gradebook(self, course_id: int) -> CourseGradeBook:
        """Get the complete gradebook for a course."""
        course = self.db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        # Get all assessments and submissions for the course
        assessments = self.db.query(Assessment).filter(
            Assessment.course_id == course_id
        ).all()

        submissions = self.db.query(AssessmentSubmission).filter(
            AssessmentSubmission.assessment_id.in_([a.id for a in assessments])
        ).all()

        # Get all students enrolled in the course
        students = self.db.query(User).join(
            StudentCourse
        ).filter(
            StudentCourse.course_id == course_id
        ).all()

        # Calculate grades for each student
        student_grades: List[GradeBookEntry] = []
        grade_distribution: Dict[str, int] = {}
        total_weighted_average = 0

        for student in students:
            student_submissions = [
                s for s in submissions if s.student_id == student.id
            ]
            
            assessment_scores = {}
            weighted_sum = 0
            weight_sum = 0

            for assessment in assessments:
                submission = next(
                    (s for s in student_submissions if s.assessment_id == assessment.id),
                    None
                )
                
                if submission and submission.score is not None:
                    weight = next(
                        (w.weight for w in course.grade_weights
                        if w.assessment_type == assessment.assessment_type),
                        0
                    )
                    
                    score = submission.score
                    assessment_scores[assessment.title] = score
                    weighted_sum += score * (weight / 100)
                    weight_sum += weight / 100

            weighted_average = weighted_sum / weight_sum if weight_sum > 0 else 0
            total_weighted_average += weighted_average

            # Calculate final letter grade
            final_grade = None
            for grade, range_values in course.grade_scale.ranges.items():
                if range_values["min"] <= weighted_average <= range_values["max"]:
                    final_grade = grade
                    grade_distribution[grade] = grade_distribution.get(grade, 0) + 1
                    break

            student_grades.append(GradeBookEntry(
                student_id=student.id,
                student_name=student.full_name,
                assessments=assessment_scores,
                weighted_average=weighted_average,
                final_grade=final_grade,
                last_graded=max(s.graded_at for s in student_submissions) if student_submissions else None
            ))

        class_average = total_weighted_average / len(students) if students else 0

        return CourseGradeBook(
            course_id=course_id,
            course_name=course.name,
            grade_scale=course.grade_scale,
            grade_weights=course.grade_weights,
            student_grades=student_grades,
            class_average=class_average,
            grade_distribution=grade_distribution
        )

    async def update_grade_weights(
        self,
        course_id: int,
        weights: Dict[AssessmentType, float]
    ) -> List[GradeWeight]:
        """Update grade weights for different assessment types in a course."""
        # Validate total weights equal 100%
        if sum(weights.values()) != 100:
            raise HTTPException(
                status_code=400,
                detail="Grade weights must sum to 100%"
            )

        # Delete existing weights
        self.db.query(GradeWeight).filter(
            GradeWeight.course_id == course_id
        ).delete()

        # Create new weights
        new_weights = []
        for assessment_type, weight in weights.items():
            grade_weight = GradeWeight(
                course_id=course_id,
                assessment_type=assessment_type,
                weight=weight
            )
            self.db.add(grade_weight)
            new_weights.append(grade_weight)

        await self.db.commit()
        return new_weights

    async def get_student_course_grade(
        self,
        student_id: int,
        course_id: int
    ) -> Dict[str, Any]:
        """Get detailed grade information for a student in a course."""
        # Get all submissions for the student in the course
        submissions = self.db.query(AssessmentSubmission).join(
            Assessment
        ).filter(
            and_(
                AssessmentSubmission.student_id == student_id,
                Assessment.course_id == course_id
            )
        ).all()

        if not submissions:
            return {
                "student_id": student_id,
                "course_id": course_id,
                "grades": [],
                "weighted_average": 0,
                "final_grade": None
            }

        course = self.db.query(Course).filter(Course.id == course_id).first()
        grades = []
        weighted_sum = 0
        weight_sum = 0

        for submission in submissions:
            grade = await self.calculate_grade(submission, course.grade_scale)
            grades.append(grade)
            
            weight = next(
                (w.weight for w in course.grade_weights
                if w.assessment_type == submission.assessment.assessment_type),
                0
            )
            
            weighted_sum += grade.raw_score * (weight / 100)
            weight_sum += weight / 100

        weighted_average = weighted_sum / weight_sum if weight_sum > 0 else 0

        # Calculate final letter grade
        final_grade = None
        for grade, range_values in course.grade_scale.ranges.items():
            if range_values["min"] <= weighted_average <= range_values["max"]:
                final_grade = grade
                break

        return {
            "student_id": student_id,
            "course_id": course_id,
            "grades": grades,
            "weighted_average": weighted_average,
            "final_grade": final_grade
        } 