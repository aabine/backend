import sys
import structlog
from app.core.config import settings

def setup_logging():
    """Configure structured logging for the application."""
    log_level = settings.LOG_LEVEL.upper()  # Convert to uppercase
    
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Set up root logger
    root_logger = structlog.get_logger()
    root_logger.info("logging_configured", log_level=log_level)

    return root_logger 