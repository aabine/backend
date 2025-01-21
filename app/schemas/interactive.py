from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class NotificationType(str, Enum):
    MESSAGE = "message"
    FORUM = "forum"
    CLASSROOM = "classroom"
    SYSTEM = "system"

class NotificationBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str
    notification_type: NotificationType
    reference_id: Optional[int] = None

class NotificationCreate(NotificationBase):
    user_id: int

class Notification(NotificationBase):
    id: int
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True

class ForumBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    course_id: int

class ForumCreate(ForumBase):
    pass

class Forum(ForumBase):
    id: int
    created_by: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    post_count: Optional[int] = None

    class Config:
        from_attributes = True

class PostBase(BaseModel):
    content: str = Field(..., min_length=1)
    forum_id: int
    parent_id: Optional[int] = None

class PostCreate(PostBase):
    pass

class Post(PostBase):
    id: int
    created_by: int
    is_pinned: bool
    created_at: datetime
    updated_at: datetime
    reply_count: Optional[int] = None

    class Config:
        from_attributes = True

class MessageBase(BaseModel):
    content: str = Field(..., min_length=1)
    receiver_id: int

class MessageCreate(MessageBase):
    pass

class Message(MessageBase):
    id: int
    sender_id: int
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True

class VirtualClassroomBase(BaseModel):
    course_id: int
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    meeting_url: Optional[str] = None
    scheduled_start: datetime
    scheduled_end: datetime

class VirtualClassroomCreate(VirtualClassroomBase):
    pass

class VirtualClassroom(VirtualClassroomBase):
    id: int
    is_active: bool
    created_by: int
    created_at: datetime
    updated_at: datetime
    participant_count: Optional[int] = None

    class Config:
        from_attributes = True

class ClassroomParticipantBase(BaseModel):
    classroom_id: int
    user_id: int

class ClassroomParticipant(ClassroomParticipantBase):
    id: int
    joined_at: datetime
    left_at: Optional[datetime] = None
    is_present: bool

    class Config:
        from_attributes = True

class ClassroomChatBase(BaseModel):
    classroom_id: int
    content: str = Field(..., min_length=1)

class ClassroomChatCreate(ClassroomChatBase):
    pass

class ClassroomChat(ClassroomChatBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True 