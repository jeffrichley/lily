"""Create run and resume. Phase A: run identity + directory + manifest + lock. No SQLite, no artifact store."""

from pathlib import Path
from typing import NamedTuple

from lily.kernel.run_id import generate_run_id
from lily.kernel.paths import get_run_root
from lily.kernel.run_directory import create_run_directory
from lily.kernel.manifest import (
    RunManifest,
    WorkOrderRef,
    create_initial_manifest,
    read_manifest,
    write_manifest_atomic,
)
from lily.kernel.run_lock import run_lock
from lily.kernel.artifact_store import ArtifactStore

# Kernel version for manifest (single source)
KERNEL_VERSION = "0.1.0"


class RunInfo(NamedTuple):
    """Result of creating a run (CLI / service)."""

    run_id: str
    run_root: Path
    work_order_ref: WorkOrderRef | None


def create_run(
    workspace_root: Path,
    work_order_ref: WorkOrderRef | None = None,
    workspace_snapshot: dict | None = None,
) -> tuple[str, Path]:
    """
    Create a new run: generate run_id, create directory, write initial manifest atomically under run lock.
    Returns (run_id, run_root). No artifact store, no SQLite.
    """
    run_id = generate_run_id()
    run_root = create_run_directory(workspace_root, run_id)
    manifest = create_initial_manifest(
        run_id=run_id,
        kernel_version=KERNEL_VERSION,
        work_order_ref=work_order_ref,
        workspace_snapshot=workspace_snapshot,
    )
    with run_lock(run_root):
        write_manifest_atomic(run_root, manifest)
    return run_id, run_root


def resume_run(workspace_root: Path, run_id: str) -> tuple[Path, RunManifest]:
    """
    Open existing run for resume: resolve run root, read manifest. No artifact store.
    Returns (run_root, manifest). Raises if run directory or manifest missing.
    """
    run_root = get_run_root(workspace_root, run_id)
    if not run_root.is_dir():
        raise FileNotFoundError(f"Run directory not found: {run_root}")
    manifest = read_manifest(run_root)
    return run_root, manifest


def create_run_with_optional_work_order(
    workspace_root: Path,
    work_order_path: Path | None = None,
) -> RunInfo:
    """
    Create a new run; optionally attach a work order file as a file artifact.
    Returns RunInfo (run_id, run_root, work_order_ref). Used by CLI.
    """
    if work_order_path is None:
        run_id, run_root = create_run(workspace_root)
        return RunInfo(run_id=run_id, run_root=run_root, work_order_ref=None)
    run_id = generate_run_id()
    run_root = create_run_directory(workspace_root, run_id)
    store = ArtifactStore(run_root, run_id)
    ref = store.put_file("work_order", work_order_path, artifact_name="work_order")
    work_order_ref = WorkOrderRef(run_id=ref.run_id, artifact_id=ref.artifact_id)
    manifest = create_initial_manifest(
        run_id=run_id,
        kernel_version=KERNEL_VERSION,
        work_order_ref=work_order_ref,
    )
    with run_lock(run_root):
        write_manifest_atomic(run_root, manifest)
    return RunInfo(run_id=run_id, run_root=run_root, work_order_ref=work_order_ref)
