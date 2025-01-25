from fastapi import APIRouter
from app.api.v1.endpoints import auth, schools, courses, ai_modules, analytics, content, interactive, assessment, admin, grading

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(schools.router, prefix="/schools", tags=["Schools"])
api_router.include_router(courses.router, prefix="/courses", tags=["Courses"])
api_router.include_router(ai_modules.router, prefix="/ai-modules", tags=["AI Modules"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(content.router, prefix="/content", tags=["Content Management"])
api_router.include_router(interactive.router, prefix="/interactive", tags=["Interactive"])
api_router.include_router(assessment.router, prefix="/assessments", tags=["Assessments"])
api_router.include_router(admin.router, prefix="/admin", tags=["Administration"])
api_router.include_router(grading.router, prefix="/grading", tags=["Grading"]) 