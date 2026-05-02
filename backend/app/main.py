from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging
from app.api.endpoints import router as api_router
from app.services.redis_client import redis_client
from app.services.mongo_client import mongo_client
from app.api.middleware import RateLimitMiddleware

# Initialize logging before FastAPI app creation
setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: connect to Redis and MongoDB
    await redis_client.connect(settings.REDIS_URI)
    mongo_client.connect()
    yield
    # Shutdown: disconnect
    await redis_client.disconnect()
    mongo_client.disconnect()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Rate Limiter Middleware
app.add_middleware(RateLimitMiddleware, max_requests_per_second=1000)

app.include_router(api_router)
