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

class BatchProcessor:
    def __init__(self, db: Session):
        self.db = db
        self.max_concurrent = 5  # Maximum concurrent API calls
        self.executor = ThreadPoolExecutor(max_workers=self.max_concurrent)

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
        
        # Create tasks for each item
        tasks = []
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def process_item(item: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                try:
                    if operation == "enhance_content":
                        result = await ai_service.enhance_learning_material(
                            material=item["material"],
                            enhancement_type=item.get("enhancement_type", "elaborate"),
                            school_config=kwargs.get("school_config", {})
                        )
                    elif operation == "analyze_progress":
                        result = await ai_service.analyze_learning_patterns(
                            course=item["course"],
                            timeframe=item.get("timeframe", "all")
                        )
                    elif operation == "generate_feedback":
                        result = await ai_service.generate_automated_feedback(
                            student=item["student"],
                            material=item["material"],
                            submission_content=item["submission"],
                            feedback_type=item.get("feedback_type", "comprehensive")
                        )
                    else:
                        raise ValueError(f"Unknown operation: {operation}")
                    
                    return {
                        "item_id": item.get("id"),
                        "status": "success",
                        "result": result
                    }
                except Exception as e:
                    return {
                        "item_id": item.get("id"),
                        "status": "error",
                        "error": str(e)
                    }
        
        # Create tasks for all items
        for item in items:
            task = asyncio.create_task(process_item(item))
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)
        return results

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