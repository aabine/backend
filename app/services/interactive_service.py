from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from fastapi import HTTPException
from app.models.models import (
    User, Course, Notification, DiscussionForum, ForumPost,
    Message, VirtualClassroom, ClassroomParticipant, ClassroomChat
)
from app.schemas.interactive import (
    NotificationCreate, ForumCreate, PostCreate,
    MessageCreate, VirtualClassroomCreate, ClassroomChatCreate
)
import logging

logger = logging.getLogger(__name__)

class InteractiveService:
    def __init__(self, db: Session):
        self.db = db

    async def create_notification(self, data: NotificationCreate) -> Notification:
        """Create a new notification."""
        notification = Notification(**data.dict())
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        return notification

    async def get_user_notifications(self, user_id: int, skip: int = 0, limit: int = 100) -> List[Notification]:
        """Get notifications for a user."""
        return self.db.query(Notification)\
            .filter(Notification.user_id == user_id)\
            .order_by(Notification.created_at.desc())\
            .offset(skip).limit(limit).all()

    async def mark_notification_read(self, notification_id: int, user_id: int) -> Notification:
        """Mark a notification as read."""
        notification = self.db.query(Notification)\
            .filter(and_(Notification.id == notification_id, Notification.user_id == user_id))\
            .first()
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        notification.is_read = True
        await self.db.commit()
        return notification

    async def create_forum(self, data: ForumCreate, user_id: int) -> DiscussionForum:
        """Create a new discussion forum."""
        forum = DiscussionForum(**data.dict(), created_by=user_id)
        self.db.add(forum)
        await self.db.commit()
        await self.db.refresh(forum)
        return forum

    async def create_forum_post(self, data: PostCreate, user_id: int) -> ForumPost:
        """Create a new forum post."""
        post = ForumPost(**data.dict(), created_by=user_id)
        self.db.add(post)
        await self.db.commit()
        await self.db.refresh(post)

        # Create notifications for forum subscribers
        forum = self.db.query(DiscussionForum).filter(DiscussionForum.id == data.forum_id).first()
        if forum:
            # TODO: Implement forum subscription logic
            pass

        return post

    async def send_message(self, data: MessageCreate, sender_id: int) -> Message:
        """Send a message to another user."""
        message = Message(**data.dict(), sender_id=sender_id)
        self.db.add(message)
        
        # Create notification for receiver
        notification = Notification(
            user_id=data.receiver_id,
            title="New Message",
            content=f"You have a new message from {sender_id}",
            notification_type="message",
            reference_id=message.id
        )
        self.db.add(notification)
        
        await self.db.commit()
        await self.db.refresh(message)
        return message

    async def get_user_messages(
        self,
        user_id: int,
        other_user_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Message]:
        """Get messages for a user."""
        query = self.db.query(Message)\
            .filter(
                or_(
                    Message.sender_id == user_id,
                    Message.receiver_id == user_id
                )
            )
        
        if other_user_id:
            query = query.filter(
                or_(
                    and_(Message.sender_id == user_id, Message.receiver_id == other_user_id),
                    and_(Message.sender_id == other_user_id, Message.receiver_id == user_id)
                )
            )
        
        return query.order_by(Message.created_at.desc()).offset(skip).limit(limit).all()

    async def create_virtual_classroom(self, data: VirtualClassroomCreate, user_id: int) -> VirtualClassroom:
        """Create a new virtual classroom."""
        classroom = VirtualClassroom(**data.dict(), created_by=user_id)
        self.db.add(classroom)
        await self.db.commit()
        await self.db.refresh(classroom)
        return classroom

    async def join_classroom(self, classroom_id: int, user_id: int) -> ClassroomParticipant:
        """Join a virtual classroom."""
        classroom = self.db.query(VirtualClassroom).filter(VirtualClassroom.id == classroom_id).first()
        if not classroom:
            raise HTTPException(status_code=404, detail="Classroom not found")
        
        participant = ClassroomParticipant(
            classroom_id=classroom_id,
            user_id=user_id,
            is_present=True
        )
        self.db.add(participant)
        await self.db.commit()
        await self.db.refresh(participant)
        return participant

    async def leave_classroom(self, classroom_id: int, user_id: int) -> ClassroomParticipant:
        """Leave a virtual classroom."""
        participant = self.db.query(ClassroomParticipant)\
            .filter(
                and_(
                    ClassroomParticipant.classroom_id == classroom_id,
                    ClassroomParticipant.user_id == user_id,
                    ClassroomParticipant.is_present == True
                )
            ).first()
        
        if not participant:
            raise HTTPException(status_code=404, detail="Participant not found")
        
        participant.is_present = False
        participant.left_at = datetime.utcnow()
        await self.db.commit()
        return participant

    async def send_classroom_message(self, data: ClassroomChatCreate, user_id: int) -> ClassroomChat:
        """Send a message in virtual classroom chat."""
        message = ClassroomChat(**data.dict(), user_id=user_id)
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message

    async def get_classroom_messages(
        self,
        classroom_id: int,
        skip: int = 0,
        limit: int = 50
    ) -> List[ClassroomChat]:
        """Get messages from a virtual classroom chat."""
        return self.db.query(ClassroomChat)\
            .filter(ClassroomChat.classroom_id == classroom_id)\
            .order_by(ClassroomChat.created_at.desc())\
            .offset(skip).limit(limit).all() 