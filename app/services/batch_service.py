from typing import List, Dict, Any
from celery import Celery
from app.core.config import settings
from app.services.ai_service import AIService
from sqlalchemy.orm import Session
import asyncio
from concurrent.futures import ThreadPoolExecutor

celery_app = Celery(
    "ai_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

class BatchService:
    def __init__(self, db: Session):
        self.db = db
        self.max_concurrent = 5
        self.executor = ThreadPoolExecutor(max_workers=self.max_concurrent)

    async def process_batch(self, operation: str, items: List[Dict[str, Any]], **kwargs) -> List[Dict[str, Any]]:
        ai_service = AIService(self.db)
        tasks = []
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def process_item(item: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                try:
                    result = await getattr(ai_service, operation)(**item, **kwargs)
                    return {"item_id": item.get("id"), "status": "success", "result": result}
                except Exception as e:
                    return {"item_id": item.get("id"), "status": "error", "error": str(e)}
        
        for item in items:
            tasks.append(asyncio.create_task(process_item(item)))
        
        return await asyncio.gather(*tasks) 