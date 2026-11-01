import logging

STANDARD_FORMATTER = logging.Formatter('%(levelname)s: '
                                       '%(filename)s@%(lineno)d %(message)s')
TIMESTAMPED_FORMATTER = logging.Formatter('%(levelname)s: %(filename)s'
                                          '@%(lineno)d %(asctime)s %(message)s')

def stream_handler() -> logging.StreamHandler:
    fmt = STANDARD_FORMATTER
    h = logging.StreamHandler()
    h.setFormatter(fmt)
    return h

logger: logging.Logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(stream_handler())
