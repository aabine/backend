import warnings
warnings.filterwarnings("ignore", message="Valid config keys have changed in V2")

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from app.api.v1.api import api_router
from app.core.config import settings
from app.api.middleware import setup_middleware
from app.core.logging import setup_logging

# Set up logging
logger = setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="AI-Powered Educational Platform API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    swagger_ui_parameters={"defaultModelsExpandDepth": -1}
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for documentation
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)

# Set up custom middleware
setup_middleware(app)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Set up Prometheus instrumentation
instrumentator = Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    should_respect_env_var=True,
    should_instrument_requests_inprogress=True,
    excluded_handlers=["/metrics"],
    env_var_name="ENABLE_METRICS",
    inprogress_name="fastapi_inprogress",
    inprogress_labels=True,
)

@app.on_event("startup")
async def startup():
    logger.info("application_starting")
    instrumentator.instrument(app).expose(app, include_in_schema=False, tags=["monitoring"])
    logger.info("application_started", metrics_enabled=settings.ENABLE_METRICS)

@app.on_event("shutdown")
async def shutdown():
    logger.info("application_stopping")

# Health check endpoint
@app.get("/health")
async def health_check():
    logger.debug("health_check_requested")
    return {"status": "healthy"} 