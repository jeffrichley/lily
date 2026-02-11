"""Phase D acceptance: put_file + open_path — file artifact, hash correct, path traversal blocked."""

import hashlib
from pathlib import Path

import pytest

from lily.kernel import create_run, ArtifactStore


def test_file_artifact_accessible(workspace_root: Path):
    """File artifact can be stored with put_file and read via open_path."""
    run_id, run_root = create_run(workspace_root)
    store = ArtifactStore(run_root, run_id)
    source = workspace_root / "input.dat"
    source.write_bytes(b"file content here")
    ref = store.put_file("blob.v1", source, artifact_name="input")
    assert ref.storage_kind.value == "file"
    path = store.open_path(ref)
    assert path.exists()
    assert path.read_bytes() == b"file content here"


def test_put_file_copy_default(workspace_root: Path):
    """Default is copy; source file still exists after put_file."""
    run_id, run_root = create_run(workspace_root)
    store = ArtifactStore(run_root, run_id)
    source = workspace_root / "original.txt"
    source.write_text("original")
    ref = store.put_file("blob.v1", source)
    assert source.exists()
    assert source.read_text() == "original"
    assert store.open_path(ref).read_text() == "original"


def test_put_file_move_true(workspace_root: Path):
    """move=True removes source and artifact has content."""
    run_id, run_root = create_run(workspace_root)
    store = ArtifactStore(run_root, run_id)
    source = workspace_root / "to_move.bin"
    source.write_bytes(b"moved content")
    ref = store.put_file("blob.v1", source, move=True)
    assert not source.exists()
    assert store.open_path(ref).read_bytes() == b"moved content"


def test_file_hash_correct(workspace_root: Path):
    """sha256 in ArtifactRef matches stored file for put_file."""
    run_id, run_root = create_run(workspace_root)
    store = ArtifactStore(run_root, run_id)
    source = workspace_root / "data.bin"
    content = b"same content for hash"
    source.write_bytes(content)
    ref = store.put_file("blob.v1", source)
    expected_sha = hashlib.sha256(content).hexdigest()
    assert ref.sha256 == expected_sha
    path = store.open_path(ref)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == ref.sha256


def test_open_path_traversal_blocked(workspace_root: Path):
    """open_path only returns path under run root; path traversal blocked."""
    run_id, run_root = create_run(workspace_root)
    store = ArtifactStore(run_root, run_id)
    source = workspace_root / "safe.txt"
    source.write_text("x")
    ref = store.put_file("blob.v1", source)
    path = store.open_path(ref)
    assert path.resolve().is_relative_to(run_root.resolve())
    # Ref with rel_path that would escape should be rejected by resolve_artifact_path

    bad_ref = ref.model_copy(update={"rel_path": "artifacts/../../run_manifest.json"})
    with pytest.raises(ValueError, match="escapes run root"):
        store.open_path(bad_ref)


def test_open_path_rejects_json_artifact(workspace_root: Path):
    """open_path raises for non-file storage_kind."""
    run_id, run_root = create_run(workspace_root)
    store = ArtifactStore(run_root, run_id)
    ref = store.put_json("work_order.v1", {"x": 1})
    assert ref.storage_kind.value == "json"
    with pytest.raises(ValueError, match="only supports storage_kind=file"):
        store.open_path(ref)
