import logging
import socket
import struct
import threading
import time
import random

from common.ccsds_parser import create_ccsds_header, parse_ccsds_header
from common.clcw import pack_clcw
from flight.farm import Farm


log = logging.getLogger(__name__)

UDP_IP = "127.0.0.1"
UDP_PORT_BROADCAST = 5005
UDP_PORT_RECEIVER = 5006
SAT_ID = 1

APID_TX = 100
APID_RX = 200
SEQ_COUNT = 1
FREQUENCY = 1

RX_HEADER_SIZE = 6

# special opcode reserved for unlock directive
OPCODE_UNLOCK = 0xFF

ADC_RESOLUTION = 4095
VOLTAGE_MAX = 36.0
TEMP_MIN = -40.0
TEMP_MAX = 160.0
TEMP_RANGE = TEMP_MAX - TEMP_MIN

PACKET_LOSS_RATE = 0.05

farm = Farm()


log.info(f"🛰️ Satellite {SAT_ID} booting up...")


def voltage_to_adc(voltage: float) -> int:
    raw = int((voltage / VOLTAGE_MAX) * ADC_RESOLUTION)
    return max(0, min(ADC_RESOLUTION, raw))

def temperature_to_adc(temperature: float) -> int:
    raw = int(((temperature - TEMP_MIN) / TEMP_RANGE) * ADC_RESOLUTION)
    return max(0, min(ADC_RESOLUTION, raw))


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

        raw_voltage = voltage_to_adc(voltage)
        raw_temperature = temperature_to_adc(temperature)

        if random.random() < PACKET_LOSS_RATE:
            log.warning(f"Packet lost (simulated RF dropout) SEQ={SEQ_COUNT}")
            SEQ_COUNT += 1
            time.sleep(FREQUENCY)
            continue

        payload = struct.pack("!ff", raw_voltage, raw_temperature)
        header = create_ccsds_header(
            apid=APID_TX,
            seq_count=SEQ_COUNT,
            payload_length=len(payload),
            is_command=False,
        )

        clcw_fields = farm.get_clcw_fields()
        clcw = pack_clcw(**clcw_fields)
        packet = header + payload + clcw

        # send to ground station
        sock.sendto(packet, (UDP_IP, UDP_PORT_BROADCAST))

        log.info(
            f"Tx: {len(packet)}B | V={voltage:.2f}V | T={temperature:.2f}C | SEQ={SEQ_COUNT} | "
            f"CLCW[N(R)={clcw_fields['report_value']} ret={clcw_fields['retransmit']} "
            f"wait={clcw_fields['wait']} lock={clcw_fields['lockout']}]"
        )
        SEQ_COUNT += 1
        time.sleep(FREQUENCY)


def command_rx():
    global SEQ_COUNT
    global FREQUENCY
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT_RECEIVER))

    log.info(f"🛰️ Listening for commands on port {UDP_PORT_RECEIVER}...")
    while True:
        try:
            raw_data, addr = sock.recvfrom(1024)

            header_bytes = raw_data[:RX_HEADER_SIZE]
            payload_bytes = raw_data[RX_HEADER_SIZE:]

            header = parse_ccsds_header(header_bytes=header_bytes)
            apid = header.get("apid")
            cmd_seq = header.get("seq_count")

            if apid != APID_RX:
                log.warning(f"Ignoring frame with unexpected APID={apid}")
                continue

            opcode = struct.unpack("!I", payload_bytes[:4])[0]

            if opcode == OPCODE_UNLOCK:
                log.info("⚠️  UNLOCK directive received")
                farm.unlock()
                continue

            accepted = farm.accept_frame(cmd_seq)
            if not accepted:
                log.warning(f"Command seq={cmd_seq} rejected by FARM")
                continue

            if opcode == 1:
                log.info("⚠️  COMMAND EXECUTED: REBOOT SYSTEM")
                SEQ_COUNT = 1
            elif opcode == 2:
                new_freq = struct.unpack("!f", payload_bytes[4:8])[0]
                log.info(f"⚠️  COMMAND EXECUTED: SET FREQ to {new_freq}s")
                FREQUENCY = new_freq
            else:
                log.warning(f"Unknown OpCode: {opcode}")

        except Exception as e:
            log.error(f"Rx Error: {e}")




def main():
    log.info(f"🛰️ Satellite {SAT_ID} booting up...")

    tx_thread = threading.Thread(target=telemetry_tx, daemon=True)
    rx_thread = threading.Thread(target=command_rx, daemon=True)

    tx_thread.start()
    rx_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("🛑 Satellite shutting down...")


if __name__ == "__main__":
    main()



