"""
Logging configuration using Loguru.
Logs errors to file, all levels to console.
"""

import sys
from loguru import logger
from .config import paths

try:
    paths.logs_dir.mkdir(exist_ok=True)
except FileExistsError:
    pass

logger.remove()

logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    colorize=True,
)

try:
    # logger.add(
    #     paths.logs_dir / "scraper_{time:YYYY-MM-DD}.log",
    #     level="INFO",
    #     format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    #     rotation="10 MB",
    #     retention="30 days",
    #     compression="zip",
    # )

    logger.add(
        paths.logs_dir / "scraper_{time:YYYY-MM-DD}.log",
        level="WARNING",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
    )

    logger.add(
        paths.logs_dir / "errors_{time:YYYY-MM-DD}.log",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
    )
except OSError:
    logger.warning("Could not set up file logging due to permissions.")

__all__ = ["logger"]
