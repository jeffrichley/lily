"""Run directory creation. L0: .iris/runs/<run_id>/ with artifacts/, logs/, tmp/."""

from pathlib import Path

from lily.kernel.paths import (
    ARTIFACTS_DIR,
    LOGS_DIR,
    TMP_DIR,
    get_run_root,
)


def create_run_directory(workspace_root: Path, run_id: str) -> Path:
    """Create run directory and subdirs. Kernel owns everything under it.

    Layout: .iris/runs/<run_id>/{artifacts/, logs/, tmp/}. .lock on lock acquire.

    Args:
        workspace_root: Workspace root (e.g. project root).
        run_id: Run identifier.

    Returns:
        Path to the created run root directory.
    """
    run_root = get_run_root(workspace_root, run_id)
    run_root.mkdir(parents=True, exist_ok=True)
    (run_root / ARTIFACTS_DIR).mkdir(exist_ok=True)
    (run_root / LOGS_DIR).mkdir(exist_ok=True)
    (run_root / TMP_DIR).mkdir(exist_ok=True)
    return run_root
