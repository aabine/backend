import os
import shutil
from typing import List, Optional, BinaryIO
from datetime import datetime
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.models.content import Content, ContentVersion, ContentFolder
from app.schemas.content import ContentCreate, ContentUpdate, ContentSearch
from app.core.config import settings
import aiofiles
import magic
import asyncio
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ContentService:
    def __init__(self, db: Session):
        self.db = db
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def create_content(self, file: UploadFile, data: ContentCreate, user_id: int) -> Content:
        """Create new content with file upload."""
        try:
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_filename = f"{timestamp}_{file.filename}"
            file_path = self.upload_dir / unique_filename

            # Save file
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)

            # Get file metadata
            mime_type = magic.from_file(str(file_path), mime=True)
            file_size = os.path.getsize(file_path)

            # Create content record
            content = Content(
                title=data.title,
                description=data.description,
                content_type=data.content_type,
                content_url=str(file_path),
                content_metadata={
                    "file_size": file_size,
                    "mime_type": mime_type
                },
                tags=data.tags,
                is_public=data.is_public,
                course_id=data.course_id,
                folder_id=data.folder_id,
                created_by=user_id
            )
            self.db.add(content)
            
            # Create initial version
            version = ContentVersion(
                content=content,
                version=1,
                content_url=str(file_path),
                created_by=user_id
            )
            self.db.add(version)
            
            await self.db.commit()
            await self.db.refresh(content)
            return content

        except Exception as e:
            logger.error(f"Error creating content: {str(e)}")
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(status_code=500, detail="Error creating content")

    async def update_content(
        self, 
        content_id: int, 
        data: ContentUpdate, 
        file: Optional[UploadFile], 
        user_id: int
    ) -> Content:
        """Update content and optionally create new version."""
        content = self.db.query(Content).filter(Content.id == content_id).first()
        if not content:
            raise HTTPException(status_code=404, detail="Content not found")

        # Update content fields
        for field, value in data.dict(exclude_unset=True).items():
            setattr(content, field, value)

        if file:
            # Create new version
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_filename = f"{timestamp}_{file.filename}"
            file_path = self.upload_dir / unique_filename

            try:
                async with aiofiles.open(file_path, 'wb') as f:
                    content = await file.read()
                    await f.write(content)

                mime_type = magic.from_file(str(file_path), mime=True)
                file_size = os.path.getsize(file_path)

                # Update content metadata
                content.content_metadata = {
                    "file_size": file_size,
                    "mime_type": mime_type
                }
                content.content_url = str(file_path)
                content.current_version += 1

                # Create new version record
                version = ContentVersion(
                    content=content,
                    version=content.current_version,
                    content_url=str(file_path),
                    created_by=user_id
                )
                self.db.add(version)

            except Exception as e:
                logger.error(f"Error updating content: {str(e)}")
                if file_path.exists():
                    file_path.unlink()
                raise HTTPException(status_code=500, detail="Error updating content")

        await self.db.commit()
        await self.db.refresh(content)
        return content

    async def delete_content(self, content_id: int):
        """Delete content and all its versions."""
        content = self.db.query(Content).filter(Content.id == content_id).first()
        if not content:
            raise HTTPException(status_code=404, detail="Content not found")

        # Delete all version files
        for version in content.versions:
            try:
                os.remove(version.content_url)
            except Exception as e:
                logger.error(f"Error deleting version file: {str(e)}")

        # Delete database records
        self.db.delete(content)
        await self.db.commit()

    async def search_content(self, search: ContentSearch) -> List[Content]:
        """Search content with filters."""
        query = self.db.query(Content)

        if search.query:
            query = query.filter(
                or_(
                    Content.title.ilike(f"%{search.query}%"),
                    Content.description.ilike(f"%{search.query}%")
                )
            )

        if search.content_types:
            query = query.filter(Content.content_type.in_(search.content_types))

        if search.tags:
            for tag in search.tags:
                query = query.filter(Content.tags.contains([tag]))

        if search.course_id:
            query = query.filter(Content.course_id == search.course_id)

        if search.folder_id:
            query = query.filter(Content.folder_id == search.folder_id)

        if search.created_by:
            query = query.filter(Content.created_by == search.created_by)

        if search.date_from:
            query = query.filter(Content.created_at >= search.date_from)

        if search.date_to:
            query = query.filter(Content.created_at <= search.date_to)

        # Apply sorting
        if search.sort_by:
            sort_column = getattr(Content, search.sort_by)
            if search.sort_order == "desc":
                sort_column = sort_column.desc()
            query = query.order_by(sort_column)

        # Apply pagination
        offset = (search.page - 1) * search.page_size
        query = query.offset(offset).limit(search.page_size)

        return query.all()

    async def get_content_version(self, content_id: int, version: int) -> Optional[ContentVersion]:
        """Get specific version of content."""
        return self.db.query(ContentVersion).filter(
            and_(
                ContentVersion.content_id == content_id,
                ContentVersion.version == version
            )
        ).first()

    async def create_folder(self, folder_data: dict, user_id: int) -> ContentFolder:
        """Create new content folder."""
        folder = ContentFolder(
            name=folder_data["name"],
            description=folder_data.get("description"),
            parent_id=folder_data.get("parent_id"),
            course_id=folder_data.get("course_id"),
            created_by=user_id
        )
        self.db.add(folder)
        await self.db.commit()
        await self.db.refresh(folder)
        return folder

    async def get_folder_contents(self, folder_id: int) -> dict:
        """Get all contents and subfolders in a folder."""
        folder = self.db.query(ContentFolder).filter(ContentFolder.id == folder_id).first()
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")

        return {
            "folder": folder,
            "subfolders": folder.subfolders,
            "contents": folder.content
        } 