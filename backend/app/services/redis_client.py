import json
import redis.asyncio as redis
from datetime import datetime, timezone
from typing import Optional, Any


DASHBOARD_CACHE_KEY = "dashboard:incidents"


def _serialize(data: dict) -> str:
    """JSON-serialize a dict, converting datetime objects to ISO strings."""
    def default(obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    return json.dumps(data, default=default)


def _deserialize(raw: str) -> dict:
    """JSON-deserialize a string back to a dict."""
    return json.loads(raw)


class RedisClient:
    def __init__(self):
        self.pool: Optional[redis.ConnectionPool] = None
        self.client: Optional[redis.Redis] = None

    async def connect(self, uri: str):
        self.pool = redis.ConnectionPool.from_url(uri, decode_responses=True)
        self.client = redis.Redis(connection_pool=self.pool)

    async def disconnect(self):
        if self.client:
            await self.client.close()
        if self.pool:
            await self.pool.disconnect()

    # ── Signal queue ──────────────────────────────────────────────────────────

    async def push_to_queue(self, queue_name: str, data: dict):
        if self.client:
            await self.client.rpush(queue_name, _serialize(data))

    # ── Dashboard cache ───────────────────────────────────────────────────────
    # Storage: Redis Hash  key=DASHBOARD_CACHE_KEY  field=workitem_id  value=JSON
    # Only active (non-CLOSED) WorkItems are stored. CLOSED items are evicted.

    async def cache_incident(self, workitem: dict) -> None:
        """
        Upsert a WorkItem into the dashboard cache.
        If the WorkItem is CLOSED, it is removed instead of stored.
        """
        if not self.client:
            return
        workitem_id = workitem.get("workitem_id")
        if not workitem_id:
            return
        state = workitem.get("state", "")
        if state == "CLOSED":
            # CLOSED incidents leave the active dashboard
            await self.client.hdel(DASHBOARD_CACHE_KEY, workitem_id)
        else:
            await self.client.hset(DASHBOARD_CACHE_KEY, workitem_id, _serialize(workitem))

    async def remove_incident_from_cache(self, workitem_id: str) -> None:
        """Explicitly remove a WorkItem from the dashboard cache."""
        if self.client:
            await self.client.hdel(DASHBOARD_CACHE_KEY, workitem_id)

    async def get_dashboard_from_cache(self) -> list[dict] | None:
        """
        Fetch all active incidents from the Redis hash.
        Returns None if the cache is empty (cold start / evicted).
        Returns an empty list only if the hash genuinely has no entries.
        """
        if not self.client:
            return None
        # HGETALL returns {} when the key doesn't exist — distinguish via EXISTS
        exists = await self.client.exists(DASHBOARD_CACHE_KEY)
        if not exists:
            return None
        raw_map = await self.client.hgetall(DASHBOARD_CACHE_KEY)
        return [_deserialize(v) for v in raw_map.values()]

    async def rebuild_dashboard_cache(self, incidents: list[dict]) -> None:
        """
        Bulk-load a list of active incidents into the cache (used at startup
        or after a cold cache miss to warm from MongoDB).
        Only non-CLOSED incidents are stored.
        """
        if not self.client:
            return
        pipeline = self.client.pipeline()
        for wi in incidents:
            workitem_id = wi.get("workitem_id")
            if workitem_id and wi.get("state") != "CLOSED":
                pipeline.hset(DASHBOARD_CACHE_KEY, workitem_id, _serialize(wi))
        await pipeline.execute()


redis_client = RedisClient()
