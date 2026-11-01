import os
import threading
import logging
import time
import signal
from collections.abc import Callable
from typing import Self

from .sending.sender_udp import SenderUDP
from . universe import Universe
from . utils import sigterm_handler

logger = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)
del logging

SEND_OUT_INTERVAL = 0.1
UNIVER_INTERVAL = 5

THREAD_NAME = 'PACN sender thread'

class SenderThreadException(Exception):
    pass

class Multiverse:
    def __init__(self, *, callback: Callable[[float,], None] | None = None,
            fps: int = 30, handle_sigterm=True) -> None:
        """An object to manage multiple universes.
        The Universes can be updated at a rate given by fps (frames per second).
        callback: a Callable taking one float, the current time.  If this
            parameter is set, the Multiverse will call it at the frame rate.
        fps: frames per second.  The default is 30. PACN has been tested at 50.
        handle_sigterm: blanks all the lights in all the Universes on
            exit.  Defaults to True.  If set to False, the light strings remain 
            in their last state when the Multiverse exits.  The effect that
            results is hardware-dependent.
        """ 
        self.callback = callback
        self.fps = fps
        self.handle_sigterm = handle_sigterm
        self._universes: dict[int, Universe] = {}
        self.socket = SenderUDP()

        self._enabled = False
        self._stopping = False
        self._sender_thread_exception: Exception|None = None
        self._thread = threading.Thread(target=self.loop, name=THREAD_NAME)
        self.mv_lock = threading.RLock()
        self.blocker = threading.Event()

    def __enter__(self) -> Self:
        if self.handle_sigterm:
            signal.signal(signal.SIGTERM, sigterm_handler)

        self.start()
        return self

    def __exit__(self, *_x) -> None:
        self.stop()

    def wait_for_kb(self) -> None:
        if not self._thread.is_alive():
            raise ValueError("Do not call wait_for_kb unless running")
        self.blocker.clear()
        self.blocker.wait()  # Ctrl-C will get through this block

    def universe(self, n: int) -> Universe:
        return self._universes[n]

    def add_universe(self, u: Universe) -> None:
        with self.mv_lock:
            logger.info("Added universe %s", u.n)
            self._universes[u.n] = u

    def remove_universe(self, u: Universe) -> None:
        with self.mv_lock:
            u = self._universes.pop(u.n)
            logger.info("Removed universe %s", u.n)
            for _ in range(3):
                self.send_out(u, time.time())
                time.sleep(0.005)

    # Context: timing thread
    def periodic_callback(self, current_time: float) -> None:
        pass

    # Context: timing thread
    def _periodic_callback(self, current_time: float) -> None:
        self.periodic_callback(current_time)
        self.check_outputs(current_time)

    # Context: timing thread
    def check_outputs(self, t: float) -> None:
        def check_one(u: Universe) -> bool:
            if u.dirty:
                return True
            return t - u.t_last_sent > SEND_OUT_INTERVAL
        def is_shutdown_complete() -> bool:
            return all(u.shutdown_count > 2 for u in self._universes.values())

        with self.mv_lock:
            for u in self._universes.values():
                if check_one(u):
                    # Mark clean before sending; if another thread
                    # makes it dirty before sending is complete, then
                    # it will be re-sent at the next update tick
                    u.transmitted()
                    self.send_out(u, t)
                if self._stopping and is_shutdown_complete():
                    self._enabled = False

    # Context: timing thread
    def send_out(self, u: Universe, t: float) -> None:
        logger.debug("Sending %s @%s", u.n, t)
        with self.mv_lock:
            self.socket.send(u.packet_data, u.ip)
            u.t_last_sent = t

    # Context: main
    def start(self) -> None:
        self._thread.start()

    # This is the timing thread itself
    def loop(self) -> None:
        logger.info('Started timing thread %s', THREAD_NAME)
        try:
            self._enabled = True
            while self._enabled:
                time_stamp = time.time()
                try:
                    if self.callback is not None:
                        self.callback(time_stamp)
                    self._periodic_callback(time_stamp)
                except Exception as ex:
                    self._sender_thread_exception = ex
                    logger.exception("Timing thread exception %s", 
                        self._sender_thread_exception)
                    os.kill(os.getpid(), signal.SIGTERM)
                time_to_sleep = (1.0 / self.fps) - (time.time() - time_stamp)
                time.sleep(max(time_to_sleep, 0.0))
        finally:
            self.socket.close()
            logger.info('Stopped %s', THREAD_NAME)
            self._enabled = False
            self.blocker.set()

    # Context: main
    def stop(self) -> None:
        """
        Stops the transmission thread, which
        closes the socket.  This function waits until
        the timing thread exits, which takes 3-4 frames.
        Do not reuse the socket after calling stop.
        """
        if not self._stopping:
            with self.mv_lock:
                for u in self._universes.values():
                    u.shutdown()
                self._stopping = True
            self._thread.join()
        if self._sender_thread_exception is not None:
            raise SenderThreadException from self._sender_thread_exception
