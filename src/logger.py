import logging
import sys


def get_logger(name: str = "aihot_mcp") -> logging.Logger:
    """Return a logger that writes to stderr with ISO 8601 timestamps.

    Guards against duplicate handlers so calling this function multiple times
    with the same *name* does not attach additional StreamHandlers.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter(
                fmt="[%(asctime)s] [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
    return logger
