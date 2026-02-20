import json

from redis import Redis
from sqlalchemy.orm import Session

from ground.domain.enums import CommandState
from ground.domain.models import Telemetry, PacketGap, CommandEntry


class IngestionRepository:
    def __init__(self, db: Session, redis: Redis) -> None:
        self.db = db
        self.redis = redis

    def save_telemetry(self, telemetry: Telemetry) -> None:
        self.db.add(telemetry)
        self.db.commit()

    def save_current_telemetry(self, telemetry: Telemetry) -> None:
        pipe = self.redis.pipeline()
        metric_name = "voltage" if telemetry.metric_id == 1 else "temperature"
        pipe.set(f"sat:1:{metric_name}", telemetry.value)
        pipe.set("sat:1:last_contact", telemetry.timestamp.isoformat())
        pipe.execute()

    def log_gap_to_db(self, packet_gap: PacketGap) -> None:
        self.db.add(packet_gap)
        self.db.commit()

    def publish_alert(self, packet_gap: PacketGap) -> None:
        self.redis.publish("alerts:packet_gap", json.dumps({
            "timestamp": packet_gap.timestamp.isoformat(),
            "satellite_id": packet_gap.satellite_id,
            "apid": packet_gap.apid,
            "expected_seq": packet_gap.expected_seq,
            "received_seq": packet_gap.received_seq,
            "gap_size": packet_gap.gap_size,
        }))

    def save_clcw(self, clcw: dict) -> None:
        self.redis.publish("clcw:update", json.dumps(clcw))

    def update_command_entry(self, command_id: int, state: CommandState) -> None:
        if command_id is None:
            return
        entry = self.db.get(CommandEntry, command_id)
        if entry:
            entry.state = state
            self.db.commit()

