import struct


CLCW_SIZE = 4


def pack_clcw(
        report_value: int,
        retransmit: bool = False,
        wait: bool = False,
        lockout: bool = False,
) -> bytes:
    word = 0

    word |= (0b01) << 22

    if lockout:
        word |= 1 << 10

    if wait:
        word |= 1 << 9

    if retransmit:
        word |= 1 << 8

    word |= report_value & 0xFF

    return struct.pack("!I", word)


def parse_clcw(clcw_bytes: bytes) -> dict:
    (word,) = struct.unpack("!I", clcw_bytes)

    return {
        "report_value": word & 0xFF,
        "retransmit": bool((word >> 8) & 1),
        "wait": bool((word >> 9) & 1),
        "lockout": bool((word >> 10) & 1),
    }


