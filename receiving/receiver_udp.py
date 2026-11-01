import socket
import threading
import queue
import time
import logging
from typing import Self

from .. import utils as UT

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)
del logging

THREAD_NAME = 'PACN receiver thread'

class Receiver:
    def __init__(self, bind_address='', bind_port=UT.DEFAULT_PORT) -> None:
        self.queue:queue.Queue[bytes|None] = queue.Queue()
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((bind_address, bind_port))
        self._thread = threading.Thread(target=self._read_thread, 
                                        name=THREAD_NAME, daemon=True)
        self._run = False

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, *_x) -> None:
        self.stop()

    def get_packet(self, block=True, timeout:float|None=None) -> bytes | None:
        return self.queue.get(block=block, timeout=timeout)

    def start(self) -> None:
        if self._thread.ident is None:
            self._run = True
            self._thread.start()

    def stop(self) -> None:
        self._run = False
        if self._socket:
            self._socket.close()
        self.queue.put(None)

    def _read_thread(self) -> None:
        self._socket.settimeout(0.5)
        while self._run:
            try:
                data = self._socket.recv(2048)
                logger.debug("%s bytes received @ %s", len(data), 
                                time.asctime())
                self.queue.put(data)
            except socket.timeout:
                continue  # Keeps loop responsive to the stop event
            except Exception:
                self.queue.put(None)
                break     # Socket was closed by stop or __exit__


