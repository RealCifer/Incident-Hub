from fastapi import APIRouter, status, HTTPException
from app.models.signal import Signal
from app.models.work_item import (
    WorkItemTransitionRequest,
    WorkItemResponse,
    WorkItemState,
    WorkItemStateMachine,
    InvalidStateTransitionError,
)
from app.services.redis_client import redis_client
from app.services.mongo_client import mongo_client

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "ok", "message": "Backend is running!"}


@router.post("/signals", status_code=status.HTTP_202_ACCEPTED)
async def ingest_signal(signal: Signal):
    await redis_client.push_to_queue("signals_queue", signal.model_dump(mode="json"))
    return {"status": "accepted", "message": "Signal queued for processing"}


# ── WorkItem endpoints ────────────────────────────────────────────────────────

@router.get(
    "/workitems/{workitem_id}",
    response_model=WorkItemResponse,
    summary="Get a WorkItem by ID",
)
async def get_work_item(workitem_id: str):
    doc = await mongo_client.get_work_item(workitem_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"WorkItem '{workitem_id}' not found.",
        )
    return WorkItemResponse(**doc)


@router.patch(
    "/workitems/{workitem_id}/transition",
    response_model=WorkItemResponse,
    summary="Transition a WorkItem to the next state",
)
async def transition_work_item(workitem_id: str, body: WorkItemTransitionRequest):
    # 1. Fetch the current WorkItem
    doc = await mongo_client.get_work_item(workitem_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"WorkItem '{workitem_id}' not found.",
        )

    current_state = WorkItemState(doc["state"])
    target_state = body.target_state

    # 2. Validate the transition via the State Machine
    machine = WorkItemStateMachine(current_state)
    try:
        machine.transition(target_state)
    except InvalidStateTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    # 3. Persist atomically — filter on current state to guard concurrent requests
    updated = await mongo_client.transition_work_item_state(
        workitem_id=workitem_id,
        current_state=current_state.value,
        target_state=target_state.value,
    )

    if not updated:
        # Another request changed the state concurrently; re-fetch and report
        fresh = await mongo_client.get_work_item(workitem_id)
        actual = fresh["state"] if fresh else "unknown"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"State was already changed by a concurrent request. "
                f"Current state is now '{actual}'."
            ),
        )

    return WorkItemResponse(**{k: v for k, v in updated.items() if k != "_id"})
