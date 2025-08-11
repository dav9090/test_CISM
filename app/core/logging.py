import logging

from structlog import configure, get_logger
from structlog.processors import JSONRenderer
from structlog.stdlib import LoggerFactory


def init_logging() -> None:
    logging.basicConfig(level=logging.INFO)
    configure(logger_factory=LoggerFactory(), processors=[JSONRenderer()])


logger = get_logger()
