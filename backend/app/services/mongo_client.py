import logging
from datetime import datetime, timezone
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
            now = datetime.now(timezone.utc)
            await self.db.work_items.insert_one({
                "workitem_id": workitem_id,
                "component_id": component_id,
                "state": "OPEN",
                "severity": "MEDIUM",
                "created_at": now,
                "updated_at": now,
            })

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(pymongo.errors.PyMongoError),
        reraise=True
    )
    async def get_work_item(self, workitem_id: str) -> dict | None:
        """Fetch a WorkItem document by its workitem_id."""
        if self.db is not None:
            return await self.db.work_items.find_one(
                {"workitem_id": workitem_id}, {"_id": 0}
            )
        return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(pymongo.errors.PyMongoError),
        reraise=True
    )
    async def transition_work_item_state(
        self, workitem_id: str, current_state: str, target_state: str
    ) -> dict | None:
        """
        Atomically update the WorkItem state in MongoDB.
        Uses a filter on both workitem_id AND current state to prevent
        overwriting a state that was already changed by a concurrent request.
        Returns the updated document, or None if no document matched (lost race).
        """
        if self.db is not None:
            now = datetime.now(timezone.utc)
            result = await self.db.work_items.find_one_and_update(
                # Guard: only match if state is still what we expect
                {"workitem_id": workitem_id, "state": current_state},
                {"$set": {"state": target_state, "updated_at": now}},
                return_document=True,
            )
            return result
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(pymongo.errors.PyMongoError),
        reraise=True
    )
    async def submit_rca(self, workitem_id: str, rca_data: dict) -> dict | None:
        """
        Embed the RCA (including auto-calculated mttr_seconds) into the WorkItem.
        Only allowed when the WorkItem is in RESOLVED state.
        Returns the updated document, or None if not found / wrong state.
        """
        if self.db is not None:
            now = datetime.now(timezone.utc)
            result = await self.db.work_items.find_one_and_update(
                # Guard: RCA can only be submitted on a RESOLVED WorkItem
                {"workitem_id": workitem_id, "state": "RESOLVED"},
                {"$set": {"rca": rca_data, "updated_at": now}},
                return_document=True,
            )
            return result
        return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(pymongo.errors.PyMongoError),
        reraise=True
    )
    async def get_active_work_items(self) -> list[dict]:
        """
        Fetch all non-CLOSED WorkItems from MongoDB.
        Used to warm the Redis dashboard cache on cold start.
        Only returns documents that have the `state` field (filters legacy docs).
        """
        if self.db is not None:
            cursor = self.db.work_items.find(
                {
                    "state": {"$exists": True, "$ne": "CLOSED"},
                },
                {"_id": 0},
            )
            return await cursor.to_list(length=None)
        return []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(pymongo.errors.PyMongoError),
        reraise=True
    )
    async def get_signals_by_workitem(self, workitem_id: str) -> list[dict]:
        """Fetch all raw signals linked to a specific workitem_id."""
        if self.db is not None:
            cursor = self.db.raw_signals.find(
                {"workitem_id": workitem_id}, {"_id": 0}
            ).sort("timestamp", -1)
            return await cursor.to_list(length=None)
        return []

    async def ping(self) -> bool:
        """Check if MongoDB is alive."""
        if self.client:
            try:
                await self.client.admin.command("ping")
                return True
            except Exception:
                return False
        return False

mongo_client = MongoClient()
