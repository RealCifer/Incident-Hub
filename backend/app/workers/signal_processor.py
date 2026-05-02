import asyncio
import json
import logging
import uuid
from app.core.config import settings
from app.services.redis_client import redis_client
from app.services.mongo_client import mongo_client
from app.core.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

class WorkerState:
    def __init__(self):
        self.processed_count = 0

state = WorkerState()

async def log_throughput():
    while True:
        await asyncio.sleep(5)
        count = state.processed_count
        state.processed_count = 0
        if count > 0:
            logger.info(f"Throughput: {count / 5.0} signals/sec ({count} signals in the last 5 seconds)")

async def consume_signals():
    queue_name = "signals_queue"
    logger.info(f"Starting signal processor on queue '{queue_name}'")
    
    while True:
        try:
            if redis_client.client:
                # BLPOP blocks until an item is available
                result = await redis_client.client.blpop(queue_name, timeout=1)
                if result:
                    _, data_bytes = result
                    data_str = data_bytes.decode('utf-8') if isinstance(data_bytes, bytes) else data_bytes
                    data = json.loads(data_str)
                    
                    component_id = data.get("component_id")
                    if component_id:
                        debounce_key = f"debounce:workitem:{component_id}"
                        
                        # Check if workitem exists for this component_id
                        workitem_id_bytes = await redis_client.client.get(debounce_key)
                        
                        if workitem_id_bytes:
                            workitem_id = workitem_id_bytes.decode('utf-8') if isinstance(workitem_id_bytes, bytes) else workitem_id_bytes
                        else:
                            # Generate a new workitem ID
                            new_workitem_id = str(uuid.uuid4())
                            
                            # Try to set it with NX (Not eXists) and EX (Expires in 10s)
                            set_result = await redis_client.client.set(debounce_key, new_workitem_id, ex=10, nx=True)
                            
                            if set_result:
                                workitem_id = new_workitem_id
                                # We successfully acquired the lock/set the key, create the workitem in DB
                                await mongo_client.create_work_item(workitem_id, component_id)
                            else:
                                # Another worker set it concurrently, get their ID
                                workitem_id_bytes = await redis_client.client.get(debounce_key)
                                if workitem_id_bytes:
                                    workitem_id = workitem_id_bytes.decode('utf-8') if isinstance(workitem_id_bytes, bytes) else workitem_id_bytes
                                else:
                                    # Fallback (should be extremely rare due to TTL, but handle just in case)
                                    workitem_id = new_workitem_id
                        
                        # Link signal to workitem
                        data["workitem_id"] = workitem_id
                    
                    # Store in MongoDB (has retry logic internally)
                    await mongo_client.store_raw_signal(data)
                    state.processed_count += 1
            else:
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error processing signal: {e}")
            await asyncio.sleep(1)

async def main():
    await redis_client.connect(settings.REDIS_URI)
    mongo_client.connect()
    
    logger.info("Worker dependencies connected")
    
    # Run throughput logger and consumer concurrently
    await asyncio.gather(
        log_throughput(),
        consume_signals()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker shutting down")
