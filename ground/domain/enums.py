from enum import Enum


class CommandPriority(Enum):
    EMERGENCY = "EMERGENCY"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class CommandState(Enum):
    QUEUED = "QUEUED"
    SENT = "SENT"
    AWAITING_ACK = "AWAITING_ACK"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"
