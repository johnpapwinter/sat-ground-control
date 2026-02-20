from datetime import timezone, datetime

from ground.ingestion.ingestion_repository import IngestionRepository
from ground.domain.models import PacketGap

SEQUENCE_MODULO = 16384


class SequenceGapDetector:
    def __init__(self, ingestion_repository: IngestionRepository):
        self.last_seen = {}
        self.repository = ingestion_repository

    def check(self, apid, seq_count):
        if apid not in self.last_seen:
            self.last_seen[apid] = seq_count
            return None

        expected = (self.last_seen[apid] + 1) % SEQUENCE_MODULO
        self.last_seen[apid] = seq_count

        if seq_count == expected:
            return None

        gap_size = (seq_count - expected) % SEQUENCE_MODULO
        now = datetime.now(timezone.utc)

        gap_event = PacketGap(
            timestamp=now,
            satellite_id=1,
            apid=apid,
            expected_seq=expected,
            received_seq=seq_count,
            gap_size=gap_size,
        )

        self.repository.log_gap_to_db(gap_event)
        self.repository.publish_alert(gap_event)

        return gap_event

