import socket
import logging

from .. utils import DEFAULT_PORT

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)
del logging

class SenderUDP:
    # Allow subclasses to have arguments
    def __init__(self, *_x, **_y) -> None:
        self._socket: socket.socket = socket.socket(socket.AF_INET,  # Internet
                                                    socket.SOCK_DGRAM)  # UDP
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def close(self) -> None:
        self._socket.close()

    def send(self, data: bytearray, destination: str, /, **_y) -> None:
        logger.debug("Sending packet %s", data)
        self._send_packet(data, destination)

    def _send_packet(self, data: bytearray, destination: str) -> None:
        try:
            self._socket.sendto(data, (destination, DEFAULT_PORT))
        except OSError as e:
            logger.exception('Failed to send packet', exc_info=e)
            raise
