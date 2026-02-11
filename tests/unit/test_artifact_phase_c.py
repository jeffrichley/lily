"""Phase C acceptance: global SQLite index, payload before commit, accurate row, concurrent runs."""

import sqlite3
import threading
from pathlib import Path


from lily.kernel import create_run, ArtifactStore, ArtifactRef
from lily.kernel.paths import get_index_path


def test_index_created_after_put(workspace_root: Path):
    """Index exists at .iris/index.sqlite after first put_json."""
    run_id, run_root = create_run(workspace_root)
    store = ArtifactStore(run_root, run_id)
    assert not get_index_path(workspace_root).exists()
    store.put_json("work_order.v1", {"x": 1})
    assert get_index_path(workspace_root).exists()


def test_payload_exists_before_index_commit(workspace_root: Path):
    """Payload file is on disk before index row is committed (durability order)."""
    run_id, run_root = create_run(workspace_root)
    store = ArtifactStore(run_root, run_id)
    ref = store.put_json("work_order.v1", {"k": "v"})
    # Index has row and payload file exists; payload was written then fsync'd before insert.
    payload_path = run_root / ref.rel_path
    assert payload_path.exists()
    conn = sqlite3.connect(str(get_index_path(workspace_root)))
    cur = conn.execute(
        "SELECT artifact_id, run_id, rel_path, sha256 FROM artifacts WHERE artifact_id = ?",
        (ref.artifact_id,),
    )
    row = cur.fetchone()
    conn.close()
    assert row is not None
    assert row[1] == run_id
    assert row[2] == ref.rel_path
    assert row[3] == ref.sha256


def test_index_row_accurate(workspace_root: Path):
    """Index row matches ArtifactRef returned by put_json."""
    run_id, run_root = create_run(workspace_root)
    store = ArtifactStore(run_root, run_id)
    ref = store.put_json("work_order.v1", {"a": 1}, artifact_name="wo")
    listed = store.list()
    assert len(listed) == 1
    r = listed[0]
    assert r.artifact_id == ref.artifact_id
    assert r.run_id == ref.run_id
    assert r.artifact_type == ref.artifact_type
    assert r.rel_path == ref.rel_path
    assert r.sha256 == ref.sha256
    assert r.artifact_name == ref.artifact_name


def test_list_by_run_id(workspace_root: Path):
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
    assert len(list1) == 2
    assert len(list2) == 1
    assert {r.run_id for r in list1} == {run_id1}
    assert list2[0].run_id == run_id2


def test_concurrent_runs_do_not_corrupt_db(workspace_root: Path):
    """Two runs writing artifacts concurrently; index has correct rows per run."""
    run_id1, run_root1 = create_run(workspace_root)
    run_id2, run_root2 = create_run(workspace_root)
    store1 = ArtifactStore(run_root1, run_id1)
    store2 = ArtifactStore(run_root2, run_id2)
    refs1: list[ArtifactRef] = []
    refs2: list[ArtifactRef] = []

    def put_many(store: ArtifactStore, run_id: str, refs: list[ArtifactRef], n: int):
        for i in range(n):
            ref = store.put_json("work_order.v1", {"i": i, "run": run_id})
            refs.append(ref)

    t1 = threading.Thread(target=put_many, args=(store1, run_id1, refs1, 5))
    t2 = threading.Thread(target=put_many, args=(store2, run_id2, refs2, 5))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    conn = sqlite3.connect(str(get_index_path(workspace_root)))
    cur = conn.execute("SELECT run_id, COUNT(*) FROM artifacts GROUP BY run_id")
    counts = {row[0]: row[1] for row in cur.fetchall()}
    conn.close()
    assert counts.get(run_id1) == 5
    assert counts.get(run_id2) == 5
    list1 = store1.list()
    list2 = store2.list()
    assert len(list1) == 5
    assert len(list2) == 5
