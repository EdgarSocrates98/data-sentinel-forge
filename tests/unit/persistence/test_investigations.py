"""Tests for the persistent investigation engine (ds-0081, §2)."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from data_sentinel.persistence.investigations import (
    VALID_TRANSITIONS,
    InvestigationStore,
    State,
)


@pytest.fixture
def store(tmp_path: Path) -> InvestigationStore:
    s = InvestigationStore(tmp_path / "test.db")
    yield s  # type: ignore[misc]
    s.close()


def test_lifecycle_transitions(store: InvestigationStore) -> None:
    store.create("i1", "p")
    store.transition("i1", State.QUEUED)
    store.transition("i1", State.RUNNING)
    store.transition("i1", State.COMPLETED)
    rec = store.get("i1")
    assert rec is not None and rec.state == State.COMPLETED


def test_invalid_transition_rejected(store: InvestigationStore) -> None:
    store.create("i2", "p")
    store.transition("i2", State.RUNNING)
    with pytest.raises(ValueError, match="invalid transition"):
        store.transition("i2", State.CREATED)
    store.transition("i2", State.COMPLETED)
    with pytest.raises(ValueError):
        store.transition("i2", State.RUNNING)


def test_every_transition_has_model() -> None:
    for st in State:
        assert st in VALID_TRANSITIONS


def test_report_persisted(store: InvestigationStore) -> None:
    store.create("i3", "p")
    store.save_report("i3", {"findings": [1, 2], "meta": "x"})
    assert store.get("i3").report == {"findings": [1, 2], "meta": "x"}


def test_restart_recovery_marks_interrupted(tmp_path: Path) -> None:
    db = tmp_path / "r.db"
    s1 = InvestigationStore(db)
    s1.create("live", "p")
    s1.transition("live", State.RUNNING)
    s1.create("done", "p")
    s1.transition("done", State.RUNNING)
    s1.transition("done", State.COMPLETED)
    s1.close()
    # simulate restart — new store instance over same db
    s2 = InvestigationStore(db)
    assert s2.get("live").state == State.INTERRUPTED
    assert s2.get("done").state == State.COMPLETED
    s2.close()


def test_interrupted_resume_explicit(store: InvestigationStore) -> None:
    store.create("i4", "p")
    store.transition("i4", State.RUNNING)
    rec = store.get("i4")
    rec.state = State.INTERRUPTED  # simulate post-crash row
    # force row to INTERRUPTED via new store
    store._conn.execute(
        "UPDATE investigations SET state=? WHERE investigation_id=?",
        (State.INTERRUPTED.value, "i4"))
    store._conn.commit()
    # resume is an explicit QUEUED transition — allowed
    store.transition("i4", State.QUEUED)
    assert store.get("i4").state == State.QUEUED


def test_event_replay_monotonic(store: InvestigationStore) -> None:
    store.create("i5", "p")
    seqs = [store.emit("i5", f"e{n}", {"n": n}) for n in range(5)]
    assert seqs == [1, 2, 3, 4, 5]
    ev = store.events("i5")
    assert [e["seq"] for e in ev] == [1, 2, 3, 4, 5]
    # replay after seq 2
    tail = store.events("i5", after_seq=2)
    assert [e["seq"] for e in tail] == [3, 4, 5]


def test_prune_by_count(store: InvestigationStore) -> None:
    for i in range(5):
        store.create(f"k{i}", "p")
    removed = store.prune(max_investigations=2)
    assert removed == 3
    assert len(store.list_all()) == 2


def test_delete_authorized(store: InvestigationStore) -> None:
    store.create("d1", "p")
    store.emit("d1", "e", {})
    assert store.delete("d1") is True
    assert store.get("d1") is None
    assert store.events("d1") == []


def test_concurrent_writes(tmp_path: Path) -> None:
    """10 threads emit events concurrently — no lost writes (§2.6)."""
    store = InvestigationStore(tmp_path / "c.db")
    store.create("cc", "p")
    errors: list[Exception] = []

    def worker(n: int) -> None:
        try:
            for k in range(10):
                store.emit("cc", f"t{n}-{k}", {"n": n, "k": k})
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(n,))
               for n in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    assert len(store.events("cc")) == 100
    seqs = [e["seq"] for e in store.events("cc")]
    assert sorted(seqs) == list(range(1, 101))
    store.close()


def test_concurrent_create_and_transition(tmp_path: Path) -> None:
    store = InvestigationStore(tmp_path / "cc2.db")
    for i in range(20):
        store.create(f"inv-{i}", "p")

    def work(i: int) -> None:
        store.transition(f"inv-{i}", State.QUEUED)
        store.transition(f"inv-{i}", State.RUNNING)

    ts = [threading.Thread(target=work, args=(i,)) for i in range(20)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert all(store.get(f"inv-{i}").state == State.RUNNING
               for i in range(20))
    store.close()
