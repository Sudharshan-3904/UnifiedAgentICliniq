import logging
import sys
import os
from ..config.settings import settings

def setup_logger(name: str = "agent_logger"):
    if not os.path.exists(settings.LOG_DIR):
        os.makedirs(settings.LOG_DIR)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        # Console Handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        # File Handler
        fh = logging.FileHandler(os.path.join(settings.LOG_DIR, "agent.log"))
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger

logger = setup_logger()
