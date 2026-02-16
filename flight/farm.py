import logging
from enum import Enum

log = logging.getLogger(__name__)


class FarmState(Enum):
    OPEN = "open"
    WAIT = "wait"
    LOCKOUT = "lockout"


POSITIVE_WINDOW = 10
SEQUENCE_MODULO = 256


class Farm:
    def __init__(self) -> None:
        self.receiver_frame_seq = 0
        self.state = FarmState.OPEN
        self.retransmit_flag = False

    def accept_frame(self, frame_seq: int) -> bool:
        if self.state == FarmState.LOCKOUT:
            log.warning(f"FARM in LOCKOUT — rejecting frame seq={frame_seq}. Send unlock to resume.")
            return False

        if self.state == FarmState.WAIT:
            log.warning(f"FARM in WAIT — rejecting frame seq={frame_seq}. Buffer full.")
            return False

        if frame_seq == self.receiver_frame_seq:
            self.receiver_frame_seq = (self.receiver_frame_seq + 1) % SEQUENCE_MODULO
            self.retransmit_flag = False
            log.info(f"FARM accepted seq={frame_seq}, next expected N(R)={self.receiver_frame_seq}")
            return True

        backward_distance = (self.receiver_frame_seq - frame_seq) % SEQUENCE_MODULO
        if 1 <= backward_distance <= POSITIVE_WINDOW:
            log.info(f"FARM discarding duplicate frame seq={frame_seq} (already past N(R)={self.receiver_frame_seq})")
            return False

        forward_distance = (frame_seq - self.receiver_frame_seq) % SEQUENCE_MODULO
        if 1 <= forward_distance <= POSITIVE_WINDOW:
            self.retransmit_flag = True
            log.warning(
                f"FARM gap detected: expected seq={self.receiver_frame_seq}, "
                f"got seq={frame_seq}. Setting retransmit flag."
            )
            return False

        self.state = FarmState.LOCKOUT
        self.retransmit_flag = False
        log.error(
            f"FARM entering LOCKOUT: expected seq={self.receiver_frame_seq}, "
            f"got seq={frame_seq} (distance={forward_distance}). "
            f"Ground must send unlock directive."
        )
        return False

    def unlock(self) -> None:
        log.info(f"FARM unlocked. Resetting from state={self.state.value}")
        self.state = FarmState.OPEN
        self.retransmit_flag = False

    def set_wait(self, waiting: bool) -> None:
        if waiting and self.state == FarmState.OPEN:
            self.state = FarmState.WAIT
            log.info("FARM entering WAIT state (buffer full)")
        elif not waiting and self.state == FarmState.WAIT:
            self.state = FarmState.OPEN
            log.info("FARM leaving WAIT state (buffer cleared)")

    def get_clcw_fields(self) -> dict:
        return {
            "report_value": self.receiver_frame_seq,
            "retransmit": self.retransmit_flag,
            "wait": self.state == FarmState.WAIT,
            "lockout": self.state == FarmState.LOCKOUT,
        }

