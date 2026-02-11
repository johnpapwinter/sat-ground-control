import socket
import struct

from common.ccsds_parser import create_ccsds_header
from common.xtce_parser import XtceParser

UDP_IP = "127.0.0.1"
UDP_PORT = 5006

parser = XtceParser("../../common/telemetry_def.xml")


def send_command(opcode: int, frequency: float) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # header = struct.pack("!HHI", 200, 0, 8)
    payload = struct.pack("!If", opcode, frequency)
    header = create_ccsds_header(
        apid=200,
        seq_count=0,
        payload_length=len(payload),
        is_command=True
    )

    packet = header + payload
    sock.sendto(packet, (UDP_IP, UDP_PORT))
    print(f"Packet sent to {UDP_IP}:{UDP_PORT}")





