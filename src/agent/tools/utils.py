"""Shared utilities for agent tools."""

import functools
import structlog
from typing import Callable, TypeVar

logger = structlog.get_logger(__name__)

T = TypeVar('T')


def tool_error_handler(operation_name: str):
    """Decorator for consistent tool error handling.

    Args:
        operation_name: Human-readable name of the operation for logging

    Usage:
        @tool_error_handler("file read")
        async def my_tool(...):
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> str:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"{operation_name} failed",
                    error=str(e),
                    exc_info=True
                )
                return f"ERROR: {operation_name} failed - {str(e)}"
        return wrapper
    return decorator
