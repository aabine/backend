from pydantic import BaseModel
from typing import Optional, Dict, Any

class SchoolBase(BaseModel):
    name: str
    description: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None

class SchoolCreate(SchoolBase):
    pass

class SchoolUpdate(SchoolBase):
    pass

class School(SchoolBase):
    id: int
    api_key: str

    class Config:
        from_attributes = True

class SchoolAPIKey(BaseModel):
    api_key: str 