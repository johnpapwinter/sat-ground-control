from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from ground.domain.enums import CommandPriority


class TelemetryPoint(BaseModel):
    timestamp: datetime
    value: float

    class Config:
        from_attributes = True


class CommandPoint(BaseModel):
    opcode: int
    frequency: Optional[float]
    priority: CommandPriority = CommandPriority.MEDIUM


class LastStatus(BaseModel):
    voltage: float
    temperature: float
    last_contact: datetime

