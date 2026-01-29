"""Logging configuration for Arakis.

Provides structured logging with configurable levels and formatters
for tracking failures, warnings, and operational events throughout
the systematic review pipeline.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

# Create the main logger for the arakis package
logger = logging.getLogger("arakis")


def setup_logging(
    level: int | str = logging.INFO,
    log_file: str | None = None,
    format_style: str = "standard",
) -> logging.Logger:
    """
    Configure logging for the arakis package.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path to write logs to
        format_style: "standard" for human-readable, "json" for structured

    Returns:
        Configured logger instance
    """
    # Convert string level to int if needed
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create formatter
    if format_style == "json":
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"module": "%(module)s", "message": "%(message)s"}'
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a child logger for a specific module.

    Args:
        name: Module name (e.g., "query_generator", "screener")

    Returns:
        Logger instance for the module
    """
    return logging.getLogger(f"arakis.{name}")


def log_failure(
    logger: logging.Logger,
    operation: str,
    error: Exception | str,
    context: dict[str, Any] | None = None,
    level: int = logging.ERROR,
) -> None:
    """
    Log a failure with structured context.

    Args:
        logger: Logger instance to use
        operation: Name of the operation that failed
        error: Exception or error message
        context: Additional context about the failure
        level: Logging level (default: ERROR)
    """
    error_msg = str(error)
    error_type = type(error).__name__ if isinstance(error, Exception) else "Error"

    msg_parts = [f"{operation} failed: [{error_type}] {error_msg}"]

    if context:
        context_str = ", ".join(f"{k}={v}" for k, v in context.items())
        msg_parts.append(f"Context: {context_str}")

    logger.log(level, " | ".join(msg_parts))


def log_warning(
    logger: logging.Logger,
    operation: str,
    message: str,
    context: dict[str, Any] | None = None,
) -> None:
    """
    Log a warning with structured context.

    Args:
        logger: Logger instance to use
        operation: Name of the operation
        message: Warning message
        context: Additional context
    """
    msg_parts = [f"{operation}: {message}"]

    if context:
        context_str = ", ".join(f"{k}={v}" for k, v in context.items())
        msg_parts.append(f"Context: {context_str}")

    logger.warning(" | ".join(msg_parts))


# Initialize default logging (can be reconfigured by CLI or settings)
setup_logging(level=logging.WARNING)
