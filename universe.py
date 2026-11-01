from threading import RLock

from . import utils as UT
from .colors import get_rgb

class Universe:
    def __init__(self, cid: bytes, n: int, ip: str, size: int, *,
                source_name='PACN') -> None:
        assert 1 <= n <= 63999
        self.cid = cid
        self.n = n
        self.ip = ip
        self.size = size
        self.source_name = source_name 
        self.t_last_sent = 0.0
        self._packet = _DataPacket(cid, source_name, n, bytearray(size))
        self._dirty = True
        self._shutdown_count = -1
        self.uni_lock = RLock()

    @property
    def dirty(self) -> bool:
        return self._dirty

    @property
    def rgb_data(self) -> bytearray:
        return self._packet.dmx_data

    @property
    def packet(self) -> _DataPacket:
        return self._packet

    @property
    def packet_data(self) -> bytearray:
        return self._packet.bx

    @property
    def shutdown_count(self) -> int:
        return self._shutdown_count

    def transmitted(self) -> None:
        # Call this after a successful transmission
        # increments the repeat count, marks me as clean
        with self.uni_lock:
            if self._shutdown_count < 0:
                self._dirty = False
            else:
                self._shutdown_count += 1
            self._packet.increment_sequence()

    def set_rgb(self, x: bytearray) -> None:
        if self._shutdown_count >= 0:
            return
        with self.uni_lock:
            if len(x) != self.size:
                raise ValueError(f"Wrong data length in universe {self.n}")
            self._packet.set_dmx_data(x)
            self._mark_me_dirty()

    def set_stream_terminated(self, b=True) -> None:
        self._packet.stream_terminated = b
        self._packet.refresh()
        self._mark_me_dirty()

    def shutdown(self) -> None:
        with self.uni_lock:
            self._set_exit_data()
            self._dirty = True
            self._shutdown_count = 0  # Initiates shutdown sequence

    def _set_exit_data(self) -> None:
        self.set_rgb(bytearray(self.size)) # All pixels off

    def _mark_me_dirty(self) -> None:
        with self.uni_lock:
            self._dirty = True

class RGBUniverse(Universe):
    def __init__(self, cid: bytes, n: int, ip: str, pixel_count: int, 
                 **kwds) -> None:
        """
        cid: identifier required by E1.31
        n: Universe number
        ip: network address of the PixelController or equivalent
        pixel_count: number of pixels in the universe
        kwds: the only valid keyword is source_name, a string identifying
              the program.  It has no signifance and defaults to "PACN".
        """
        super().__init__(cid, n, ip, pixel_count*3, **kwds)
        self._pixels: list[str] = ["#000000"] * pixel_count

    def __len__(self) -> int:
        return len(self._pixels)

    def pixels(self) -> list[str]:
        """Return a copy of the pixel list."""
        with self.uni_lock:
            return self._pixels[:]
 
    def change_pixel(self, i: int, s: str) -> None:
        with self.uni_lock:
            self._pixels[i] = s
            for n, a in enumerate(get_rgb(s), i*3):
                self.packet.poke(n, a)
            self._mark_me_dirty()

    def set_pixel_data(self, pixels: list[str]) -> None:
        """
        pixels: a list of strings defining the state all of the pixels.
        """    
        with self.uni_lock:
            self._pixels = pixels
            self._update_pixels()

    def _update_pixels(self) -> None:
        b = bytearray()
        for p in self._pixels:
            b.extend(get_rgb(p))
        self.set_rgb(b)

class _PacketRoot:
    def __init__(self, cid: bytes, root_vector: bytes, universe=0,
                    sync_universe=0) -> None:
        if len(root_vector) != 4:
            raise ValueError('the length of the vector is not 4!')
        self.cid = cid
        self.root_vector = root_vector
        self.universe = universe
        self.sync_universe = sync_universe

    def length(self) -> int:
        raise NotImplementedError

    def get_bytes(self) -> bytearray:
        '''Returns the Root layer as a bytearray'''
        b: bytearray = bytearray()
        b.extend(UT.PREAMBLE)
        # first append the high byte from the Flags and Length
        # high 4 bit: 0x7 then the bits 8-11(indexes) from _length
        length = self.length() - 16
        b.extend(UT.encode_length(length))

        b.extend(self.root_vector)
        b.extend(self.cid)

        return b

class _DataPacket(_PacketRoot):
    def __init__(self, cid: bytes, source_name: str, 
                       universe: int, dmx_data: bytearray, *,
                 priority = 100,
                 sequence = 0, 
                 stream_terminated = False, 
                 preview_data = False,
                 force_sync = False, 
                 sync_universe = 0, 
                 dmx_start_code = 0) -> None:
        super().__init__(cid, UT.VECTOR_ROOT, universe, sync_universe)
        # Source name, padded with 0s to a length of 64 bytes
        self.source_name = UT.valid_source_name(source_name)
        self._dmx_data = dmx_data
        self.priority = priority
        self.sequence = sequence % 256
        self.dmx_start_code = dmx_start_code
        self.stream_terminated = stream_terminated
        self.preview_data = preview_data
        self.force_sync = force_sync
        self.bx = self.get_bytes()

    def __str__(self) -> str:
        return (f'sACN DataPacket: Universe: {self.universe}, '
                f'Priority: {self.priority}, Sequence: {self.sequence}, '
                f'CID: {self.cid!r}')

    @property
    def dmx_data(self) -> bytearray:
        return self._dmx_data

    def refresh(self) -> None:
        self.bx = self.get_bytes()

    def length(self) -> int:
        return 126 + len(self._dmx_data)

    def increment_sequence(self) -> None:
        self.sequence = (self.sequence+1) % 256
        self.bx[111] = self.sequence # Nothing else changes in the data

    def poke(self, i: int, a: int) -> None:
        """Pokes one r, g, b directly into the pixel data part of the
        packet.  Pixel data begins at index 126."""
        self.bx[126 + i] = a

    def set_dmx_data(self, dmx_data: bytearray) -> None:
        self._dmx_data = dmx_data
        self.bx = self.get_bytes()

    def get_bytes(self) -> bytearray:
        x: bytearray = super().get_bytes()
        # Framing layer
        x.extend(UT.encode_length(self.length() - 38))
        x.extend(UT.VECTOR_DATA)
        x.extend(self.source_name)
        x.append(self.priority)
        x.extend(UT.int_to_bytes(self.sync_universe))
        x.append(self.sequence)
        flags = 0
        # flag to terminate this universe's stream
        flags += int(self.stream_terminated) << 6
        # flag indicating that this data is not for display
        flags += int(self.preview_data) << 7
        # force synchronization (I don't know what that means)
        flags += int(self.force_sync) << 5
        x.append(flags)
        # universe number
        x.extend(UT.int_to_bytes(self.universe))

        # Data layer
        x.extend(UT.encode_length(self.length() - 115))
        x.append(UT.VECTOR_DMP_SET)
        # Some static values (Address & Data Type, First Property addr, ...)
        x.extend([0xa1, 0x00, 0x00, 0x00, 0x01])
        dmx_len = len(self._dmx_data)+1
        x.extend(UT.int_to_bytes(dmx_len))
        # At last, the actual data!
        x.append(self.dmx_start_code)
        x.extend(self._dmx_data)
        return x
