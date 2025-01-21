from typing import List, Optional, Dict
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, validator
from datetime import timedelta

class Settings(BaseSettings):
    PROJECT_NAME: str = "Learning Platform API"
    API_V1_STR: str = "/api/v1"
    
    # Content Management
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS: List[str] = [
        # Documents
        "pdf", "doc", "docx", "txt", "rtf", "odt",
        # Images
        "jpg", "jpeg", "png", "gif", "svg",
        # Audio
        "mp3", "wav", "ogg", "m4a",
        # Video
        "mp4", "avi", "mov", "wmv",
        # Presentations
        "ppt", "pptx", "odp",
        # Archives
        "zip", "rar", "7z"
    ]
    MEDIA_TYPES: Dict[str, List[str]] = {
        "document": ["pdf", "doc", "docx", "txt", "rtf", "odt"],
        "image": ["jpg", "jpeg", "png", "gif", "svg"],
        "audio": ["mp3", "wav", "ogg", "m4a"],
        "video": ["mp4", "avi", "mov", "wmv"],
        "presentation": ["ppt", "pptx", "odp"],
        "archive": ["zip", "rar", "7z"]
    }
    
    # Security
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days
    ALGORITHM: str = "HS256"
    
    # Security Policies
    MINIMUM_PASSWORD_LENGTH: int = 8
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 60
    VERIFICATION_TOKEN_EXPIRE_MINUTES: int = 60
    MAX_LOGIN_ATTEMPTS: int = 5
    LOGIN_ATTEMPT_TIMEOUT: int = 300  # 5 minutes
    
    # API Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60  # 1 minute
    
    # Data Encryption
    ENCRYPTION_KEY: str = None  # Set in production
    ENCRYPTION_ALGORITHM: str = "AES-256-CBC"
    
    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    SQLALCHEMY_DATABASE_URI: Optional[str] = None
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_URL: Optional[str] = None

    # AI Service Configuration
    AI_API_BASE_URL: str
    AI_API_KEY: str
    AI_REQUEST_TIMEOUT: int = 30
    AI_MAX_RETRIES: int = 3
    AI_CIRCUIT_BREAKER_THRESHOLD: int = 5
    AI_CIRCUIT_BREAKER_TIMEOUT: int = 60
    
    # Monitoring Configuration
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 8000
    METRICS_HOST: str = "0.0.0.0"
    LOG_LEVEL: str = "info"

    # Email Configuration
    SMTP_TLS: bool = True
    SMTP_PORT: int = 587
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAILS_FROM_EMAIL: str = ""
    EMAILS_FROM_NAME: str = PROJECT_NAME
    
    # Social Authentication
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    MICROSOFT_CLIENT_ID: str = ""
    MICROSOFT_CLIENT_SECRET: str = ""
    
    # Server
    SERVER_HOST: str = "http://localhost:8000"  # Frontend URL for email links

    @validator("REDIS_URL", pre=True)
    def assemble_redis_url(cls, v: str | None, values: dict) -> str:
        if v:
            return v
        password = f":{values.get('REDIS_PASSWORD')}@" if values.get('REDIS_PASSWORD') else ""
        return f"redis://{password}{values['REDIS_HOST']}:{values['REDIS_PORT']}/{values['REDIS_DB']}"

    # CORS Configuration
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",  # React default port
        "http://localhost:5173",  # Vite default port
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    ALLOWED_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
    ALLOWED_HEADERS: List[str] = [
        "Content-Type",
        "Authorization",
        "X-API-Key",
        "Accept",
        "Origin",
        "X-Requested-With",
    ]
    ALLOW_CREDENTIALS: bool = True
    EXPOSE_HEADERS: List[str] = ["Content-Length"]
    MAX_AGE: int = 600  # Maximum time to cache CORS responses

    @validator("SQLALCHEMY_DATABASE_URI", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: dict) -> str:
        if v:
            return v
        return f"postgresql://{values['POSTGRES_USER']}:{values['POSTGRES_PASSWORD']}@{values['POSTGRES_SERVER']}/{values['POSTGRES_DB']}"

    # AI Configuration
    OPENAI_API_KEY: str = ""
    
    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings() 