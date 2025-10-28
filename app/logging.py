import logging

# Removed: queue, QueueListener, RotatingFileHandler, ProcessorFormatter
from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from pythonjsonlogger.json import JsonFormatter

from app.config import IS_DEBUG

logger = logging.getLogger(__name__)


def setup_logging():
    if not IS_DEBUG:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.DEBUG)

    log_handler = logging.StreamHandler()
    formatter = JsonFormatter(
        '%(asctime)s %(levelname)s %(name)s %(message)s %(correlation_id)s'
    )
    log_handler.setFormatter(formatter)

    logger.addHandler(log_handler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info('Application is starting up.')
    yield
    logger.info('Application is shutting down.')
