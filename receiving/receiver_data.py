import logging

from .. import utils as UT

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
del logging

class ReceivedData:
    def __init__(self, *, cid: bytes, source_name: str,
            universe: int, dmx_data: bytes, priority: int,
            sequence: int, sync_universe: int, preview_data: bool,
            stream_terminated: bool, force_sync: bool,
            dmx_start_code: int) -> None:
        self.cid = cid
        self.source_name = source_name
        self.universe = universe
        self.dmx_data = dmx_data
        self.priority = priority
        self.sequence = sequence
        self.sync_universe = sync_universe
        self.preview_data = preview_data
        self.stream_terminated = stream_terminated
        self.force_sync = force_sync
        self.dmx_start_code = dmx_start_code

def decode_packet(bx: bytes) -> ReceivedData | None:
    if len(bx) < 126:
        raise ValueError('Data too short')
    if bx[0:len(UT.PREAMBLE)] != UT.PREAMBLE:
        raise ValueError("Incorrect preamble")
    if bx[40:44] != UT.VECTOR_DATA:
        raise ValueError("Wrong data vector")
    vector = bx[18:22]
    match vector:
        case UT.VECTOR_ROOT:
            if bx[117] != UT.VECTOR_DMP_SET:
                raise ValueError("No DMP set")
            x = ReceivedData(cid=bx[22:38], 
              source_name=bytes(bx[44:108]).decode('utf-8').replace('\0', ''),
              universe=UT.bytes_to_int(bx[113:115]),
              dmx_data = bx[126:638],
              priority=bx[108],
              sequence=bx[111],
              sync_universe=UT.bytes_to_int(bx[109:111]),
              preview_data=bool(bx[112] & 0b10000000),
              stream_terminated=bool(bx[112] & 0b01000000),
              force_sync=bool(bx[112] & 0b00100000),
              dmx_start_code=bx[125])
            return x
        case UT.VECTOR_ROOT_EXTENDED:
            logger.debug("Universe discovery packet TBD")
            return None
        case _:
            raise ValueError("Invalid root vector")
