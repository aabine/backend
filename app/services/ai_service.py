from typing import Dict, Any, List, Optional
import openai
from app.core.config import settings
from app.models.models import LearningMaterial, StudentCourse, Course, User
from sqlalchemy.orm import Session
import json
from app.core.cache import cache_service

class AIService:
    def __init__(self, db: Session):
        self.db = db
        openai.api_key = settings.OPENAI_API_KEY

    async def _get_cached_response(
        self,
        cache_key: str,
        operation: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Get cached response or generate new one."""
        # Try to get from cache first
        cached_response = await cache_service.get(cache_key)
        if cached_response:
            return cached_response

        # Generate new response based on operation
        try:
            if operation == "chat_completion":
                response = await openai.ChatCompletion.create(**kwargs)
                result = response.choices[0].message.content
            else:
                raise ValueError(f"Unknown operation: {operation}")

            # Cache the result
            await cache_service.set(cache_key, result)
            return result
        except Exception as e:
            raise Exception(f"Error in AI operation: {str(e)}")

    async def enhance_learning_material(
        self,
        material: LearningMaterial,
        enhancement_type: str,
        school_config: Dict[str, Any]
    ) -> str:
        """
        Enhance learning material content using AI with caching.
        """
        cache_key = cache_service._generate_cache_key(
            "enhance_material",
            content=material.content,
            enhancement_type=enhancement_type
        )

        system_prompt = (
            "You are an expert educational content enhancer. "
            "Your task is to improve educational content while maintaining accuracy "
            "and adapting to the student's learning level."
        )

        enhancement_prompts = {
            "simplify": "Simplify this content while maintaining its educational value:",
            "elaborate": "Provide more detailed explanations and examples for this content:",
            "interactive": "Transform this content into an interactive format with questions and exercises:",
            "differentiate": "Adapt this content for different learning levels (basic, intermediate, advanced):",
        }

        try:
            return await self._get_cached_response(
                cache_key,
                "chat_completion",
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"{enhancement_prompts.get(enhancement_type, enhancement_prompts['elaborate'])}\n\n{material.content}"}
                ],
                temperature=0.7,
            )
        except Exception as e:
            raise Exception(f"Error enhancing content: {str(e)}")

    async def generate_personalized_recommendations(
        self,
        student: User,
        course: Course
    ) -> Dict[str, Any]:
        """
        Generate personalized learning recommendations with caching.
        """
        enrollment = (
            self.db.query(StudentCourse)
            .filter(
                StudentCourse.student_id == student.id,
                StudentCourse.course_id == course.id
            )
            .first()
        )

        if not enrollment:
            raise Exception("Student not enrolled in this course")

        materials = (
            self.db.query(LearningMaterial)
            .filter(LearningMaterial.course_id == course.id)
            .all()
        )

        context = {
            "progress": enrollment.progress,
            "available_materials": [
                {"title": m.title, "type": m.material_type}
                for m in materials
            ],
            "course_name": course.name,
        }

        cache_key = cache_service._generate_cache_key(
            "recommendations",
            student_id=student.id,
            course_id=course.id,
            progress_hash=hash(json.dumps(enrollment.progress))
        )

        try:
            recommendations = await self._get_cached_response(
                cache_key,
                "chat_completion",
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an AI educational advisor specialized in personalized learning. "
                            "Analyze the student's progress and provide specific recommendations "
                            "for improvement and next steps."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Based on this student's progress and available materials, provide personalized learning recommendations:\n\n{json.dumps(context, indent=2)}"
                    }
                ],
                temperature=0.7,
            )

            return {
                "student_id": student.id,
                "course_id": course.id,
                "recommendations": recommendations,
                "context": context
            }
        except Exception as e:
            raise Exception(f"Error generating recommendations: {str(e)}")

    async def analyze_learning_patterns(
        self,
        course: Course,
        timeframe: Optional[str] = "all"
    ) -> Dict[str, Any]:
        """
        Analyze learning patterns and engagement in a course.
        """
        # Get all enrollments for the course
        enrollments = (
            self.db.query(StudentCourse)
            .filter(StudentCourse.course_id == course.id)
            .all()
        )

        progress_data = [
            {
                "student_id": e.student_id,
                "progress": e.progress,
            }
            for e in enrollments
        ]

        system_prompt = (
            "You are an AI educational analyst specialized in learning patterns. "
            "Analyze the course data to identify patterns, trends, and areas for improvement."
        )

        try:
            response = await openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": (
                            "Analyze this course data and provide insights on:\n"
                            "1. Common learning patterns\n"
                            "2. Engagement levels\n"
                            "3. Areas where students are struggling\n"
                            "4. Recommendations for course improvement\n\n"
                            f"{json.dumps(progress_data, indent=2)}"
                        )
                    }
                ],
                temperature=0.7,
            )

            analysis = response.choices[0].message.content
            return {
                "course_id": course.id,
                "analysis": analysis,
                "raw_data": progress_data,
                "timeframe": timeframe
            }
        except Exception as e:
            raise Exception(f"Error analyzing learning patterns: {str(e)}")

    async def generate_adaptive_assessment(
        self,
        material: LearningMaterial,
        student_level: str = "intermediate"
    ) -> Dict[str, Any]:
        """
        Generate adaptive assessments based on learning material and student level.
        """
        system_prompt = (
            "You are an AI assessment generator specialized in creating "
            "educational assessments that adapt to student levels. "
            "Create engaging and effective questions that test understanding."
        )

        try:
            response = await openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": (
                            f"Create an adaptive assessment for this content at {student_level} level. "
                            "Include a mix of multiple choice, short answer, and analytical questions:\n\n"
                            f"{material.content}"
                        )
                    }
                ],
                temperature=0.7,
            )

            assessment = response.choices[0].message.content
            return {
                "material_id": material.id,
                "student_level": student_level,
                "assessment": assessment
            }
        except Exception as e:
            raise Exception(f"Error generating assessment: {str(e)}")

    async def provide_learning_insights(
        self,
        student: User,
        timeframe: str = "last_month"
    ) -> Dict[str, Any]:
        """
        Provide comprehensive learning insights for a student across all courses.
        """
        # Get all student enrollments
        enrollments = (
            self.db.query(StudentCourse)
            .filter(StudentCourse.student_id == student.id)
            .all()
        )

        learning_data = []
        for enrollment in enrollments:
            course = (
                self.db.query(Course)
                .filter(Course.id == enrollment.course_id)
                .first()
            )
            learning_data.append({
                "course_name": course.name,
                "progress": enrollment.progress,
            })

        system_prompt = (
            "You are an AI learning analyst specialized in student performance. "
            "Provide comprehensive insights about the student's learning journey, "
            "including strengths, areas for improvement, and actionable recommendations."
        )

        try:
            response = await openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": (
                            "Analyze this student's learning data and provide insights on:\n"
                            "1. Overall progress and performance\n"
                            "2. Learning strengths and preferences\n"
                            "3. Areas needing attention\n"
                            "4. Personalized recommendations\n\n"
                            f"{json.dumps(learning_data, indent=2)}"
                        )
                    }
                ],
                temperature=0.7,
            )

            insights = response.choices[0].message.content
            return {
                "student_id": student.id,
                "insights": insights,
                "raw_data": learning_data,
                "timeframe": timeframe
            }
        except Exception as e:
            raise Exception(f"Error generating learning insights: {str(e)}")

    async def generate_curriculum_plan(
        self,
        course: Course,
        learning_objectives: List[str],
        duration_weeks: int,
        student_level: str = "intermediate"
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive curriculum plan using AI.
        """
        system_prompt = (
            "You are an expert curriculum designer specialized in creating "
            "engaging and effective educational plans. Design a curriculum "
            "that meets learning objectives while maintaining student engagement."
        )

        context = {
            "course_name": course.name,
            "objectives": learning_objectives,
            "duration_weeks": duration_weeks,
            "student_level": student_level,
        }

        try:
            response = await openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": (
                            "Create a detailed curriculum plan including:\n"
                            "1. Weekly learning objectives\n"
                            "2. Recommended activities and materials\n"
                            "3. Assessment strategies\n"
                            "4. Engagement techniques\n\n"
                            f"{json.dumps(context, indent=2)}"
                        )
                    }
                ],
                temperature=0.7,
            )

            curriculum_plan = response.choices[0].message.content
            return {
                "course_id": course.id,
                "curriculum_plan": curriculum_plan,
                "context": context
            }
        except Exception as e:
            raise Exception(f"Error generating curriculum plan: {str(e)}")

    async def analyze_student_engagement(
        self,
        course: Course,
        timeframe: str = "last_month",
        include_recommendations: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze student engagement patterns and provide improvement strategies.
        """
        enrollments = (
            self.db.query(StudentCourse)
            .filter(StudentCourse.course_id == course.id)
            .all()
        )

        engagement_data = []
        for enrollment in enrollments:
            student = (
                self.db.query(User)
                .filter(User.id == enrollment.student_id)
                .first()
            )
            engagement_data.append({
                "student_name": student.full_name,
                "progress": enrollment.progress,
                "last_activity": enrollment.progress.get("last_activity", "unknown"),
                "completion_rate": enrollment.progress.get("completion_rate", 0),
                "interaction_frequency": enrollment.progress.get("interaction_frequency", "low")
            })

        system_prompt = (
            "You are an AI engagement analyst specialized in educational platforms. "
            "Analyze student engagement patterns and provide actionable strategies "
            "for improving student participation and motivation."
        )

        try:
            response = await openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": (
                            "Analyze this engagement data and provide insights on:\n"
                            "1. Overall engagement patterns\n"
                            "2. Risk factors and early warning signs\n"
                            "3. Success patterns\n"
                            "4. Recommended engagement strategies\n\n"
                            f"{json.dumps(engagement_data, indent=2)}"
                        )
                    }
                ],
                temperature=0.7,
            )

            analysis = response.choices[0].message.content
            return {
                "course_id": course.id,
                "engagement_analysis": analysis,
                "raw_data": engagement_data,
                "timeframe": timeframe
            }
        except Exception as e:
            raise Exception(f"Error analyzing engagement: {str(e)}")

    async def generate_automated_feedback(
        self,
        student: User,
        material: LearningMaterial,
        submission_content: str,
        feedback_type: str = "comprehensive"
    ) -> Dict[str, Any]:
        """
        Generate personalized automated feedback for student submissions.
        """
        system_prompt = (
            "You are an AI educational feedback generator specialized in providing "
            "constructive, encouraging, and actionable feedback to students. "
            "Focus on both strengths and areas for improvement."
        )

        feedback_prompts = {
            "comprehensive": "Provide detailed feedback covering all aspects of the submission",
            "quick": "Provide brief, focused feedback on the most important aspects",
            "conceptual": "Focus feedback on understanding of core concepts",
            "technical": "Focus feedback on technical accuracy and implementation"
        }

        context = {
            "material_title": material.title,
            "material_type": material.material_type,
            "submission": submission_content
        }

        try:
            response = await openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": (
                            f"{feedback_prompts.get(feedback_type, feedback_prompts['comprehensive'])}:\n\n"
                            f"Material: {material.content}\n\n"
                            f"Student Submission: {submission_content}"
                        )
                    }
                ],
                temperature=0.7,
            )

            feedback = response.choices[0].message.content
            return {
                "student_id": student.id,
                "material_id": material.id,
                "feedback": feedback,
                "feedback_type": feedback_type,
                "context": context
            }
        except Exception as e:
            raise Exception(f"Error generating feedback: {str(e)}")

    async def predict_student_performance(
        self,
        student: User,
        course: Course,
        prediction_horizon: str = "end_of_course"
    ) -> Dict[str, Any]:
        """
        Predict student performance and identify intervention needs.
        """
        # Get student's current progress
        enrollment = (
            self.db.query(StudentCourse)
            .filter(
                StudentCourse.student_id == student.id,
                StudentCourse.course_id == course.id
            )
            .first()
        )

        if not enrollment:
            raise Exception("Student not enrolled in this course")

        # Get historical performance data
        historical_data = {
            "current_progress": enrollment.progress,
            "past_performances": [],  # You would populate this from historical data
            "engagement_metrics": {
                "attendance": enrollment.progress.get("attendance", 0),
                "participation": enrollment.progress.get("participation", 0),
                "assignment_completion": enrollment.progress.get("assignment_completion", 0)
            }
        }

        system_prompt = (
            "You are an AI educational forecasting specialist. "
            "Analyze student data to predict future performance and identify "
            "potential challenges or support needs."
        )

        try:
            response = await openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": (
                            f"Based on this student's data, predict their performance for {prediction_horizon} and provide:\n"
                            "1. Performance prediction\n"
                            "2. Risk assessment\n"
                            "3. Early intervention recommendations\n"
                            "4. Success strategies\n\n"
                            f"{json.dumps(historical_data, indent=2)}"
                        )
                    }
                ],
                temperature=0.7,
            )

            prediction = response.choices[0].message.content
            return {
                "student_id": student.id,
                "course_id": course.id,
                "prediction": prediction,
                "confidence_level": "medium",  # You could calculate this based on data quality
                "prediction_horizon": prediction_horizon,
                "raw_data": historical_data
            }
        except Exception as e:
            raise Exception(f"Error predicting performance: {str(e)}")

    async def generate_concept_map(
        self,
        material: LearningMaterial,
        complexity_level: str = "intermediate"
    ) -> Dict[str, Any]:
        """
        Generate a concept map for learning material.
        """
        system_prompt = (
            "You are an AI educational content mapper specialized in creating "
            "clear and organized concept maps. Break down complex topics into "
            "interconnected concepts and relationships."
        )

        try:
            response = await openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": (
                            f"Create a concept map for this content at {complexity_level} level. "
                            "Include:\n"
                            "1. Main concepts\n"
                            "2. Relationships between concepts\n"
                            "3. Prerequisites\n"
                            "4. Learning outcomes\n\n"
                            f"{material.content}"
                        )
                    }
                ],
                temperature=0.7,
            )

            concept_map = response.choices[0].message.content
            return {
                "material_id": material.id,
                "concept_map": concept_map,
                "complexity_level": complexity_level
            }
        except Exception as e:
            raise Exception(f"Error generating concept map: {str(e)}")

    async def invalidate_cache(self, pattern: str) -> bool:
        """
        Invalidate cache for a specific pattern.
        """
        return await cache_service.clear_pattern(pattern) 