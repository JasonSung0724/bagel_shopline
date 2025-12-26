"""
Retry utilities for handling transient failures.
"""
import time
import functools
from typing import Callable, Tuple, Type, Optional, Any
from loguru import logger


def retry_with_backoff(
    max_retries: int = 3,
    backoff_factor: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
) -> Callable:
    """
    Decorator that retries a function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for delay between retries
        exceptions: Tuple of exception types to catch and retry
        on_retry: Optional callback function called on each retry with (exception, attempt)

    Returns:
        Decorated function

    Example:
        @retry_with_backoff(max_retries=3, exceptions=(requests.RequestException,))
        def fetch_data():
            return requests.get(url)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        delay = backoff_factor * (2 ** attempt)
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )

                        if on_retry:
                            on_retry(e, attempt + 1)

                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_retries + 1} attempts failed for {func.__name__}: {e}"
                        )

            raise last_exception

        return wrapper
    return decorator


class RetryContext:
    """
    Context manager for retry logic without decorator.

    Example:
        with RetryContext(max_retries=3) as retry:
            while retry.should_continue():
                try:
                    result = do_something()
                    break
                except SomeException as e:
                    retry.handle_exception(e)
    """

    def __init__(
        self,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
        exceptions: Tuple[Type[Exception], ...] = (Exception,)
    ):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.exceptions = exceptions
        self.attempt = 0
        self.last_exception = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def should_continue(self) -> bool:
        """Check if we should continue retrying."""
        return self.attempt <= self.max_retries

    def handle_exception(self, exception: Exception) -> None:
        """Handle an exception and prepare for next retry."""
        self.last_exception = exception

        if not isinstance(exception, self.exceptions):
            raise exception

        if self.attempt < self.max_retries:
            delay = self.backoff_factor * (2 ** self.attempt)
            logger.warning(
                f"Attempt {self.attempt + 1}/{self.max_retries + 1} failed: {exception}. "
                f"Retrying in {delay:.1f}s..."
            )
            time.sleep(delay)
            self.attempt += 1
        else:
            logger.error(f"All {self.max_retries + 1} attempts failed: {exception}")
            raise exception
