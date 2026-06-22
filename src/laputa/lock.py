"""File locking for Laputa governance operations.

Translated from agent-diva-laputa/src/lock.rs
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

from .error import LockTimeout


class LaputaLock:
    """File-based lock with timeout and stale recovery.

    Usage:
        with LaputaLock(path):
            # critical section
            pass
    """

    def __init__(
        self,
        lock_path: Path,
        timeout: float = 5.0,
        stale_after: float = 300.0,
    ):
        self._lock_path = Path(lock_path)
        self._timeout = timeout
        self._stale_after = stale_after
        self._fd: Optional[int] = None

    def acquire(self) -> None:
        """Acquire the lock, waiting up to timeout seconds."""
        start = time.monotonic()
        while True:
            try:
                self._fd = os.open(
                    self._lock_path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o644,
                )
                # Write PID for debugging
                os.write(self._fd, str(os.getpid()).encode())
                return
            except FileExistsError:
                # Lock file exists, check if stale
                if self._is_stale():
                    self._break_stale()
                    continue
                # Check timeout
                elapsed = time.monotonic() - start
                if elapsed >= self._timeout:
                    raise LockTimeout(self._lock_path, self._timeout)
                time.sleep(0.1)

    def release(self) -> None:
        """Release the lock."""
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None
        try:
            os.unlink(self._lock_path)
        except OSError:
            pass

    def _is_stale(self) -> bool:
        """Check if the lock file is older than stale_after seconds."""
        try:
            mtime = os.path.getmtime(self._lock_path)
            return (time.time() - mtime) > self._stale_after
        except OSError:
            return False

    def _break_stale(self) -> None:
        """Remove a stale lock file."""
        try:
            os.unlink(self._lock_path)
        except OSError:
            pass

    def __enter__(self) -> LaputaLock:
        self.acquire()
        return self

    def __exit__(self, *args) -> None:
        self.release()
