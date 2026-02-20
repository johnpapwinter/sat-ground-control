import logging
import socket

from datetime import datetime, timezone
from pathlib import Path

from common.ccsds_parser import parse_ccsds_header
from common.clcw import CLCW_SIZE, parse_clcw
from common.xtce_parser import XtceParser
from ground.ingestion.db_clients import db_session_local, client as redis_client
from ground.ingestion.ingestion_repository import IngestionRepository
from ground.ingestion.ingestion_settings import IngestionSettings, get_ingestion_settings
from ground.domain.models import Telemetry
from ground.ingestion.sequence_detector import SequenceGapDetector


log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TELEMETRY_DEF = PROJECT_ROOT / "common" / "telemetry_def.xml"



class IngestionService:
    def __init__(
            self,
            repository: IngestionRepository,
            gap_detector: SequenceGapDetector,
            xtce_parser: XtceParser,
            settings: IngestionSettings,
    ) -> None:
        self.repository = repository
        self.gap_detector = gap_detector
        self.xtce_parser = xtce_parser
        self.settings = settings

    def process_packet(self, raw_data: bytes, addr) -> None:
        visible = self.repository.redis.get(f"sat:{self.settings.satellite_id}:visible")
        if visible != b"True":
            return None

        if len(raw_data) < self.settings.header_size:
            log.error(f"⚠️ Corrupt packet received from {addr}, length too short {len(raw_data)}...")
            return None

        clcw_bytes = raw_data[-CLCW_SIZE:]
        space_packet_data = raw_data[:-CLCW_SIZE]

        clcw = parse_clcw(clcw_bytes=clcw_bytes)
        log.info(f"📡 CLCW | report_value={clcw['report_value']}")
        self.repository.save_clcw(clcw=clcw)

        header_bytes = space_packet_data[:self.settings.header_size]

        header = parse_ccsds_header(header_bytes=header_bytes)
        apid = header.get("apid")
        seq_count = header.get("seq_count")

        gap = self.gap_detector.check(apid=apid, seq_count=seq_count)
        if gap:
            log.error(f"   └── ⚠️ GAP DETECTED: lost {gap['gap_size']} packets (expected {gap['expected_seq']}, "
                  f"got {gap['received_seq']})")

        payload_length = header.get("length")
        log.info(f"📦 Pkt Rx | APID: {apid} | Seq: {seq_count} | PayLoad Len: {payload_length}")

        payload_bytes = space_packet_data[self.settings.header_size:self.settings.header_size + payload_length]

        if apid == self.settings.telemetry_id:
            decoded_data = self.xtce_parser.decode(apid=apid, payload_bytes=payload_bytes)
            if decoded_data is None:
                log.error(f"Failed to decode packed for apid: {apid}")
                return None
            voltage = decoded_data.get("Battery_Voltage")
            temperature = decoded_data.get("Solar_Temp")
            log.info(f"   └── 🔋 Voltage: {voltage:.2f}V | 🌡️ Temp: {temperature:.2f}C")
            self.save_metric(self.settings.metric_voltage, voltage)
            self.save_metric(self.settings.metric_temperature, temperature)
            log.info(f"   └── 💾 Saved: {voltage:.2f}V | {temperature:.2f}C")
            return None
        elif apid == 200:
            return None
        else:
            log.info(f"   └── ❓ Unknown APID: {apid}")
            return None

    def save_metric(self, metric_id: int, metric_value: float) -> None:
        now = datetime.now(timezone.utc)
        telemetry = Telemetry(
            timestamp=now,
            satellite_id=self.settings.satellite_id,
            metric_id=metric_id,
            value=metric_value,
        )
        self.repository.save_telemetry(telemetry=telemetry)
        self.repository.save_current_telemetry(telemetry=telemetry)

    def run(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.settings.udp_ip, self.settings.udp_port))

        try:
            while True:
                log.info("Listening...")
                raw_data, addr = sock.recvfrom(1024)
                self.process_packet(raw_data, addr)
        except KeyboardInterrupt:
            log.info("Ground station shutting down...")
            sock.close()


def main():
    settings = get_ingestion_settings()

    repository = IngestionRepository(db_session_local, redis_client)
    gap_detector = SequenceGapDetector(repository)
    xtce_parser = XtceParser(str(TELEMETRY_DEF))
    service = IngestionService(repository, gap_detector, xtce_parser, settings)
    service.run()


if __name__ == "__main__":
    main()
