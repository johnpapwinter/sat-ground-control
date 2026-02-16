import json
import logging
import socket
import struct
import threading

from redis import Redis

from common.ccsds_parser import create_ccsds_header
from db_clients import client as redis_client
from ground.ingestion.ingestion_settings import IngestionSettings, get_ingestion_settings

log = logging.getLogger(__name__)

SEQUENCE_MODULO = 256
OPCODE_UNLOCK = 0xFF


class FOPService:
    def __init__(self, redis: Redis, settings: IngestionSettings):
        self.redis = redis
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.send_seq = 0
        self.last_ack = 0
        self.waiting_for_ack = False
        self.current_payload = b""

        self.lockout = False
        self.wait = False
        self.retransmit = False

        self.clcw_event = threading.Event()
        self.settings = settings

    def listen_clcw(self) -> None:
        pubsub = self.redis.pubsub()
        pubsub.subscribe("clcw:update")

        for message in pubsub.listen():
            if message["type"] != "message":
                continue
            clcw = json.loads(message["data"])
            self.last_ack = clcw["report_value"]
            self.lockout = clcw.get("lockout", False)
            self.wait = clcw.get("wait", False)
            self.retransmit = clcw.get("retransmit", False)

            log.info(
                f"📡 CLCW received: N(R)={self.last_ack} "
                f"lockout={self.lockout} wait={self.wait} retransmit={self.retransmit}"
            )
            self.clcw_event.set()

    def send_frame(self, payload: bytes) -> None:
        header = create_ccsds_header(
            apid=self.settings.command_id,
            seq_count=self.send_seq,
            payload_length=len(payload),
            is_command=True
        )
        packet = header + payload
        self.sock.sendto(packet, (self.settings.udp_ip, self.settings.udp_cmd_port))
        log.info(f"📤 Sent command seq={self.send_seq} ({len(packet)} bytes)")

    def send_unlock(self) -> None:
        payload = struct.pack("!I", OPCODE_UNLOCK)
        header = create_ccsds_header(
            apid=self.settings.command_id,
            seq_count=0,
            payload_length=len(payload),
            is_command=True
        )
        packet = header + payload
        self.sock.sendto(packet, (self.settings.udp_ip, self.settings.udp_cmd_port))
        log.info("🔓 Sent UNLOCK directive to satellite")

    def handle_lockout(self) -> bool:
        log.warning("🔒 Satellite is in LOCKOUT. Sending unlock directive...")
        self.send_unlock()

        self.clcw_event.clear()
        got_clcw = self.clcw_event.wait(timeout=self.settings.fop_timeout_seconds)

        if got_clcw and not self.lockout:
            self.send_seq = self.last_ack
            log.info(f"🔓 Lockout cleared. Re-synced V(S) to {self.send_seq}")
            return True

        log.error("🔒 Lockout persists after unlock attempt")
        return False

    def wait_for_ack(self) -> bool:
        for attempt in range(self.settings.fop_max_retries):
            self.clcw_event.clear()
            got_clcw = self.clcw_event.wait(timeout=self.settings.fop_timeout_seconds)

            if got_clcw and self._is_acked(self.last_ack):
                return True

            if not got_clcw:
                log.warning(
                    f"⏱️ Timeout waiting for ack (attempt {attempt + 1}/{self.settings.fop_max_retries}), "
                    f"retransmitting seq={self.send_seq}"
                )
                self.send_frame(self.current_payload)

            if self.lockout:
                cleared = self.handle_lockout()
                if cleared:
                    self.send_frame(self.current_payload)
                    continue
                else:
                    return False

            if self.wait:
                log.info("⏸️ Satellite signalling WAIT — pausing until buffer clears...")
                while self.wait:
                    self.clcw_event.clear()
                    self.clcw_event.wait(timeout=self.settings.fop_timeout_seconds)
                log.info("▶️ Wait cleared, retransmitting")
                self.send_frame(self.current_payload)
                continue

            if self.retransmit:
                log.warning(
                    f"🔄 Satellite requesting retransmit from N(R)={self.last_ack} "
                    f"(we sent seq={self.send_seq})"
                )
                self.send_seq = self.last_ack
                self.send_frame(self.current_payload)
                continue

            if self._is_acked(self.last_ack):
                return True
            
        return False

    def _is_acked(self, report_value: int) -> bool:
        diff = (report_value - self.send_seq) % SEQUENCE_MODULO
        return 1 <= diff <= 127

    def run(self):
        log.info("🚀 FOP Service started, waiting for commands...")

        while True:
            result = self.redis.brpop([self.settings.fop_queue_key], timeout=1)
            if result is None:
                continue

            _, raw_command = result
            command = json.loads(raw_command)
            self.current_payload = self.build_payload(command)

            log.info(f"📋 Dequeued command: {command}")

            self.send_frame(self.current_payload)
            acked = self.wait_for_ack()

            if acked:
                self.send_seq = (self.send_seq + 1) % 256
                log.info(f"✅ Command acknowledged, next seq={self.send_seq}")
            else:
                log.error(f"❌ Command seq={self.send_seq} failed after {self.settings.fop_max_retries} retries")

    def build_payload(self, command: dict) -> bytes:
        opcode = command["opcode"]
        if opcode == 2:
            return struct.pack("!If", opcode, command.get("frequency", 1.0))
        else:
            return struct.pack("!I", opcode)


def main():
    settings = get_ingestion_settings()

    fop_service = FOPService(redis_client, settings)

    clcw_thread = threading.Thread(target=fop_service.listen_clcw, daemon=True)
    clcw_thread.start()

    fop_service.run()


if __name__ == "__main__":
    main()
