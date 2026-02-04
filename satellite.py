import socket
import struct
import threading
import time
import random

from ccsds_parser import create_ccsds_header, parse_ccsds_header

UDP_IP = "127.0.0.1"
UDP_PORT_BROADCAST = 5005
UDP_PORT_RECEIVER = 5006
SAT_ID = 1

APID_TX = 100
APID_RX = 200
SEQ_COUNT = 1
FREQUENCY = 1
LENGTH = 8

RX_HEADER_FORMAT = "!HHI"
RX_HEADER_SIZE = 6


print(f"🛰️ Satellite {SAT_ID} booting up...")


def telemetry_tx():
    global SEQ_COUNT
    global FREQUENCY
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


    while True:
        # simulate sensor readings
        # battery
        voltage = 24.0 + random.uniform(-0.5, 0.5)
        # solar panel temperature
        temperature = 15.0 + random.uniform(-2, 2)


        payload = struct.pack("!ff", voltage, temperature)
        header = create_ccsds_header(
            apid=APID_TX,
            seq_count=SEQ_COUNT,
            payload_length=len(payload),
            is_command=False,
        )

        packet = header + payload

        # send to ground station
        sock.sendto(packet, (UDP_IP, UDP_PORT_BROADCAST))

        print(f"Tx: {len(packet)} bytes | Voltage: {voltage:.2f}V | Temp: {temperature:.2f}C, SEQ: {SEQ_COUNT}")
        SEQ_COUNT += 1
        time.sleep(FREQUENCY)


def command_rx():
    global SEQ_COUNT
    global FREQUENCY
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT_RECEIVER))

    print(f"🛰️ Listening for commands on port {UDP_PORT_RECEIVER}...")
    while True:
        try:
            raw_data, addr = sock.recvfrom(1024)

            header_bytes = raw_data[:RX_HEADER_SIZE]
            payload_bytes = raw_data[RX_HEADER_SIZE:]

            header = parse_ccsds_header(header_bytes=header_bytes)
            apid = header.get("apid")
            # apid, seq, length = struct.unpack(RX_HEADER_FORMAT, header_bytes)

            if apid == APID_RX:
                opcode = struct.unpack("!I", payload_bytes[:4])[0]
                if opcode == 1:
                    print("   └── ⚠️  COMMAND RECEIVED: REBOOT SYSTEM")
                    SEQ_COUNT = 1
                elif opcode == 2:
                    new_freq = struct.unpack("!f", payload_bytes[4:8])[0]
                    print(f"   └── ⚠️  COMMAND RECEIVED: SET FREQ to {new_freq}s")
                    FREQUENCY = new_freq
                else:
                    print(f"   └── ❓ Unknown OpCode: {opcode}")
        except Exception as e:
            print(f"Rx Error: {e}")




try:
    tx_thread = threading.Thread(target=telemetry_tx, daemon=True)
    rx_thread = threading.Thread(target=command_rx, daemon=True)

    tx_thread.start()
    rx_thread.start()

    while True:
        time.sleep(FREQUENCY)
except KeyboardInterrupt:
    print("🛑 Satellite shutting down...")




