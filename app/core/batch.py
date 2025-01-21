from typing import List, Dict, Any
from celery import Celery
from app.core.config import settings
from app.services.ai_service import AIService
from sqlalchemy.orm import Session
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

celery_app = Celery(
    "ai_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

class BatchProcessor:
    def __init__(self, db: Session):
        self.db = db
        self.max_concurrent = 5  # Maximum concurrent API calls
        self.executor = ThreadPoolExecutor(max_workers=self.max_concurrent)
        self.logger = logging.getLogger(__name__)

    async def process_batch(
        self,
        operation: str,
        items: List[Dict[str, Any]],
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Process a batch of items using the specified AI operation.
        """
        ai_service = AIService(self.db)
        
        if not items:
            return []

        tasks = []
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def process_item(item: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                try:
                    if not isinstance(item, dict) or "id" not in item:
                        raise ValueError("Invalid item format")
                        
                    result = await getattr(ai_service, operation)(**item, **kwargs)
                    return {
                        "item_id": item["id"],
                        "status": "success",
                        "result": result
                    }
                except AttributeError:
                    self.logger.error(f"Operation {operation} not found")
                    return {
                        "item_id": item.get("id"),
                        "status": "error",
                        "error": f"Operation {operation} not found"
                    }
                except Exception as e:
                    self.logger.error(f"Error processing item {item.get('id')}: {str(e)}")
                    return {
                        "item_id": item.get("id"),
                        "status": "error",
                        "error": str(e)
                    }

        try:
            for item in items:
                tasks.append(asyncio.create_task(process_item(item)))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle any unhandled exceptions from gather
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"Unhandled error in batch processing: {str(result)}")
                    processed_results.append({
                        "item_id": items[i].get("id"),
                        "status": "error",
                        "error": f"Unhandled error: {str(result)}"
                    })
                else:
                    processed_results.append(result)
                    
            return processed_results
            
        except Exception as e:
            self.logger.error(f"Critical error in batch processing: {str(e)}")
            return [{
                "item_id": None,
                "status": "error",
                "error": f"Batch processing failed: {str(e)}"
            }]

@celery_app.task
def process_batch_task(operation: str, items: List[Dict[str, Any]], **kwargs) -> str:
    """
    Celery task for processing batches asynchronously.
    """
    from app.db.session import SessionLocal
    
    db = SessionLocal()
    try:
        processor = BatchProcessor(db)
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(
            processor.process_batch(operation, items, **kwargs)
        )
        return {
            "status": "completed",
            "results": results
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
    finally:
        db.close()

class BatchService:
    def __init__(self, db: Session):
        self.db = db
        self.processor = BatchProcessor(db)

    async def enhance_materials_batch(
        self,
        materials: List[Dict[str, Any]],
        school_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enhance multiple learning materials in batch.
        """
        task = process_batch_task.delay(
            "enhance_content",
            materials,
            school_config=school_config
        )
        return {"task_id": task.id}

    async def analyze_progress_batch(
        self,
        courses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze progress for multiple courses in batch.
        """
        task = process_batch_task.delay(
            "analyze_progress",
            courses
        )
        return {"task_id": task.id}

    async def generate_feedback_batch(
        self,
        submissions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate feedback for multiple submissions in batch.
        """
        task = process_batch_task.delay(
            "generate_feedback",
            submissions
        )
        return {"task_id": task.id}

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get the status of a batch processing task.
        """
        task = celery_app.AsyncResult(task_id)
        if task.ready():
            if task.successful():
                return {
                    "status": "completed",
                    "results": task.result
                }
            else:
                return {
                    "status": "failed",
                    "error": str(task.result)
                }
        return {
            "status": "processing",
            "task_id": task_id
        } 