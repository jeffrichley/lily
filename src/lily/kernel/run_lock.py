"""Run-scoped file lock. Held only during manifest write. No nested locks."""

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from filelock import FileLock

from lily.kernel.paths import get_lock_path


@contextmanager
def run_lock(run_root: Path) -> Generator:
    """Acquire run-scoped file lock (.lock). Use only for manifest writes.

    Never acquire any other lock while holding the run lock.

    Args:
        run_root: Run directory root (lock file is .lock under it).

    Yields:
        None; lock is held for the context body.
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
