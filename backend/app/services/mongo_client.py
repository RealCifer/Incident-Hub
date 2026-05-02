import logging
from motor.motor_asyncio import AsyncIOMotorClient
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.core.config import settings
import pymongo.errors

logger = logging.getLogger(__name__)

class MongoClient:
    def __init__(self):
        self.client = None
        self.db = None

    def connect(self):
        self.client = AsyncIOMotorClient(settings.MONGODB_URI)
        self.db = self.client[settings.MONGODB_DB_NAME]

    def disconnect(self):
        if self.client:
            self.client.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(pymongo.errors.PyMongoError),
        reraise=True
    )
    async def store_raw_signal(self, data: dict):
        if self.db is not None:
            await self.db.raw_signals.insert_one(data)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(pymongo.errors.PyMongoError),
        reraise=True
    )
    async def create_work_item(self, workitem_id: str, component_id: str):
        if self.db is not None:
            from datetime import datetime, timezone
            await self.db.work_items.insert_one({
                "workitem_id": workitem_id,
                "component_id": component_id,
                "created_at": datetime.now(timezone.utc)
            })

mongo_client = MongoClient()
