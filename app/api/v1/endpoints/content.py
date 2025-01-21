from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.api import deps
from app.services.content_service import ContentService
from app.schemas.content import (
    Content, ContentCreate, ContentUpdate, ContentSearch,
    ContentFolder, ContentFolderCreate, ContentVersion
)
from app.models.models import User, UserRole
from fastapi.responses import FileResponse
import json

router = APIRouter()

@router.post("/upload", response_model=Content)
async def upload_content(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    content_type: str = Form(...),
    tags: str = Form("[]"),  # JSON string of tags
    is_public: bool = Form(False),
    course_id: Optional[int] = Form(None),
    folder_id: Optional[int] = Form(None),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Upload new content.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.TEACHER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    content_service = ContentService(db)
    content_data = ContentCreate(
        title=title,
        description=description,
        content_type=content_type,
        tags=json.loads(tags),
        is_public=is_public,
        course_id=course_id,
        folder_id=folder_id
    )
    
    return await content_service.create_content(file, content_data, current_user.id)

@router.put("/{content_id}", response_model=Content)
async def update_content(
    content_id: int,
    file: Optional[UploadFile] = File(None),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    content_type: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # JSON string of tags
    is_public: Optional[bool] = Form(None),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Update content and optionally upload new version.
    """
    content_service = ContentService(db)
    content = await content_service.get_content(content_id)
    
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    if content.created_by != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    update_data = ContentUpdate(
        title=title,
        description=description,
        content_type=content_type,
        tags=json.loads(tags) if tags else None,
        is_public=is_public
    )
    
    return await content_service.update_content(content_id, update_data, file, current_user.id)

@router.delete("/{content_id}")
async def delete_content(
    content_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Delete content and all its versions.
    """
    content_service = ContentService(db)
    content = await content_service.get_content(content_id)
    
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    if content.created_by != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    await content_service.delete_content(content_id)
    return {"message": "Content deleted successfully"}

@router.get("/search", response_model=List[Content])
async def search_content(
    search_params: ContentSearch = Depends(),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Search content with filters.
    """
    content_service = ContentService(db)
    return await content_service.search_content(search_params)

@router.get("/{content_id}/versions/{version}", response_model=ContentVersion)
async def get_content_version(
    content_id: int,
    version: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Get specific version of content.
    """
    content_service = ContentService(db)
    content_version = await content_service.get_content_version(content_id, version)
    
    if not content_version:
        raise HTTPException(status_code=404, detail="Content version not found")
    
    return content_version

@router.get("/{content_id}/download")
async def download_content(
    content_id: int,
    version: Optional[int] = None,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Download content file.
    """
    content_service = ContentService(db)
    content = await content_service.get_content(content_id)
    
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    if not content.is_public and content.created_by != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    if version:
        content_version = await content_service.get_content_version(content_id, version)
        if not content_version:
            raise HTTPException(status_code=404, detail="Content version not found")
        file_path = content_version.content_url
    else:
        file_path = content.content_url
    
    return FileResponse(file_path, filename=content.title)

@router.post("/folders", response_model=ContentFolder)
async def create_folder(
    folder: ContentFolderCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Create new content folder.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.TEACHER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    content_service = ContentService(db)
    return await content_service.create_folder(folder.dict(), current_user.id)

@router.get("/folders/{folder_id}")
async def get_folder_contents(
    folder_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Get all contents and subfolders in a folder.
    """
    content_service = ContentService(db)
    return await content_service.get_folder_contents(folder_id) 