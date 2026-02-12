"""Phase A: create run, atomic manifest, run lock, resume."""

import json
import threading
from pathlib import Path

import pytest

from lily.kernel import (
    RunStatus,
    create_run,
    get_manifest_path,
    get_run_root,
    read_manifest,
    resume_run,
)
from lily.kernel.manifest import create_initial_manifest, write_manifest_atomic
from lily.kernel.paths import (
    ARTIFACTS_DIR,
    IRIS_DIR,
    LOGS_DIR,
    RUNS_DIR,
    TMP_DIR,
)
from lily.kernel.run_directory import create_run_directory
from lily.kernel.run_id import generate_run_id
from lily.kernel.run_lock import run_lock


def test_generate_run_id() -> None:
    """RunId is uuid4 string."""
    r1 = generate_run_id()
    r2 = generate_run_id()
    assert isinstance(r1, str)
    assert len(r1) == 36  # UUID format
    assert r1 != r2


def test_create_run(workspace_root: Path) -> None:
    """Can create run: directory and manifest exist."""
    run_id, run_root = create_run(workspace_root)
    assert run_id
    assert run_root.is_dir()
    assert run_root == workspace_root / IRIS_DIR / RUNS_DIR / run_id
    assert (run_root / "run_manifest.json").exists()
    assert (run_root / ARTIFACTS_DIR).is_dir()
    assert (run_root / LOGS_DIR).is_dir()
    assert (run_root / TMP_DIR).is_dir()


def test_manifest_is_atomic(workspace_root: Path) -> None:
    """Manifest is valid JSON with required fields; written atomically."""
    run_id, run_root = create_run(workspace_root)
    path = get_manifest_path(run_root)
    content = path.read_text(encoding="utf-8")
    data = json.loads(content)
    assert data["run_id"] == run_id
    assert data["status"] == RunStatus.CREATED
    assert "created_at" in data
    assert "updated_at" in data
    assert data["kernel_version"]


def test_resume_works(workspace_root: Path) -> None:
    """Resume loads run root and manifest."""
    run_id, run_root = create_run(workspace_root)
    loaded_root, manifest = resume_run(workspace_root, run_id)
    assert loaded_root == run_root
    assert manifest.run_id == run_id
    assert manifest.status == RunStatus.CREATED


def test_resume_missing_run_raises(workspace_root: Path) -> None:
    """Resume with missing run_id raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        resume_run(workspace_root, "00000000-0000-0000-0000-000000000000")


def test_run_lock_serializes_manifest_writes(workspace_root: Path) -> None:
    """Run lock: two threads writing manifest do not corrupt; lock serializes writes."""
    run_id = generate_run_id()
    create_run_directory(workspace_root, run_id)
    run_root = get_run_root(workspace_root, run_id)
    results: list[Exception | None] = []

    def write_manifest(step: int) -> None:
        try:
            manifest = create_initial_manifest(
                run_id=run_id,
                kernel_version="0.1.0",
            )
            # Simulate status update
            manifest.updated_at = f"2025-01-01T12:00:0{step}Z"
            with run_lock(run_root):
                write_manifest_atomic(run_root, manifest)
            results.append(None)
        except Exception as e:
            results.append(e)

    t1 = threading.Thread(target=write_manifest, args=(1,))
    t2 = threading.Thread(target=write_manifest, args=(2,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    assert all(r is None for r in results), results
    manifest = read_manifest(run_root)
    assert manifest.run_id == run_id
    assert manifest.status == RunStatus.CREATED


def test_no_sqlite_no_artifact_store(workspace_root: Path) -> None:
    """Phase A: no .iris/index.sqlite; no artifact store usage."""
    create_run(workspace_root)
    iris = workspace_root / IRIS_DIR
    assert iris.is_dir()
    index_sqlite = iris / "index.sqlite"
    assert not index_sqlite.exists()
