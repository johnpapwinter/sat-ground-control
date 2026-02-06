import struct


def create_ccsds_header(apid, seq_count, payload_length, is_command=False):
    # byte 0-1: packet identification (16 bits)
    version = 0b000 # always 0
    packet_type = 1 if is_command else 0 # 1=command, 0=telemetry
    sec_header_flag = 0 # 0=no secondary header, 1=has secondary

    packet_id = (version << 13) | (packet_type << 12) | (sec_header_flag << 11) | (apid & 0x7FF)

    # byte 2-3: packet sequence control (16 bits)
    seq_flags =  0b11 # 11 = unsegmented packet

    sequence_control = (seq_flags << 14) | (seq_count & 0x3FFF)

    # byte 4-5: packet data length
    packet_length = payload_length - 1

    # pack all three 16-bit fields
    header = struct.pack("!HHH", packet_id, sequence_control, packet_length)

    return header


def parse_ccsds_header(header_bytes):
    packet_id, sequence_control, packet_length = struct.unpack("!HHH", header_bytes)

    version = (packet_id >> 13) & 0x07
    packet_type = (packet_id >> 12) & 0x01
    sec_header_flag = (packet_id >> 11) & 0x01
    apid = packet_id & 0x7FF

    seq_flags = (sequence_control >> 14) & 0x03
    seq_count = sequence_control & 0x3FFF

    length = packet_length + 1

    return {
        "version": version,
        "type": "command" if packet_type == 1 else "telemetry",
        "sec_header_flag": sec_header_flag,
        "apid": apid,
        "seq_flags": seq_flags,
        "seq_count": seq_count,
        "length": length,
    }
