from __future__ import annotations

import atexit
import os
import signal
from concurrent.futures.process import ProcessPoolExecutor
from typing import Any, Optional

PROCESS_POOL_MAX_WORKERS = None

_process_pool: Optional[ProcessPoolExecutor] = None


def shutdown_process_pool() -> None:
    global _process_pool
    try:
        if _process_pool is not None:
            _process_pool.shutdown(True)
            _process_pool = None
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException:  # NOSONAR
        pass


def _terminate(*args: Any, **kwargs: Any) -> None:
    shutdown_process_pool()


# we need this, because ProcessPoolExecutor is not correctly initialized if asyncio is reading from stdin
def get_process_pool() -> ProcessPoolExecutor:
    global _process_pool
    if _process_pool is None:
        _process_pool = ProcessPoolExecutor(
            max_workers=(
                int(s)
                if (s := os.environ.get("ROBOT_PROCESS_POOL_MAX_WORKERS", None)) and s.isnumeric()
                else PROCESS_POOL_MAX_WORKERS
            ),
            initializer=_init_pool,
        )
        atexit.register(_terminate)

        try:
            _process_pool.submit(_dummy_first_run_pool).result(5)
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException:
            pass

    return _process_pool


def _init_pool() -> None:
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def _dummy_first_run_pool() -> None:
    """Dummy function to initialize the ProcessPoolExecutor"""
    pass
