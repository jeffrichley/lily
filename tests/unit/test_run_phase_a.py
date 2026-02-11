"""Phase A acceptance: create run, atomic manifest, run lock, resume. No SQLite, no artifact store."""

import json
import threading
from pathlib import Path

import pytest

from lily.kernel import (
    create_run,
    resume_run,
    read_manifest,
    get_run_root,
    get_manifest_path,
    RunStatus,
)
from lily.kernel.paths import (
    IRIS_DIR,
    RUNS_DIR,
    ARTIFACTS_DIR,
    LOGS_DIR,
    TMP_DIR,
)
from lily.kernel.run_id import generate_run_id
from lily.kernel.run_directory import create_run_directory
from lily.kernel.run_lock import run_lock
from lily.kernel.manifest import write_manifest_atomic, create_initial_manifest


def test_generate_run_id():
    """RunId is uuid4 string."""
    r1 = generate_run_id()
    r2 = generate_run_id()
    assert isinstance(r1, str)
    assert len(r1) == 36  # UUID format
    assert r1 != r2


def test_create_run(workspace_root: Path):
    """Can create run: directory and manifest exist."""
    run_id, run_root = create_run(workspace_root)
    assert run_id
    assert run_root.is_dir()
    assert run_root == workspace_root / IRIS_DIR / RUNS_DIR / run_id
    assert (run_root / "run_manifest.json").exists()
    assert (run_root / ARTIFACTS_DIR).is_dir()
    assert (run_root / LOGS_DIR).is_dir()
    assert (run_root / TMP_DIR).is_dir()


def test_manifest_is_atomic(workspace_root: Path):
    """Manifest is valid JSON and has required fields; written atomically (no partial file)."""
    run_id, run_root = create_run(workspace_root)
    path = get_manifest_path(run_root)
    content = path.read_text(encoding="utf-8")
    data = json.loads(content)
    assert data["run_id"] == run_id
    assert data["status"] == RunStatus.CREATED
    assert "created_at" in data
    assert "updated_at" in data
    assert data["kernel_version"]


def test_resume_works(workspace_root: Path):
    """Resume loads run root and manifest."""
    run_id, run_root = create_run(workspace_root)
    loaded_root, manifest = resume_run(workspace_root, run_id)
    assert loaded_root == run_root
    assert manifest.run_id == run_id
    assert manifest.status == RunStatus.CREATED


def test_resume_missing_run_raises(workspace_root: Path):
    """Resume with missing run_id raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        resume_run(workspace_root, "00000000-0000-0000-0000-000000000000")


def test_run_lock_serializes_manifest_writes(workspace_root: Path):
    """Run lock: two threads writing manifest do not corrupt; lock serializes writes."""
    run_id = generate_run_id()
    create_run_directory(workspace_root, run_id)
    run_root = get_run_root(workspace_root, run_id)
    results: list[Exception | None] = []

    def write_manifest(step: int):
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


def test_no_sqlite_no_artifact_store(workspace_root: Path):
    """Phase A: no .iris/index.sqlite; no artifact store usage."""
    create_run(workspace_root)
    iris = workspace_root / IRIS_DIR
    assert iris.is_dir()
    index_sqlite = iris / "index.sqlite"
    assert not index_sqlite.exists()
