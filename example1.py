from pacn.multiverse import Multiverse
from pacn.universe import RGBUniverse
from pacn.utils import DEFAULT_CID_BYTES
from pacn.pac_logger import logging

IP = '127.0.0.1'   # Loopback for use with e131_sim.py

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

canes: list[RGBUniverse] = []

def create_canes() -> None:
    wide = ["red"] * 6 + ["white"] * 9
    narrow = ["green"] * 4 + ["white"] * 11
    size = 150
    stripes = size // len(wide)
    patterns = [wide, narrow, narrow, wide]
    for i, p in enumerate(patterns, 1):
        cane = RGBUniverse(DEFAULT_CID_BYTES, i, IP, size)
        cane.set_pixel_data(p*stripes)
        canes.append(cane)

def step(_t: float) -> None:
    for c in canes:
        pixels = c.pixels()
        pixels = pixels[-1:] + pixels[:-1]
        c.set_pixel_data(pixels)

def main() -> None:
    create_canes()
    with Multiverse(callback=step) as mv:
        for c in canes:
            mv.add_universe(c)
        mv.wait_for_kb()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
