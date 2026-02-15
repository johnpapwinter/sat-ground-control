import struct


CLCW_SIZE = 4


def pack_clcw(report_value: int) -> bytes:
    word = 0
    word |= (1 & 0x03) << 24
    word |= (report_value & 0xFF) << 1

    return struct.pack("!I", word)


def parse_clcw(clcw_bytes: bytes) -> dict:
    (word,) = struct.unpack("!I", clcw_bytes)

    return {
        "report_value": (word >> 1) & 0xFF
    }


