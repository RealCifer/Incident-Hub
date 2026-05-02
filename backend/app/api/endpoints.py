from fastapi import APIRouter, status, HTTPException
from app.models.signal import Signal
from app.models.work_item import (
    WorkItemTransitionRequest,
    WorkItemResponse,
    WorkItemState,
    WorkItemStateMachine,
    InvalidStateTransitionError,
    RcaMissingError,
    RCARequest,
    RCAResponse,
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

    # 3. Block RESOLVED → CLOSED if no RCA has been submitted
    if target_state == WorkItemState.CLOSED and not doc.get("rca"):
        try:
            raise RcaMissingError(workitem_id)
        except RcaMissingError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e),
            )

    # 4. Persist atomically — filter on current state to guard concurrent requests
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


# ── RCA endpoints ─────────────────────────────────────────────────────────────

@router.post(
    "/rca/{work_item_id}",
    response_model=WorkItemResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit an RCA for a RESOLVED WorkItem",
    description=(
        "Submits a Root Cause Analysis for the given WorkItem. "
        "The WorkItem must be in RESOLVED state. "
        "MTTR (Mean Time To Resolve) is auto-calculated as `end_time - start_time` and stored in seconds. "
        "An RCA is required before the WorkItem can be moved to CLOSED."
    ),
)
async def submit_rca(work_item_id: str, body: RCARequest):
    # 1. Validate end_time > start_time
    if body.end_time <= body.start_time:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"end_time must be after start_time. Got start={body.start_time.isoformat()}, end={body.end_time.isoformat()}",
        )

    # 2. Auto-calculate MTTR
    mttr_seconds = (body.end_time - body.start_time).total_seconds()

    # 3. Build the RCA payload (plain dict for MongoDB storage)
    rca_data = {
        "root_cause_category": body.root_cause_category,
        "fix_applied": body.fix_applied,
        "prevention_steps": body.prevention_steps,
        "start_time": body.start_time,
        "end_time": body.end_time,
        "mttr_seconds": mttr_seconds,
    }

    # 4. Persist — submit_rca guards that WorkItem must be in RESOLVED state
    updated = await mongo_client.submit_rca(
        workitem_id=work_item_id,
        rca_data=rca_data,
    )

    if not updated:
        # Either WorkItem doesn't exist or it isn't in RESOLVED state
        doc = await mongo_client.get_work_item(work_item_id)
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"WorkItem '{work_item_id}' not found.",
            )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"RCA can only be submitted for a WorkItem in RESOLVED state. "
                f"Current state is '{doc['state']}'."
            ),
        )

    return WorkItemResponse(**{k: v for k, v in updated.items() if k != "_id"})
