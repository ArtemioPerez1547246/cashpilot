"""Best-effort copy of owner updates into DevRev as a comment (DevRev REST API, timeline-entries.create).

Configured only on the server: DEVREV_PAT (a DevRev personal access token) and DEVREV_OBJECT_ID (the
DevRev object to comment on, for example an account or a task). Never blocks the CashPilot update.
"""
import os

import requests

URL = "https://api.devrev.ai/timeline-entries.create"


def configured():
    return bool(os.getenv("DEVREV_PAT") and os.getenv("DEVREV_OBJECT_ID"))


def post_comment(text):
    if not configured():
        return {"synced": False, "detail": "DevRev sync not configured on the server"}
    try:
        r = requests.post(URL, timeout=10,
                          headers={"Authorization": os.environ["DEVREV_PAT"], "Content-Type": "application/json"},
                          json={"object": os.environ["DEVREV_OBJECT_ID"], "type": "timeline_comment",
                                "body": text[:4000], "body_type": "text"})
        if r.ok:
            return {"synced": True, "detail": "Comment added in DevRev"}
        return {"synced": False, "detail": f"DevRev returned {r.status_code}"}
    except requests.RequestException as e:
        return {"synced": False, "detail": f"DevRev not reachable ({type(e).__name__})"}
