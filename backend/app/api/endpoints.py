from fastapi import APIRouter, status
from app.models.signal import Signal
from app.services.redis_client import redis_client

router = APIRouter()

@router.get("/health")
async def health_check():
    return {"status": "ok", "message": "Backend is running!"}

@router.post("/signals", status_code=status.HTTP_202_ACCEPTED)
async def ingest_signal(signal: Signal):
    # Push signal payload to redis stream without blocking on DB
    # We serialize datetime to string if needed, or let model_dump(mode="json") handle it
    await redis_client.push_to_stream("signals_stream", signal.model_dump(mode="json"))
    return {"status": "accepted", "message": "Signal queued for processing"}
