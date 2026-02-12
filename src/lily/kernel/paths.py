"""Paths for Layer 0 run store. .iris is the kernel root."""

from pathlib import Path

# Kernel owns everything under .iris/
IRIS_DIR = ".iris"
RUNS_DIR = "runs"
MANIFEST_FILENAME = "run_manifest.json"
RUN_STATE_FILENAME = "run_state.json"
LOCK_FILENAME = ".lock"

# Subdirs under each run
ARTIFACTS_DIR = "artifacts"
LOGS_DIR = "logs"
TMP_DIR = "tmp"


def get_iris_root(workspace_root: Path) -> Path:
    """Return path to .iris (kernel root) under workspace.

    Args:
        workspace_root: Workspace root path.

    Returns:
        Path to .iris directory.
    """
    return workspace_root / IRIS_DIR


def get_runs_root(workspace_root: Path) -> Path:
    """Return path to .iris/runs.

    Args:
        workspace_root: Workspace root path.

    Returns:
        Path to .iris/runs directory.
    """
    return get_iris_root(workspace_root) / RUNS_DIR


def get_run_root(workspace_root: Path, run_id: str) -> Path:
    """Return path to .iris/runs/<run_id>/ (run directory).

    Args:
        workspace_root: Workspace root path.
        run_id: Run identifier.

    Returns:
        Path to run directory.
    """
    return get_runs_root(workspace_root) / run_id


def get_lock_path(run_root: Path) -> Path:
    """Return path to run-scoped lock file: run_root/.lock.

    Args:
        run_root: Run directory path.

    Returns:
        Path to .lock file.
    """
    return run_root / LOCK_FILENAME


def get_manifest_path(run_root: Path) -> Path:
    """Return path to run_manifest.json.

    Args:
        run_root: Run directory path.

    Returns:
        Path to run_manifest.json.
    """
    return run_root / MANIFEST_FILENAME


def get_run_state_path(run_root: Path) -> Path:
    """Return path to run_state.json.

    Args:
        run_root: Run directory path.

    Returns:
        Path to run_state.json.
    """
    return run_root / RUN_STATE_FILENAME


INDEX_FILENAME = "index.sqlite"


def get_index_path(workspace_root: Path) -> Path:
    """Return path to global artifact index: .iris/index.sqlite.

    Args:
        workspace_root: Workspace root path.

    Returns:
        Path to index.sqlite.
    """
    return get_iris_root(workspace_root) / INDEX_FILENAME


def resolve_artifact_path(run_root: Path, rel_path: str) -> Path:
    """Resolve rel_path under run_root; ValueError if path escapes run root.

    Args:
        run_root: Run directory (resolved).
        rel_path: Relative path under run root.

    Returns:
        Resolved absolute path under run root.

    Raises:
        ValueError: If resolved path escapes run root.
    """
    run_root = run_root.resolve()
    resolved = (run_root / rel_path).resolve()
    try:
        resolved.relative_to(run_root)
    except ValueError:
        raise ValueError(
            f"Artifact path escapes run root: {rel_path!r} -> {resolved!s}"
        ) from None
    return resolved
