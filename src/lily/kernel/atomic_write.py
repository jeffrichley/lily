"""Atomic JSON write with fsync for run directory files. Layer 0."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any


def atomic_write_json_at(
    run_root: Path,
    final_path: Path,
    data: dict[str, Any],
    temp_prefix: str,
) -> None:
    """Write JSON to final_path atomically: temp -> fsync -> rename -> fsync dir.

    Temp file is created in run_root so rename is atomic. On failure, temp is
    removed. Caller must hold run lock if required for the target file.

    Args:
        run_root: Directory containing the final path (and temp file).
        final_path: Destination path for the JSON file.
        data: JSON-serializable dict (e.g. from .to_file_dict()).
        temp_prefix: Prefix for temp filename, e.g. "run_manifest" or "run_state".
    """
    temp_path = run_root / f".{temp_prefix}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp"
    content_bytes = json.dumps(data, indent=2).encode("utf-8")
    try:
        fd = os.open(
            str(temp_path),
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
            0o644,
        )
        try:
            os.write(fd, content_bytes)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(temp_path, final_path)
        try:
            dir_fd = os.open(str(run_root), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            pass  # e.g. Windows: directory fsync best-effort
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
