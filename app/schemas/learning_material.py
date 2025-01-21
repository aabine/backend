from pydantic import BaseModel
from typing import Optional

class LearningMaterialBase(BaseModel):
    title: str
    content: str
    material_type: str
    ai_enhanced: bool = False

class LearningMaterialCreate(LearningMaterialBase):
    pass

class LearningMaterialUpdate(LearningMaterialBase):
    pass

class LearningMaterial(LearningMaterialBase):
    id: int
    course_id: int

    class Config:
        from_attributes = True 