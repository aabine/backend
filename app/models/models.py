from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, JSON, Enum
from sqlalchemy.orm import relationship
import enum
from .base import Base

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"
    PARENT = "parent"

class User(Base):
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    role = Column(Enum(UserRole), nullable=False)
    is_active = Column(Boolean, default=True)
    school_id = Column(Integer, ForeignKey("school.id"))
    
    school = relationship("School", back_populates="users")
    courses = relationship("Course", back_populates="teacher")
    student_courses = relationship("StudentCourse", back_populates="student")

class School(Base):
    name = Column(String, nullable=False)
    description = Column(Text)
    configuration = Column(JSON)
    api_key = Column(String, unique=True)
    
    users = relationship("User", back_populates="school")
    courses = relationship("Course", back_populates="school")
    ai_modules = relationship("AIModule", back_populates="school")

class Course(Base):
    name = Column(String, nullable=False)
    description = Column(Text)
    teacher_id = Column(Integer, ForeignKey("user.id"))
    school_id = Column(Integer, ForeignKey("school.id"))
    
    teacher = relationship("User", back_populates="courses")
    school = relationship("School", back_populates="courses")
    students = relationship("StudentCourse", back_populates="course")
    learning_materials = relationship("LearningMaterial", back_populates="course")

class StudentCourse(Base):
    student_id = Column(Integer, ForeignKey("user.id"))
    course_id = Column(Integer, ForeignKey("course.id"))
    progress = Column(JSON)
    
    student = relationship("User", back_populates="student_courses")
    course = relationship("Course", back_populates="students")

class LearningMaterial(Base):
    title = Column(String, nullable=False)
    content = Column(Text)
    material_type = Column(String)
    course_id = Column(Integer, ForeignKey("course.id"))
    ai_enhanced = Column(Boolean, default=False)
    
    course = relationship("Course", back_populates="learning_materials")

class AIModule(Base):
    name = Column(String, nullable=False)
    description = Column(Text)
    module_type = Column(String)
    configuration = Column(JSON)
    school_id = Column(Integer, ForeignKey("school.id"))
    is_active = Column(Boolean, default=True)
    
    school = relationship("School", back_populates="ai_modules") 