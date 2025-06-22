import logging
from structlog import get_logger, configure
from structlog.stdlib import LoggerFactory
from structlog.processors import JSONRenderer


def init_logging():
    logging.basicConfig(level=logging.INFO)
    configure(logger_factory=LoggerFactory(), processors=[JSONRenderer()])


logger = get_logger()
