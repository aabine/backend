from fastapi import APIRouter
from app.api.v1.endpoints import auth, schools, courses, ai_modules, analytics

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(schools.router, prefix="/schools", tags=["Schools"])
api_router.include_router(courses.router, prefix="/courses", tags=["Courses"])
api_router.include_router(ai_modules.router, prefix="/ai-modules", tags=["AI Modules"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"]) 