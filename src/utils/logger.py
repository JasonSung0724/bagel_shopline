"""
Unified logging configuration for the application.
"""

import sys
from loguru import logger
from typing import Optional


def setup_logger(log_file: str = "logs/app.log", level: str = "DEBUG", rotation: str = "100 MB", retention: str = "14 days", compression: str = "zip") -> None:
    """
    Configure the application logger with console and file handlers.

    Args:
        log_file: Path to the log file
        level: Minimum log level for file output
        rotation: When to rotate the log file (e.g., "100 MB", "1 day")
        retention: How long to keep old log files
        compression: Compression format for rotated files
    """
    # Remove default handler
    logger.remove()

    # Console handler - INFO level with colors
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
    )

    # File handler - configurable level
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {function}:{line} - {message}",
        level=level,
        rotation=rotation,
        retention=retention,
        compression=compression,
        encoding="utf-8",
    )


def get_logger(name: Optional[str] = None):
    """
    Get a logger instance.

    Args:
        name: Optional name for the logger context

    Returns:
        Logger instance
    """
    if name:
        return logger.bind(name=name)
    return logger
