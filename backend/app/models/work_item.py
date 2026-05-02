from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class WorkItemState(str, Enum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


# Strict allowed transitions — only forward, no skipping
ALLOWED_TRANSITIONS: dict[WorkItemState, WorkItemState] = {
    WorkItemState.OPEN: WorkItemState.INVESTIGATING,
    WorkItemState.INVESTIGATING: WorkItemState.RESOLVED,
    WorkItemState.RESOLVED: WorkItemState.CLOSED,
    # CLOSED is terminal — no outgoing transitions
}


class WorkItemStateMachine:
    """
    Implements the State Pattern for WorkItem lifecycle management.
    Enforces that state transitions are strictly sequential and unidirectional.
    """

    def __init__(self, current_state: WorkItemState):
        self._state = current_state

    @property
    def state(self) -> WorkItemState:
        return self._state

    def can_transition_to(self, target: WorkItemState) -> bool:
        """Returns True if transitioning to `target` from current state is allowed."""
        allowed_next = ALLOWED_TRANSITIONS.get(self._state)
        return allowed_next == target

    def transition(self, target: WorkItemState) -> WorkItemState:
        """
        Performs the state transition.
        Raises InvalidStateTransitionError if the transition is not allowed.
        """
        if not self.can_transition_to(target):
            allowed = ALLOWED_TRANSITIONS.get(self._state)
            allowed_str = allowed.value if allowed else "none (terminal state)"
            raise InvalidStateTransitionError(
                current=self._state,
                target=target,
                allowed=allowed_str,
            )
        self._state = target
        return self._state


class InvalidStateTransitionError(Exception):
    """Raised when an invalid WorkItem state transition is attempted."""

    def __init__(self, current: WorkItemState, target: WorkItemState, allowed: str):
        self.current = current
        self.target = target
        self.allowed = allowed
        super().__init__(
            f"Invalid transition: {current.value} \u2192 {target.value}. "
            f"From '{current.value}', only '{allowed}' is allowed."
        )


class RcaMissingError(Exception):
    """Raised when a WorkItem is moved to CLOSED without a completed RCA."""

    def __init__(self, workitem_id: str):
        super().__init__(
            f"WorkItem '{workitem_id}' cannot be moved to CLOSED without a completed RCA. "
            f"Submit an RCA via POST /rca/{workitem_id} first."
        )


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class RCARequest(BaseModel):
    """Payload required to submit a Root Cause Analysis for a WorkItem."""
    root_cause_category: str = Field(
        ...,
        description="High-level category of the root cause (e.g. 'Infrastructure', 'Code Bug', 'Human Error')",
    )
    fix_applied: str = Field(
        ...,
        description="Description of the fix that was applied to resolve the incident",
    )
    prevention_steps: str = Field(
        ...,
        description="Steps to be taken to prevent this class of incident in the future",
    )
    start_time: datetime = Field(
        ...,
        description="UTC datetime when the incident started (used for MTTR calculation)",
    )
    end_time: datetime = Field(
        ...,
        description="UTC datetime when the incident was resolved (used for MTTR calculation)",
    )


class RCAResponse(BaseModel):
    """RCA data as stored on the WorkItem."""
    root_cause_category: str
    fix_applied: str
    prevention_steps: str
    start_time: datetime
    end_time: datetime
    mttr_seconds: float = Field(
        ..., description="Mean Time To Resolve in seconds (end_time - start_time)"
    )


class WorkItem(BaseModel):
    workitem_id: str
    component_id: str
    state: WorkItemState = WorkItemState.OPEN
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    rca: Optional[RCAResponse] = None


class WorkItemTransitionRequest(BaseModel):
    target_state: WorkItemState = Field(
        ..., description="The state to transition this WorkItem into"
    )


class WorkItemResponse(BaseModel):
    workitem_id: str
    component_id: str
    state: WorkItemState
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    rca: Optional[RCAResponse] = None
