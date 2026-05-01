from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.services.redis_client import redis_client
import time

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests_per_second: int = 1000):
        super().__init__(app)
        self.max_requests_per_second = max_requests_per_second

    async def dispatch(self, request: Request, call_next):
        # Only apply rate limiting to the signals ingestion endpoint
        if request.url.path.endswith("/signals") and request.method == "POST":
            client_ip = request.client.host if request.client else "unknown"
            current_second = int(time.time())
            redis_key = f"rate_limit:signals:{client_ip}:{current_second}"
            
            if redis_client.client:
                try:
                    pipe = redis_client.client.pipeline()
                    pipe.incr(redis_key)
                    pipe.expire(redis_key, 2)  # Short TTL for per-second window
                    results = await pipe.execute()
                    
                    request_count = results[0]
                    if request_count > self.max_requests_per_second:
                        return JSONResponse(status_code=429, content={"detail": "Too Many Requests"})
                except Exception as e:
                    # In case of redis error, we probably don't want to block ingestion entirely,
                    # but logging the error would be good. We'll let it pass through for now.
                    pass
                    
        response = await call_next(request)
        return response
