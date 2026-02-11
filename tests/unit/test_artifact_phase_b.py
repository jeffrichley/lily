"""Phase B acceptance: put/get JSON, path confinement, no overwrite, hash correct. No SQLite."""

from pathlib import Path

import pytest

from lily.kernel import create_run, ArtifactStore, resolve_artifact_path


def test_put_get_json_artifact(workspace_root: Path):
    """Can put and get a JSON artifact."""
    run_id, run_root = create_run(workspace_root)
    store = ArtifactStore(run_root, run_id)
    payload = {"type": "work_order", "version": 1, "steps": []}
    ref = store.put_json("work_order.v1", payload, artifact_name="work_order")
    assert ref.artifact_id
    assert ref.run_id == run_id
    assert ref.storage_kind == "json"
    assert ref.rel_path.endswith("payload.json")
    loaded = store.get(ref)
    assert loaded == payload


def test_cannot_escape_run_root(workspace_root: Path):
    """Path confinement: resolving a path that escapes run root raises."""
    run_id, run_root = create_run(workspace_root)
    run_root = run_root.resolve()
    with pytest.raises(ValueError, match="escapes run root"):
        resolve_artifact_path(run_root, "../../../etc/passwd")
    with pytest.raises(ValueError, match="escapes run root"):
        resolve_artifact_path(run_root, "..")  # parent of run root escapes


def test_get_rejects_wrong_run_id(workspace_root: Path):
    """get() rejects ArtifactRef with different run_id."""
    run_id, run_root = create_run(workspace_root)
    store = ArtifactStore(run_root, run_id)
    ref = store.put_json("work_order.v1", {"x": 1})
    other_run_id = "00000000-0000-0000-0000-000000000000"
    bad_ref = ref.model_copy(update={"run_id": other_run_id})
    with pytest.raises(ValueError, match="does not match store run_id"):
        store.get(bad_ref)


def test_overwrite_impossible(workspace_root: Path):
    """Each put_json creates a new artifact_id directory; no overwrite."""
    run_id, run_root = create_run(workspace_root)
    store = ArtifactStore(run_root, run_id)
    ref1 = store.put_json("work_order.v1", {"v": 1})
    ref2 = store.put_json("work_order.v1", {"v": 2})
    assert ref1.artifact_id != ref2.artifact_id
    assert store.get(ref1) == {"v": 1}
    assert store.get(ref2) == {"v": 2}


def test_hash_correct(workspace_root: Path):
    """sha256 in ArtifactRef matches stored file."""
    run_id, run_root = create_run(workspace_root)
    store = ArtifactStore(run_root, run_id)
    payload = {"same": "content"}
    ref = store.put_json("work_order.v1", payload)
    assert ref.sha256
    assert len(ref.sha256) == 64  # hex digest
    payload_path = run_root / ref.rel_path
    content = payload_path.read_bytes()
    import hashlib

    expected = hashlib.sha256(content).hexdigest()
    assert ref.sha256 == expected


def test_put_text_and_get(workspace_root: Path):
    """put_text stores plain text; get returns str for text artifacts."""
    run_id, run_root = create_run(workspace_root)
    store = ArtifactStore(run_root, run_id)
    text = "plain text content\nline two"
    ref = store.put_text("log.v1", text, artifact_name="log")
    assert ref.storage_kind.value == "text"
    assert ref.rel_path.endswith("payload.txt")
    loaded = store.get(ref)
    assert loaded == text
    assert isinstance(loaded, str)
