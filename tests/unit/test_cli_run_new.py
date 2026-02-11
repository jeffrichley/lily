"""Unit tests for run creation (create_run_with_optional_work_order). CLI entrypoint coverage optional."""

import json
from pathlib import Path


from lily.kernel import read_manifest, get_manifest_path, RunStatus
from lily.kernel.paths import IRIS_DIR, RUNS_DIR, ARTIFACTS_DIR, LOGS_DIR, TMP_DIR
from lily.kernel.run import create_run_with_optional_work_order, RunInfo


def test_create_run_with_optional_work_order_creates_directory_and_manifest(
    workspace_root: Path,
) -> None:
    """create_run_with_optional_work_order(no work order) creates directory structure and manifest."""
    info = create_run_with_optional_work_order(workspace_root, work_order_path=None)
    assert isinstance(info, RunInfo)
    assert info.run_id
    assert info.run_root.is_dir()
    assert info.work_order_ref is None
    assert info.run_root == workspace_root / IRIS_DIR / RUNS_DIR / info.run_id
    assert (info.run_root / "run_manifest.json").exists()
    assert (info.run_root / ARTIFACTS_DIR).is_dir()
    assert (info.run_root / LOGS_DIR).is_dir()
    assert (info.run_root / TMP_DIR).is_dir()

    manifest_path = get_manifest_path(info.run_root)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["run_id"] == info.run_id
    assert data["status"] == RunStatus.CREATED
    assert "created_at" in data
    assert "updated_at" in data
    assert data["kernel_version"]
    assert data.get("work_order_ref") is None


def test_create_run_with_work_order_sets_ref_and_stores_artifact(
    workspace_root: Path,
) -> None:
    """Providing a work order path populates work_order_ref and stores the artifact under the run."""
    work_order_file = workspace_root / "wo.txt"
    work_order_file.write_text("work order content")

    info = create_run_with_optional_work_order(
        workspace_root, work_order_path=work_order_file
    )
    assert info.work_order_ref is not None
    assert info.work_order_ref.run_id == info.run_id
    assert info.work_order_ref.artifact_id

    manifest = read_manifest(info.run_root)
    assert manifest.work_order_ref is not None
    assert manifest.work_order_ref.artifact_id == info.work_order_ref.artifact_id
    assert manifest.work_order_ref.run_id == info.run_id

    artifact_dir = info.run_root / ARTIFACTS_DIR / info.work_order_ref.artifact_id
    assert artifact_dir.is_dir()
    stored_file = artifact_dir / "wo.txt"
    assert stored_file.exists()
    assert stored_file.read_text() == "work order content"
