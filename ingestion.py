import socket
import struct
from datetime import datetime

import psycopg2
from redis import Redis

from ccsds_parser import parse_ccsds_header
from xtce_parser import XtceParser


conn = psycopg2.connect("postgres://postgres:space@localhost:5432/space")
conn.autocommit = True
r = Redis(host="localhost", port=6379, db=0)


UDP_IP = "127.0.0.1"
UDP_PORT = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

METRIC_VOLTAGE = 1
METRIC_TEMPERATURE = 2

HEADER_FORMAT = "!HHI"
HEADER_SIZE = 6


print(f"📡 Ground Station listening on {UDP_PORT}...")


parser = XtceParser("telemetry_def.xml")

try:
    while True:
        print("Listening...")
        raw_data, addr = sock.recvfrom(1024)
        if len(raw_data) < HEADER_SIZE:
            print(f"⚠️ Corrupt packet received from {addr}, length too short {len(raw_data)}...")
            continue

        # split data
        header_bytes = raw_data[:HEADER_SIZE]

        # decode header
        header = parse_ccsds_header(header_bytes=header_bytes)
        apid = header.get("apid")
        seq_count = header.get("seq_count")
        payload_length = header.get("length")
        print(f"📦 Pkt Rx | APID: {apid} | Seq: {seq_count} | PayLoad Len: {payload_length}")

        payload_bytes = raw_data[HEADER_SIZE:HEADER_SIZE + payload_length]

        if apid == 100:
            # if len(payload_bytes) != payload_length:
            #     print(f"⚠️  Size Mismatch! Header said {payload_length}, but got {len(payload_bytes)}")
            #     continue

            decoded_data = parser.decode(apid, payload_bytes)
            if decoded_data is None:
                print(f"Failed to decode packed for apid: {apid}")
                continue
            voltage = decoded_data.get("Battery_Voltage")
            temperature = decoded_data.get("Solar_Temp")
            # voltage, temperature = struct.unpack("!ff", payload_bytes)
            print(f"   └── 🔋 Voltage: {voltage:.2f}V | 🌡️ Temp: {temperature:.2f}C")

            now = datetime.now()
            pipe = r.pipeline()
            pipe.set("sat:1:voltage", voltage)
            pipe.set("sat:1:temperature", temperature)
            pipe.set("sat:1:last_contact", now.isoformat())
            pipe.execute()

            cursor = conn.cursor()
            sql = """
                INSERT INTO telemetry (timestamp, satellite_id, metric_id, value)
                VALUES (%s, %s, %s, %s), (%s, %s, %s, %s);
            """
            cursor.execute(sql, (
                now.isoformat(), 1, METRIC_VOLTAGE, voltage,
                now.isoformat(), 1, METRIC_TEMPERATURE, temperature,
            ))

            print(f"   └── 💾 Saved: {voltage:.2f}V | {temperature:.2f}C")

        elif apid == 200:
            pass
        else:
            print(f"   └── ❓ Unknown APID: {apid}")
except KeyboardInterrupt:
    print("Ground station shutting down...")
    sock.close()
    conn.close()


