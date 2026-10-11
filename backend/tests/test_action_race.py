"""20 simultaneous drafts: no crashes, unique IDs, and the same key still gives one action."""
import os
import tempfile
import threading

os.environ.setdefault("CASHPILOT_STATE_DIR", tempfile.mkdtemp(prefix="forecash-race-"))
from app.actions import store  # noqa: E402


def test_simultaneous_drafts_do_not_collide():
    store.clear()
    errors = []

    def go(i, lever):
        try:
            store.draft_action(lever, "test", "Someone", "s", "b", [f"T{i:02d}"])
        except Exception as e:
            errors.append(e)
    threads = [threading.Thread(target=go, args=(i, f"L{i}")) for i in range(20)]
    threads += [threading.Thread(target=go, args=(99, "SAME")) for _ in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()
    ids = [a.id for a in store.list_actions()]
    assert not errors and len(ids) == 21 and len(set(ids)) == 21
