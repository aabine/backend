from typing import List
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "EduAI Platform"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = "your-secret-key-here"  # Change in production
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "eduai_db"
    SQLALCHEMY_DATABASE_URI: str = None

    # CORS
    ALLOWED_ORIGINS: List[AnyHttpUrl] = []

    @validator("SQLALCHEMY_DATABASE_URI", pre=True)
    def assemble_db_connection(cls, v: str | None, values: dict) -> str:
        if v:
            return v
        return f"postgresql://{values['POSTGRES_USER']}:{values['POSTGRES_PASSWORD']}@{values['POSTGRES_SERVER']}/{values['POSTGRES_DB']}"

    # AI Configuration
    OPENAI_API_KEY: str = ""
    
    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings() 