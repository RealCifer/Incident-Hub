import redis.asyncio as redis
from typing import Optional

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

    async def push_to_queue(self, queue_name: str, data: dict):
        if self.client:
            import json
            stringified_data = json.dumps(data)
            await self.client.rpush(queue_name, stringified_data)

redis_client = RedisClient()
