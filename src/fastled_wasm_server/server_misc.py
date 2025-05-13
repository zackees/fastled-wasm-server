import os
import threading
import time
import warnings

import psutil  # type: ignore

_MEMORY_CHECK_INTERVAL = 0.1  # Check every 100ms
_MEMORY_EXCEEDED_EXIT_CODE = 137  # Standard OOM kill code


def start_memory_watchdog(memory_limit_mb: int) -> None:
    """Monitor memory usage and kill process if it exceeds limit."""
    if memory_limit_mb <= 0:
        warnings.warn("Memory limit is set at 0, watchdog will not be started.")
        return

    def check_memory() -> None:
        while True:
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            if memory_mb > memory_limit_mb:
                print(
                    f"Memory limit exceeded! Using {memory_mb:.1f}MB > {memory_limit_mb}MB limit"
                )
                os._exit(_MEMORY_EXCEEDED_EXIT_CODE)
            time.sleep(_MEMORY_CHECK_INTERVAL)

    watchdog_thread = threading.Thread(target=check_memory, daemon=True)
    watchdog_thread.start()
