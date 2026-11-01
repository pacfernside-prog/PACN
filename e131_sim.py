import tkinter as tk
import queue
import time
from itertools import batched

from pacn.pac_logger import logging
from pacn.colors import make_color
from pacn.receiving.receiver_udp import Receiver
from pacn.receiving.receiver_data import decode_packet, ReceivedData

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)
del logging

def main():
    root = tk.Tk()
    mf = MainFrame(root)
    mf.grid(sticky='nsew')
    root.rowconfigure(0, weight=1)
    root.columnconfigure(0, weight=1)
    with Receiver() as rvr:
        root.after_idle(check_receiver, mf, rvr)
        root.mainloop()

def check_receiver(mf: MainFrame, rvr: Receiver) -> None:
    t0 = time.monotonic()
    for n in range(1000):
        try:
            x = rvr.get_packet(block=False)
        except queue.Empty:
            break
        if x is None:
            break
        # print("Got packet", x)
        try:
            pkt = decode_packet(x)
        except ValueError:
            logger.exception("Packet decode error")
        else:
            if pkt is not None:
                mf.process_packet(pkt)
    logger.info("Received %s packets in %.3f seconds", n, time.monotonic()-t0)
    mf.after_idle(mf.draw)
    mf.after(50, check_receiver, mf, rvr)

class MainFrame(tk.Frame):
    def __init__(self, root: tk.Tk) -> None:
        super().__init__(root)
        root.title("E131 Simulator")
        self.canvas = tk.Canvas(self, bg='black')
        self.canvas.grid(sticky='nsew')
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.universes: dict[int, bytes] = {}
        self.dirty: dict[int, bool] = {}
        self.new_uni = False
        self.uny: dict[int, int] = {}  # y index for each universe

    def draw(self) -> None:
        if self.new_uni:
            self._organize_universes()
            self.new_uni = False
            self.dirty = {u: True for u in self.universes}

        for u, dmx in self.universes.items():
            if not self.dirty[u]:
                continue
            self.dirty[u] = False
            tag = f"U{u}"
            self.canvas.delete(tag)
            m = 30
            n = self.uny[u]
            for x in batched(dmx, 3):
                c = make_color(x)
                self.canvas.create_text(m, n, text="\u25CF", # circle
                    fill=c, font=("Arial", 14), anchor='nw', tags=(tag,))
                m += 10

    def process_packet(self, p: ReceivedData) -> None:
        u = p.universe
        if u not in self.universes:
            self.new_uni = True
            logger.info("Added universe %s", u)
            self.universes[u] = p.dmx_data
        elif self.universes[u] != p.dmx_data:
            logger.debug("Data changed %s", u)
            self.universes[u] = p.dmx_data
            self.dirty[u] = True

    def _organize_universes(self) -> None:
        self.canvas.delete("n_uni")
        for u in self.universes:
            tag = f"U{u}"
            self.canvas.delete(tag)
        for i, u in enumerate(sorted(self.universes)):
            n = i * 30
            self.canvas.create_text(1, n, text=str(u), fill='white',
                font=("Arial", 14), anchor='nw', tags=('n_uni',))
            self.uny[u] = n

if __name__ == "__main__":
    main()
