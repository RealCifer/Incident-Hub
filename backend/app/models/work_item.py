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
            f"Invalid transition: {current.value} → {target.value}. "
            f"From '{current.value}', only '{allowed}' is allowed."
        )


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class WorkItem(BaseModel):
    workitem_id: str
    component_id: str
    state: WorkItemState = WorkItemState.OPEN
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


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
