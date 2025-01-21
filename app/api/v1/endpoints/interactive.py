from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.api import deps
from app.services.interactive_service import InteractiveService
from app.schemas.interactive import (
    Notification, NotificationCreate,
    Forum, ForumCreate, Post, PostCreate,
    Message, MessageCreate,
    VirtualClassroom, VirtualClassroomCreate,
    ClassroomParticipant, ClassroomChat, ClassroomChatCreate
)
from app.models.models import User, UserRole
from app.core.websocket import ConnectionManager

router = APIRouter()
manager = ConnectionManager()

# Notifications endpoints
@router.get("/notifications", response_model=List[Notification])
async def get_notifications(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """Get user's notifications."""
    service = InteractiveService(db)
    return await service.get_user_notifications(current_user.id, skip, limit)

@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """Mark a notification as read."""
    service = InteractiveService(db)
    return await service.mark_notification_read(notification_id, current_user.id)

# Discussion forum endpoints
@router.post("/forums", response_model=Forum)
async def create_forum(
    forum: ForumCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """Create a new discussion forum."""
    if current_user.role not in [UserRole.ADMIN, UserRole.TEACHER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    service = InteractiveService(db)
    return await service.create_forum(forum, current_user.id)

@router.post("/forums/posts", response_model=Post)
async def create_post(
    post: PostCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """Create a new forum post."""
    service = InteractiveService(db)
    return await service.create_forum_post(post, current_user.id)

# Messaging endpoints
@router.post("/messages", response_model=Message)
async def send_message(
    message: MessageCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """Send a message to another user."""
    service = InteractiveService(db)
    return await service.send_message(message, current_user.id)

@router.get("/messages", response_model=List[Message])
async def get_messages(
    other_user_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """Get user's messages."""
    service = InteractiveService(db)
    return await service.get_user_messages(current_user.id, other_user_id, skip, limit)

@router.websocket("/ws/chat/{user_id}")
async def websocket_chat(
    websocket: WebSocket,
    user_id: int,
    db: Session = Depends(deps.get_db)
):
    """WebSocket endpoint for real-time chat."""
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_json()
            service = InteractiveService(db)
            message = await service.send_message(
                MessageCreate(
                    content=data["content"],
                    receiver_id=data["receiver_id"]
                ),
                user_id
            )
            # Send message to both sender and receiver
            await manager.send_personal_message(message.dict(), message.receiver_id)
            await manager.send_personal_message(message.dict(), user_id)
    except WebSocketDisconnect:
        manager.disconnect(user_id)

# Virtual classroom endpoints
@router.post("/classrooms", response_model=VirtualClassroom)
async def create_classroom(
    classroom: VirtualClassroomCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """Create a new virtual classroom."""
    if current_user.role not in [UserRole.ADMIN, UserRole.TEACHER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    service = InteractiveService(db)
    return await service.create_virtual_classroom(classroom, current_user.id)

@router.post("/classrooms/{classroom_id}/join", response_model=ClassroomParticipant)
async def join_classroom(
    classroom_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """Join a virtual classroom."""
    service = InteractiveService(db)
    return await service.join_classroom(classroom_id, current_user.id)

@router.post("/classrooms/{classroom_id}/leave", response_model=ClassroomParticipant)
async def leave_classroom(
    classroom_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """Leave a virtual classroom."""
    service = InteractiveService(db)
    return await service.leave_classroom(classroom_id, current_user.id)

@router.websocket("/ws/classroom/{classroom_id}/{user_id}")
async def websocket_classroom(
    websocket: WebSocket,
    classroom_id: int,
    user_id: int,
    db: Session = Depends(deps.get_db)
):
    """WebSocket endpoint for virtual classroom chat."""
    await manager.connect(websocket, f"classroom_{classroom_id}_{user_id}")
    try:
        while True:
            data = await websocket.receive_json()
            service = InteractiveService(db)
            message = await service.send_classroom_message(
                ClassroomChatCreate(
                    classroom_id=classroom_id,
                    content=data["content"]
                ),
                user_id
            )
            # Broadcast message to all participants in the classroom
            await manager.broadcast_to_room(f"classroom_{classroom_id}", message.dict())
    except WebSocketDisconnect:
        manager.disconnect(f"classroom_{classroom_id}_{user_id}") 