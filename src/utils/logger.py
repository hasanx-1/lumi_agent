import logging
import os
from src.utils.config import config

os.makedirs('logs', exist_ok=True)

def setup_logger(name, log_file, level = logging.INFO):
    '''Function to setup logger with a specific log file and level'''

    formatter = logging.Formatter(config.LOGGER_FORMAT)

    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger


app_logger = setup_logger('app_logger',config.APP_LOGGER,logging.INFO)
pipeline_logger = setup_logger('pipeline_logger',config.PIPELINE_LOGGER,logging.INFO)
manager_logger = setup_logger('manager_logger',config.MANAGER_LOGGER,logging.INFO)
