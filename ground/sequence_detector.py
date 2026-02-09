import json
from datetime import timezone, datetime

SEQUENCE_MODULO = 16384


class SequenceGapDetector:
    def __init__(self, redis_client, db_connection):
        self.last_seen = {}
        self.redis_client = redis_client
        self.db_connection = db_connection

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

        gap_event = {
            "timestamp": now.isoformat(),
            "satellite_id": 1,
            "apid": apid,
            "expected_seq": expected,
            "received_seq": seq_count,
            "gap_size": gap_size,
        }

        self._log_to_db(gap_event, now)
        self._publish_alert(gap_event)

        return gap_event

    def _log_to_db(self, gap, now):
        cursor = self.db_connection.cursor()
        cursor.execute(
            """
            INSERT INTO packet_gaps (timestamp, satellite_id, apid, expected_seq, received_seq, gap_size)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (now, gap["satellite_id"], gap["apid"], gap["expected_seq"], gap["received_seq"], gap["gap_size"])
        )

    def _publish_alert(self, gap):
        self.redis_client.publish("alerts:packet_gap", json.dumps(gap))
