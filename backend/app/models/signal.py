from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Any

class Signal(BaseModel):
    component_id: str = Field(..., description="The ID of the component emitting the signal")
    timestamp: datetime = Field(..., description="ISO 8601 formatted timestamp")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary signal payload data")
    severity: str = Field(..., description="Severity level of the signal (e.g., info, warning, error, critical)")
