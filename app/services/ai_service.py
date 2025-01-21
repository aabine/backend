from typing import Dict, Any, List, Optional
import openai
from app.core.config import settings
from app.models.models import LearningMaterial, StudentCourse, Course, User
from sqlalchemy.orm import Session
import json
from app.core.cache import cache_service
from circuitbreaker import circuit, CircuitBreakerError
import httpx
import asyncio
import logging
from prometheus_client import Counter, Histogram
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog
import backoff

# Initialize metrics
AI_REQUEST_COUNTER = Counter('ai_requests_total', 'Total number of AI API requests', ['operation'])
AI_REQUEST_LATENCY = Histogram('ai_request_duration_seconds', 'AI request latency', ['operation'])
AI_ERROR_COUNTER = Counter('ai_errors_total', 'Total number of AI API errors', ['operation', 'error_type'])

logger = structlog.get_logger(__name__)

class AIServiceError(Exception):
    """Base exception for AI service errors."""
    pass

class AIService:
    def __init__(self, db: Session):
        self.db = db
        self.client = httpx.AsyncClient(timeout=30.0)  # 30 second timeout
        self.openai_client = openai.AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=30.0
        )
        self.logger = logger.bind(service="ai_service")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    @circuit(failure_threshold=5, recovery_timeout=60)
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _make_ai_request(self, operation: str, **kwargs) -> Dict[str, Any]:
        """
        Make an AI API request with circuit breaker and retry logic.
        """
        cache_key = cache_service._generate_cache_key(f"ai:{operation}", **kwargs)
        cached_result = await cache_service.get(cache_key)
        
        if cached_result:
            self.logger.info("cache_hit", operation=operation)
            return cached_result

        try:
            with AI_REQUEST_LATENCY.labels(operation=operation).time():
                AI_REQUEST_COUNTER.labels(operation=operation).inc()
                
                # Check cache first
                cache_key = f"ai_request:{operation}:{hash(str(kwargs))}"
                cached_result = await cache_service.get(cache_key)
                if cached_result:
                    return cached_result

                # Make API call
                response = await self.openai_client.chat.completions.create(**kwargs)
                
                # Cache successful response
                result = response.choices[0].message.content
                await cache_service.set(cache_key, result, ttl=3600)  # Cache for 1 hour
                return result

        except openai.APITimeoutError as e:
            AI_ERROR_COUNTER.labels(operation=operation, error_type='timeout').inc()
            self.logger.error(f"AI request timeout for {operation}: {str(e)}")
            raise AIServiceError(f"Request timeout: {str(e)}")
        except openai.APIError as e:
            AI_ERROR_COUNTER.labels(operation=operation, error_type='api_error').inc()
            self.logger.error(f"AI API error for {operation}: {str(e)}")
            raise AIServiceError(f"API error: {str(e)}")
        except CircuitBreakerError as e:
            AI_ERROR_COUNTER.labels(operation=operation, error_type='circuit_breaker').inc()
            self.logger.error(f"Circuit breaker open for {operation}: {str(e)}")
            # Return cached result if available, otherwise raise
            cached_result = await cache_service.get(cache_key)
            if cached_result:
                self.logger.info(f"Using cached result for {operation} due to circuit breaker")
                return cached_result
            raise AIServiceError(f"Service temporarily unavailable: {str(e)}")
        except Exception as e:
            AI_ERROR_COUNTER.labels(operation=operation, error_type='unknown').inc()
            self.logger.error(f"Unexpected error in AI request for {operation}: {str(e)}")
            raise AIServiceError(f"Unexpected error: {str(e)}")

    async def enhance_learning_material(
        self,
        material: LearningMaterial,
        enhancement_type: str,
        school_config: Dict[str, Any]
    ) -> str:
        """Enhance learning material content using AI."""
        try:
            prompt = self._build_enhancement_prompt(material, enhancement_type, school_config)
            return await self._make_ai_request(
                "enhance_material",
                messages=[{"role": "user", "content": prompt}],
                model="gpt-4",
                temperature=0.7,
                max_tokens=1000
            )
        except Exception as e:
            self.logger.error(
                "enhance_material_failed",
                material_id=material.id,
                error=str(e)
            )
            raise

    async def analyze_learning_patterns(
        self,
        course: Course,
        timeframe: str = "all"
    ) -> Dict[str, Any]:
        """Analyze learning patterns in a course."""
        try:
            enrollments = (
                self.db.query(StudentCourse)
                .filter(StudentCourse.course_id == course.id)
                .all()
            )
            
            if not enrollments:
                raise ValueError("No student data found for analysis")

            prompt = self._build_analysis_prompt(enrollments, timeframe)
            return await self._make_ai_request(
                "analyze_patterns",
                messages=[{"role": "user", "content": prompt}],
                model="gpt-4",
                temperature=0.5,
                max_tokens=1500
            )
        except Exception as e:
            self.logger.error(
                "analyze_patterns_failed",
                course_id=course.id,
                error=str(e)
            )
            raise

    def _build_enhancement_prompt(
        self,
        material: LearningMaterial,
        enhancement_type: str,
        school_config: Dict[str, Any]
    ) -> str:
        """Build prompt for content enhancement."""
        return f"""
        Enhance the following {material.material_type} content using {enhancement_type} approach.
        Consider these configurations: {json.dumps(school_config)}
        
        Content:
        {material.content}
        """

    def _build_analysis_prompt(
        self,
        enrollments: List[StudentCourse],
        timeframe: str
    ) -> str:
        """Build prompt for learning pattern analysis."""
        return f"""
        Analyze learning patterns for {len(enrollments)} students over {timeframe} timeframe.
        
        Progress Data:
        {json.dumps([e.progress for e in enrollments])}
        """

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
            recommendations = await self._make_ai_request(
                "recommendations",
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
                model="gpt-4",
                temperature=0.7,
                max_tokens=1000
            )

            return {
                "student_id": student.id,
                "course_id": course.id,
                "recommendations": recommendations,
                "context": context
            }
        except Exception as e:
            raise Exception(f"Error generating recommendations: {str(e)}")

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
            response = await self._make_ai_request(
                "generate_assessment",
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
                model="gpt-4",
                temperature=0.7,
                max_tokens=1000
            )

            assessment = response
            return {
                "material_id": material.id,
                "student_level": student_level,
                "assessment": assessment
            }
        except Exception as e:
            self.logger.error(
                "generate_assessment_failed",
                material_id=material.id,
                error=str(e)
            )
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
            response = await self._make_ai_request(
                "provide_insights",
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
                model="gpt-4",
                temperature=0.7,
                max_tokens=1000
            )

            insights = response
            return {
                "student_id": student.id,
                "insights": insights,
                "raw_data": learning_data,
                "timeframe": timeframe
            }
        except Exception as e:
            self.logger.error(
                "get_insights_failed",
                student_id=student.id,
                error=str(e)
            )
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
            response = await self._make_ai_request(
                "generate_curriculum_plan",
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
                model="gpt-4",
                temperature=0.7,
                max_tokens=1000
            )

            curriculum_plan = response
            return {
                "course_id": course.id,
                "curriculum_plan": curriculum_plan,
                "context": context
            }
        except Exception as e:
            self.logger.error(
                "generate_curriculum_plan_failed",
                course_id=course.id,
                error=str(e)
            )
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
            response = await self._make_ai_request(
                "analyze_engagement",
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
                model="gpt-4",
                temperature=0.7,
                max_tokens=1000
            )

            analysis = response
            return {
                "course_id": course.id,
                "engagement_analysis": analysis,
                "raw_data": engagement_data,
                "timeframe": timeframe
            }
        except Exception as e:
            self.logger.error(
                "analyze_engagement_failed",
                course_id=course.id,
                error=str(e)
            )
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
            response = await self._make_ai_request(
                "generate_feedback",
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
                model="gpt-4",
                temperature=0.7,
                max_tokens=1000
            )

            feedback = response
            return {
                "student_id": student.id,
                "material_id": material.id,
                "feedback": feedback,
                "feedback_type": feedback_type,
                "context": context
            }
        except Exception as e:
            self.logger.error(
                "generate_feedback_failed",
                student_id=student.id,
                material_id=material.id,
                error=str(e)
            )
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
            response = await self._make_ai_request(
                "predict_performance",
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
                model="gpt-4",
                temperature=0.7,
                max_tokens=1000
            )

            prediction = response
            return {
                "student_id": student.id,
                "course_id": course.id,
                "prediction": prediction,
                "confidence_level": "medium",  # You could calculate this based on data quality
                "prediction_horizon": prediction_horizon,
                "raw_data": historical_data
            }
        except Exception as e:
            self.logger.error(
                "predict_performance_failed",
                student_id=student.id,
                course_id=course.id,
                error=str(e)
            )
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
            response = await self._make_ai_request(
                "generate_concept_map",
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
                model="gpt-4",
                temperature=0.7,
                max_tokens=1000
            )

            concept_map = response
            return {
                "material_id": material.id,
                "concept_map": concept_map,
                "complexity_level": complexity_level
            }
        except Exception as e:
            self.logger.error(
                "generate_concept_map_failed",
                material_id=material.id,
                error=str(e)
            )
            raise Exception(f"Error generating concept map: {str(e)}")

    async def invalidate_cache(self, pattern: str) -> bool:
        """
        Invalidate cache for a specific pattern.
        """
        return await cache_service.clear_pattern(pattern) 