"""Phase C: global SQLite index, payload before commit, concurrent runs."""

import threading
from pathlib import Path

from lily.kernel import ArtifactRef, ArtifactStore, PutArtifactOptions, create_run


def test_index_created_after_put(workspace_root: Path) -> None:
    """After first put_json, list() returns the new artifact (index is usable)."""
    run_id, run_root = create_run(workspace_root)
    store = ArtifactStore(run_root, run_id)
    assert len(store.list()) == 0, "new store should list no artifacts before first put"
    ref = store.put_json("work_order.v1", {"x": 1})
    listed = store.list()
    assert len(listed) == 1, "after one put, list() should return one ref"
    assert listed[0].artifact_id == ref.artifact_id, "listed ref should match put ref"
    assert store.get(ref) == {"x": 1}, "get(ref) should return stored payload"


def test_payload_exists_before_index_commit(workspace_root: Path) -> None:
    """After put_json, payload exists and ref is listable/gettable (durability)."""
    run_id, run_root = create_run(workspace_root)
    store = ArtifactStore(run_root, run_id)
    ref = store.put_json("work_order.v1", {"k": "v"})
    payload_path = run_root / ref.rel_path
    assert payload_path.exists(), "payload file should exist after put"
    listed = store.list()
    assert any(r.artifact_id == ref.artifact_id for r in listed), (
        "ref should appear in list()"
    )
    assert store.get(ref) == {"k": "v"}, "get(ref) should return stored payload"


def test_index_row_accurate(workspace_root: Path) -> None:
    """Index row matches ArtifactRef returned by put_json."""
    run_id, run_root = create_run(workspace_root)
    store = ArtifactStore(run_root, run_id)
    ref = store.put_json(
        "work_order.v1", {"a": 1}, options=PutArtifactOptions(artifact_name="wo")
    )
    listed = store.list()
    assert len(listed) == 1, "list() should return one ref"
    r = listed[0]
    assert r.artifact_id == ref.artifact_id, "list row artifact_id should match put ref"
    assert r.run_id == ref.run_id, "list row run_id should match"
    assert r.artifact_type == ref.artifact_type, "list row artifact_type should match"
    assert r.rel_path == ref.rel_path, "list row rel_path should match"
    assert r.sha256 == ref.sha256, "list row sha256 should match"
    assert r.artifact_name == ref.artifact_name, "list row artifact_name should match"


def test_list_by_run_id(workspace_root: Path) -> None:
    """list() returns artifacts for the run; multiple runs do not mix."""
    run_id1, run_root1 = create_run(workspace_root)
    run_id2, run_root2 = create_run(workspace_root)
    store1 = ArtifactStore(run_root1, run_id1)
    store2 = ArtifactStore(run_root2, run_id2)
    store1.put_json("work_order.v1", {"r": 1})
    store1.put_json("work_order.v1", {"r": 2})
    store2.put_json("work_order.v1", {"r": 3})
    list1 = store1.list()
    list2 = store2.list()
    assert len(list1) == 2, "store1 should list two artifacts"
    assert len(list2) == 1, "store2 should list one artifact"
    assert {r.run_id for r in list1} == {run_id1}, "list1 should only contain run_id1"
    assert list2[0].run_id == run_id2, "list2 should contain run_id2"


def test_concurrent_runs_do_not_corrupt_db(workspace_root: Path) -> None:
    """Two runs writing artifacts concurrently; index has correct rows per run."""
    run_id1, run_root1 = create_run(workspace_root)
    run_id2, run_root2 = create_run(workspace_root)
    store1 = ArtifactStore(run_root1, run_id1)
    store2 = ArtifactStore(run_root2, run_id2)
    refs1: list[ArtifactRef] = []
    refs2: list[ArtifactRef] = []

    def put_many(
        store: ArtifactStore, run_id: str, refs: list[ArtifactRef], n: int
    ) -> None:
        for i in range(n):
            ref = store.put_json("work_order.v1", {"i": i, "run": run_id})
            refs.append(ref)

    t1 = threading.Thread(target=put_many, args=(store1, run_id1, refs1, 5))
    t2 = threading.Thread(target=put_many, args=(store2, run_id2, refs2, 5))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    list1 = store1.list()
    list2 = store2.list()
    assert len(list1) == 5, "store1 should list 5 artifacts after concurrent puts"
    assert len(list2) == 5, "store2 should list 5 artifacts after concurrent puts"
    assert {r.run_id for r in list1} == {run_id1}
    assert {r.run_id for r in list2} == {run_id2}
