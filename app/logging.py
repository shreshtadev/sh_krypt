import logging
import os
import sys
from logging.config import dictConfig

from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager

# Define a logger for your application
logger = logging.getLogger('shkrypts')


def setup_logging():
    """Configures logging for the application based on the environment."""
    log_config_dev = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S',
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'default',
                'stream': sys.stdout,
            },
        },
        'root': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
    }

    log_config_prod = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S',
            },
        },
        'handlers': {
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'default',
                'filename': 'app.log',
                'maxBytes': 5000000,  # 5 MB
                'backupCount': 5,
            },
        },
        'root': {
            'level': 'INFO',
            'handlers': ['file'],
        },
    }

    # Use an environment variable to switch between configurations
    if bool(os.getenv('IS_DEBUG', 'True')):
        dictConfig(log_config_prod)
        logger.info('Configured persistent logger.')
    else:
        dictConfig(log_config_dev)
        logger.info('Configured console logger.')


@asynccontextmanager
async def lifespan(app: FastAPI):
    # This block runs at startup
    setup_logging()  # Set up the console or file logger
    logger.info('Application is starting up.')
    yield  # The application will now handle requests
    logger.info('Application is shutting down.')
