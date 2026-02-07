from datetime import datetime

from pydantic import BaseModel


class TelemetryPoint(BaseModel):
    timestamp: datetime
    value: float

    class Config:
        from_attributes = True


class CommandPoint(BaseModel):
    opcode: int
    frequency: float


class LastStatus(BaseModel):
    voltage: float
    temperature: float
    last_contact: datetime

