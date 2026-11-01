import sys
import logging
import uuid
from collections.abc import Sequence

logger = logging.getLogger(__name__)
del logging

DEFAULT_PORT = 5568

# Generate a CID (required by E1.31)
# This is just some random UUID I created with standard tools
# I don't see any reason why it can't be used on every project,
# unless there are two PACN emitters on the same network.
_DEFAULT_CID_STR = "b3cec3cb-caab-439c-a5d3-f7755137975a"
_cid_object = uuid.UUID(_DEFAULT_CID_STR)
DEFAULT_CID_BYTES = _cid_object.bytes

def sigterm_handler(*_x):
    logger.info("Received SIGTERM, shutting down")
    sys.exit(0)

def check_universe(universe: int, u_min=1) -> None:
    assert u_min <= universe < 64000

def valid_source_name(s: str) -> bytearray:
    b0 = bytearray(s, "UTF-8")
    lenb0 = len(b0)
    assert lenb0 < 64
    b1 = bytearray(64-lenb0)
    return b0 + b1

def valid_dmx(x: Sequence[int]) -> list[int]:
    b = bytes(x)
    assert len(b) <= 512
    return list(x)

def valid_priority(i: int) -> int:
    assert 0 <= i <= 200
    return i

def bytes_to_int(b: bytes) -> int:
    if len(b) != 2:
        raise ValueError("Need exactly two bytes")
    return (b[0] << 8) + b[1]

def int_to_bytes(i: int) -> bytearray:
    """
    Converts a single integer number to an list with the length 2 with highest
    byte first.
    The returned list contains values in the range [0-255]
    :param integer: the integer to convert
    :return: the list with the high byte first
    """
    assert 0 <= i <= 65535
    return bytearray([(i >> 8) & 0xFF, i & 0xFF])

def encode_length(i: int) -> bytearray:
    assert 0 <= i << 0xFFF
    i1 = i >> 8 + 0xF0
    i2 = i & 0xFF
    return bytearray([i1, i2])

PREAMBLE = bytes([0, 0x10, 0, 0, 0x41, 0x53, 0x43, 0x2d, 0x45,
                0x31, 0x2e, 0x31, 0x37, 0x00, 0x00, 0x00])
VECTOR_ROOT = bytes([0, 0, 0, 0x4])
VECTOR_ROOT_EXTENDED = bytes([0, 0, 0, 0x8])
VECTOR_DATA = bytes([0, 0, 0, 0x02])
VECTOR_EXTENDED_DISCOVERY = bytes([0, 0, 0, 0x02])
VECTOR_DMP_SET = 0x02
VECTOR_EXTENDED_SYNCH = bytes([0, 0, 0, 0x1])
VECTOR_UNIVERSE_LIST = bytes([0, 0, 0, 0x1])



