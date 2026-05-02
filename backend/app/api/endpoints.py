import logging
from collections import Counter
from datetime import datetime
from fastapi import APIRouter, status, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
from app.models.signal import Signal
from app.models.work_item import (
    WorkItemTransitionRequest,
    WorkItemResponse,
    WorkItemState,
    WorkItemStateMachine,
    InvalidStateTransitionError,
    RcaMissingError,
    RCARequest,
    DashboardResponse,
)
from app.services.redis_client import redis_client
from app.services.mongo_client import mongo_client

logger = logging.getLogger(__name__)
router = APIRouter()


def _doc_to_response(doc: dict) -> WorkItemResponse:
    """Strip Mongo's _id and coerce to WorkItemResponse."""
    return WorkItemResponse(**{k: v for k, v in doc.items() if k != "_id"})


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health")
async def health_check():
    return {"status": "ok", "message": "Backend is running!"}


# ── Signals ───────────────────────────────────────────────────────────────────

@router.post("/signals", status_code=status.HTTP_202_ACCEPTED)
async def ingest_signal(signal: Signal):
    await redis_client.push_to_queue("signals_queue", signal.model_dump(mode="json"))
    return {"status": "accepted", "message": "Signal queued for processing"}


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    summary="Active incidents dashboard",
    description=(
        "Returns all active (non-CLOSED) incidents. "
        "Served from the Redis cache for zero DB latency. "
        "Falls back to MongoDB on cold start and warms the cache automatically."
    ),
)
async def get_dashboard():
    served_from_cache = True

    # 1. Try Redis cache first
    incidents_raw = await redis_client.get_dashboard_from_cache()

    if incidents_raw is None:
        # Cache is cold (key doesn't exist) — warm it from MongoDB
        logger.info("Dashboard cache miss — warming from MongoDB")
        served_from_cache = False
        db_incidents = await mongo_client.get_active_work_items()
        await redis_client.rebuild_dashboard_cache(db_incidents)
        incidents_raw = db_incidents

    # 2. Sort by severity then created_at descending
    severity_weights = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

    def _sort_key(wi: dict):
        sev = wi.get("severity", "MEDIUM")
        sev_weight = severity_weights.get(sev, 2)
        ct = wi.get("created_at")
        ct_str = ct if isinstance(ct, str) else (ct.isoformat() if ct else "")
        # Sort by weight asc (critical first) then time desc
        return (sev_weight, -datetime.fromisoformat(ct_str.replace("Z", "+00:00")).timestamp() if ct_str else 0)

    sorted_incidents = sorted(incidents_raw, key=_sort_key)

    # 3. Count by state
    counts = Counter(wi.get("state", "UNKNOWN") for wi in sorted_incidents)

    # 4. Build response — coerce each raw dict through WorkItemResponse
    incident_responses = [_doc_to_response(wi) for wi in sorted_incidents]

    return DashboardResponse(
        total_active=len(incident_responses),
        counts_by_state=dict(counts),
        incidents=incident_responses,
        served_from_cache=served_from_cache,
    )


# ── WorkItems ─────────────────────────────────────────────────────────────────

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
    return _doc_to_response(doc)


@router.patch(
    "/workitems/{workitem_id}/transition",
    response_model=WorkItemResponse,
    summary="Transition a WorkItem to the next state",
)
async def transition_work_item(workitem_id: str, body: WorkItemTransitionRequest):
    # 1. Fetch current WorkItem
    doc = await mongo_client.get_work_item(workitem_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"WorkItem '{workitem_id}' not found.",
        )

    current_state = WorkItemState(doc["state"])
    target_state = body.target_state

    # 2. Validate via State Machine
    machine = WorkItemStateMachine(current_state)
    try:
        machine.transition(target_state)
    except InvalidStateTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    # 3. Block RESOLVED → CLOSED without RCA
    if target_state == WorkItemState.CLOSED and not doc.get("rca"):
        try:
            raise RcaMissingError(workitem_id)
        except RcaMissingError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e),
            )

    # 4. Persist atomically (optimistic concurrency guard)
    logger.info("attempting_state_transition", extra={
        "workitem_id": workitem_id,
        "target_state": body.target_state
    })
    updated = await mongo_client.transition_work_item_state(
        workitem_id=workitem_id,
        current_state=current_state.value,
        target_state=target_state.value,
    )

    if not updated:
        fresh = await mongo_client.get_work_item(workitem_id)
        actual = fresh["state"] if fresh else "unknown"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"State was already changed by a concurrent request. "
                f"Current state is now '{actual}'."
            ),
        )

    # 5. Update dashboard cache (CLOSED → evict, else upsert)
    clean = {k: v for k, v in updated.items() if k != "_id"}
    await redis_client.cache_incident(clean)

    return _doc_to_response(clean)


# ── RCA ───────────────────────────────────────────────────────────────────────

@router.post(
    "/rca/{work_item_id}",
    response_model=WorkItemResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit an RCA for a RESOLVED WorkItem",
    description=(
        "Submits a Root Cause Analysis for the given WorkItem. "
        "The WorkItem must be in RESOLVED state. "
        "MTTR is auto-calculated as end_time - start_time and stored in seconds. "
        "An RCA is required before the WorkItem can be moved to CLOSED."
    ),
)
async def submit_rca(work_item_id: str, body: RCARequest):
    # 1. Validate time ordering
    if body.end_time <= body.start_time:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"end_time must be after start_time. "
                f"Got start={body.start_time.isoformat()}, end={body.end_time.isoformat()}"
            ),
        )

    # 2. Auto-calculate MTTR
    mttr_seconds = (body.end_time - body.start_time).total_seconds()

    # 3. Build RCA dict for MongoDB
    rca_data = {
        "root_cause_category": body.root_cause_category,
        "fix_applied": body.fix_applied,
        "prevention_steps": body.prevention_steps,
        "start_time": body.start_time,
        "end_time": body.end_time,
        "mttr_seconds": mttr_seconds,
    }

    # 4. Persist (guards WorkItem must be RESOLVED)
    updated = await mongo_client.submit_rca(workitem_id=work_item_id, rca_data=rca_data)

    if not updated:
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

    # 5. Update dashboard cache with RCA-enriched doc (still RESOLVED, still active)
    clean = {k: v for k, v in updated.items() if k != "_id"}
    await redis_client.cache_incident(clean)

    return _doc_to_response(clean)


@router.get(
    "/workitems/{workitem_id}/signals",
    summary="Get all signals for a WorkItem",
)
async def get_workitem_signals(workitem_id: str):
    signals = await mongo_client.get_signals_by_workitem(workitem_id)
    return signals
@router.get(
    "/health",
    summary="Service Health Check",
    description="Checks the connectivity to Redis and MongoDB."
)
async def health_check():
    redis_ok = await redis_client.ping()
    mongo_ok = await mongo_client.ping()
    
    status_code = status.HTTP_200_OK if redis_ok and mongo_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "pass" if redis_ok and mongo_ok else "fail",
            "dependencies": {
                "redis": "connected" if redis_ok else "disconnected",
                "mongodb": "connected" if mongo_ok else "disconnected"
            }
        }
    )
