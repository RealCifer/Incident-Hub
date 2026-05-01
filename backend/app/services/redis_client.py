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

    async def push_to_stream(self, stream_name: str, data: dict, maxlen: int = 100000):
        if self.client:
            # We can use XADD with MAXLEN to limit the stream size
            # Ensure all values in the dict are strings/bytes for redis stream
            stringified_data = {k: str(v) for k, v in data.items()}
            await self.client.xadd(name=stream_name, fields=stringified_data, maxlen=maxlen)

redis_client = RedisClient()
