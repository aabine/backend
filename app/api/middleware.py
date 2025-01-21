from fastapi import Request, HTTPException
from app.core.security import check_rate_limit
from app.models.models import School
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from typing import Optional
import re

async def get_api_key(request: Request) -> Optional[str]:
    """Extract API key from request headers or query parameters."""
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        api_key = request.query_params.get("api_key")
    return api_key

async def verify_api_key(api_key: str, db: Session) -> Optional[School]:
    """Verify API key and return associated school."""
    if not api_key:
        return None
    
    school = db.query(School).filter(School.api_key == api_key).first()
    return school

async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware."""
    # Skip rate limiting for certain paths
    if any(path in request.url.path for path in ["/api/v1/docs", "/api/v1/openapi.json", "/api/v1/redoc"]):
        return await call_next(request)

    # Get client identifier (IP or API key)
    client_id = request.headers.get("X-API-Key", request.client.host)
    
    # Check rate limit
    if not await check_rate_limit(f"rate_limit:{client_id}"):
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later."
        )
    
    return await call_next(request)

async def api_key_middleware(request: Request, call_next):
    """API key validation middleware."""
    # List of paths that don't require API key
    public_paths = [
        "/api/v1/docs",
        "/api/v1/redoc",
        "/api/v1/openapi.json",
        "/api/v1/auth"
    ]
    
    # Skip API key validation for public paths
    if any(request.url.path.startswith(path) for path in public_paths):
        return await call_next(request)

    # Skip if not an API route
    if not request.url.path.startswith("/api/v1/"):
        return await call_next(request)

    api_key = await get_api_key(request)
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key is required"
        )

    # Verify API key
    db = SessionLocal()
    try:
        school = await verify_api_key(api_key, db)
        if not school:
            raise HTTPException(
                status_code=401,
                detail="Invalid API key"
            )
        
        # Add school to request state
        request.state.school = school
        return await call_next(request)
    finally:
        db.close()

async def security_headers_middleware(request: Request, call_next):
    """Add security headers to responses."""
    response = await call_next(request)
    
    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    # Skip CSP for documentation routes
    if not any(path in request.url.path for path in ["/api/v1/docs", "/api/v1/redoc", "/api/v1/openapi.json"]):
        response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data:; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';"
    
    return response

def setup_middleware(app):
    """Set up all middleware."""
    app.middleware("http")(security_headers_middleware)
    app.middleware("http")(api_key_middleware)
    app.middleware("http")(rate_limit_middleware) 