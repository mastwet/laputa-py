"""Atomic file write operations.

Translated from agent-diva-laputa/src/atomic.rs
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def atomic_write(path: Path, data: bytes) -> None:
    """Write data to file atomically using temp file + rename.

    This ensures that either the entire write succeeds, or the original
    file is preserved (no partial writes).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file first
    fd, tmp_path = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    try:
        os.write(fd, data)
        os.fsync(fd)
        os.close(fd)
        # Atomic rename
        os.replace(tmp_path, path)
    except Exception:
        # Clean up temp file on failure
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def atomic_write_json(path: Path, obj: Any) -> None:
    """Write a JSON-serializable object to file atomically."""
    data = json.dumps(obj, indent=2, ensure_ascii=False, default=str)
    atomic_write(path, data.encode("utf-8"))
