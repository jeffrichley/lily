"""Run-scoped file lock. Held only during manifest write. Never hold another lock while holding this."""

from contextlib import contextmanager
from pathlib import Path

from filelock import FileLock

from lily.kernel.paths import get_lock_path


@contextmanager
def run_lock(run_root: Path):
    """
    Acquire run-scoped file lock (.lock). Use only for manifest writes.
    Lock ordering: never acquire any other lock while holding the run lock.
    """
    lock_path = get_lock_path(run_root)
    # Ensure parent exists (run directory)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    flock = FileLock(str(lock_path))
    flock.acquire()
    try:
        yield
    finally:
        flock.release()
