"""DevRev follow-up board: preview writes nothing, evidence required, no duplicates, honest gaps."""
import pytest

from app.devrev_board import store

SRC = [{"ref": "transcripts/acme_qbr.json", "lines": "40-44", "quote": "We will send the revised SOW by Friday"}]
DRAFT = dict(account="Acme Corp", title="Send revised SOW", sources=SRC, requested_by="irvin")


@pytest.fixture(autouse=True)
def clean():
    store.clear()
    yield


def test_preview_writes_nothing():
    p = store.preview(**DRAFT)
    assert p["duplicate_of"] is None and p["idempotency_key"]
    assert store.list_follow_ups()["total"] == 0


def test_create_then_repeat_is_not_a_duplicate():
    key = store.preview(**DRAFT)["idempotency_key"]
    first = store.create(idempotency_key=key, **DRAFT)
    again = store.create(idempotency_key=key, **DRAFT)
    assert first["created"] and not again["created"]
    assert again["follow_up"]["id"] == first["follow_up"]["id"] == "F001"
    assert again["follow_up"]["repeat_attempts"] == 1
    assert store.list_follow_ups()["total"] == 1
    assert store.preview(**DRAFT)["duplicate_of"] == "F001"


def test_same_task_reworded_spacing_is_same_key():
    a = store.preview(**DRAFT)["idempotency_key"]
    b = store.preview(**{**DRAFT, "title": "  send   REVISED sow "})["idempotency_key"]
    assert a == b


def test_no_evidence_no_follow_up():
    with pytest.raises(ValueError, match="source"):
        store.create(**{**DRAFT, "sources": []})
    with pytest.raises(ValueError, match="source"):
        store.create(**{**DRAFT, "sources": [{"ref": "  "}]})
    assert store.list_follow_ups()["total"] == 0


def test_missing_owner_and_date_are_marked_not_invented():
    f = store.create(**DRAFT)["follow_up"]
    assert f["owner"] == "not documented" and f["due_date"] == "not documented"


def test_bad_date_rejected():
    with pytest.raises(ValueError, match="due_date"):
        store.create(**{**DRAFT, "due_date": "next Friday"})


def test_filters_and_status():
    store.create(**DRAFT)
    store.create(**{**DRAFT, "account": "Globex", "title": "Share uptime report"})
    assert store.list_follow_ups(account="globex")["total"] == 1
    assert store.set_status("F002", "done")["status"] == "done"
    assert store.list_follow_ups(status="open")["total"] == 1
    assert store.set_status("F999", "done") is None
