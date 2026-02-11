"""Run directory creation. Layer 0: .iris/runs/<run_id>/ with artifacts/, logs/, tmp/."""

from pathlib import Path

from lily.kernel.paths import (
    get_run_root,
    ARTIFACTS_DIR,
    LOGS_DIR,
    TMP_DIR,
)


def create_run_directory(workspace_root: Path, run_id: str) -> Path:
    """
    Create run directory and subdirs. Kernel owns everything under it.
    Layout: .iris/runs/<run_id>/{artifacts/, logs/, tmp/}
    .lock is created when locking; not a directory.
    """
    run_root = get_run_root(workspace_root, run_id)
    run_root.mkdir(parents=True, exist_ok=True)
    (run_root / ARTIFACTS_DIR).mkdir(exist_ok=True)
    (run_root / LOGS_DIR).mkdir(exist_ok=True)
    (run_root / TMP_DIR).mkdir(exist_ok=True)
    return run_root
