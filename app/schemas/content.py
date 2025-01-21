from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class ContentType(str, Enum):
    DOCUMENT = "document"
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    PRESENTATION = "presentation"
    OTHER = "other"

class ContentVersion(BaseModel):
    version: int
    content_url: str
    created_at: datetime
    created_by: int
    changes: Optional[str] = None

class ContentMetadata(BaseModel):
    file_size: int
    mime_type: str
    duration: Optional[float] = None  # For audio/video
    dimensions: Optional[Dict[str, int]] = None  # For images/videos
    encoding: Optional[str] = None
    additional_info: Optional[Dict[str, Any]] = None

class ContentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    content_type: ContentType
    tags: List[str] = Field(default_factory=list)
    content_metadata: Optional[ContentMetadata] = None
    is_public: bool = False

    @validator('tags')
    def validate_tags(cls, v):
        return [tag.lower().strip() for tag in v if tag.strip()]

class ContentCreate(ContentBase):
    course_id: Optional[int] = None
    folder_id: Optional[int] = None

class ContentUpdate(ContentBase):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content_type: Optional[ContentType] = None

class Content(ContentBase):
    id: int
    current_version: int
    content_url: str
    versions: List[ContentVersion]
    created_at: datetime
    updated_at: datetime
    created_by: int
    course_id: Optional[int] = None
    folder_id: Optional[int] = None
    download_count: int = 0
    view_count: int = 0

    class Config:
        from_attributes = True

class ContentSearch(BaseModel):
    query: Optional[str] = None
    content_types: Optional[List[ContentType]] = None
    tags: Optional[List[str]] = None
    course_id: Optional[int] = None
    folder_id: Optional[int] = None
    created_by: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    sort_by: Optional[str] = "updated_at"
    sort_order: Optional[str] = "desc"
    page: int = 1
    page_size: int = 20

class ContentFolder(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    parent_id: Optional[int] = None
    course_id: Optional[int] = None
    created_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ContentFolderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    parent_id: Optional[int] = None
    course_id: Optional[int] = None 