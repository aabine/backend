from sqlalchemy import Boolean, Column, String, Integer, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.db.base_class import Base

class AuthProvider(str, enum.Enum):
    LOCAL = "local"
    GOOGLE = "google"
    MICROSOFT = "microsoft"

class UserRole(str, enum.Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)  # Nullable for social auth
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    role = Column(SQLEnum(UserRole), default=UserRole.STUDENT)
    
    # Profile fields
    avatar_url = Column(String, nullable=True)
    bio = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    
    # Authentication fields
    auth_provider = Column(SQLEnum(AuthProvider), default=AuthProvider.LOCAL)
    social_id = Column(String, nullable=True)  # ID from social provider
    last_login = Column(DateTime, nullable=True)
    password_reset_token = Column(String, nullable=True)
    password_reset_expires = Column(DateTime, nullable=True)
    
    # 2FA fields
    is_2fa_enabled = Column(Boolean, default=False)
    twofa_secret = Column(String, nullable=True)
    backup_codes = Column(String, nullable=True)  # Stored as JSON string
    
    # Verification
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)
    verification_expires = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    courses = relationship("Course", back_populates="teacher", foreign_keys="Course.teacher_id")
    enrollments = relationship("StudentCourse", back_populates="student")
    
    def __repr__(self):
        return f"<User {self.email}>" 