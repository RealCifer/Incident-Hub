from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Any

class Signal(BaseModel):
    component_id: str = Field(..., description="The ID of the component emitting the signal")
    payload: Any = Field(..., description="Arbitrary signal payload data")
