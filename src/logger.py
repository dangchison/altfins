# -*- coding: utf-8 -*-
import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """
    Return a configured logger for the given module name.
    Format: 2026-04-18 13:25:01 [INFO] src.scraper.auth: Login successful
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
