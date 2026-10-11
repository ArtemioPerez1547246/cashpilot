"""ForeCash follow-up board as an MCP server for DevRev Computer (Streamable HTTP + Bearer token).

Run from backend/:   MCP_TOKEN=... python -m app.devrev_board.server
In Computer set access modes: create_follow_up = Needs approval; the other three = Always allow.
"""
import hmac
import os

import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import BaseModel, Field

from app.devrev_board import store, vault

TOKEN = os.environ.get("MCP_TOKEN", "").encode("utf-8")
if len(TOKEN) < 32:
    raise SystemExit("MCP_TOKEN must be a random secret of at least 32 characters")
HOSTS = [h.strip() for h in os.getenv("MCP_ALLOWED_HOSTS", "localhost:*,127.0.0.1:*").split(",") if h.strip()]
ORIGINS = [o.strip() for o in os.getenv("MCP_ALLOWED_ORIGINS", "").split(",") if o.strip()]

mcp = FastMCP("ForeCash Follow-up Board and Evidence", stateless_http=True, json_response=True,
              transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=True,
                                                           allowed_hosts=HOSTS, allowed_origins=ORIGINS))
READ = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}
WRITE = {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}


class Source(BaseModel):
    ref: str = Field(description="Record ID, transcript ID or file path the commitment comes from")
    lines: str = Field("", description="Line range or location inside the source, if available")
    sha256: str = Field("", description="Source hash, if the evidence tool returned one")
    quote: str = Field("", description="Short exact quote of the commitment (max 300 chars)")


def _fields(account, title, sources, details, owner, due_date, requested_by):
    return dict(account=account, title=title, sources=[s.model_dump() for s in sources], details=details,
                owner=owner, due_date=due_date, requested_by=requested_by)


@mcp.tool(annotations=READ)
def list_sources(prefix: str = "", offset: int = 0, limit: int = 20) -> dict:
    """List the evidence files (synthetic, team-authored) (folders: transcripts/, crm_json_data/, pm_json_data/,
    maple_kb/, internal_docs/). Filter with prefix, e.g. 'transcripts/'. Page with next_offset."""
    return vault.list_sources(prefix, offset, limit)


@mcp.tool(annotations=READ)
def search_evidence(query: str, prefix: str = "", offset: int = 0, limit: int = 10) -> dict:
    """Literal, case-insensitive substring search over the export (NOT semantic). One hit per file.
    Use account names/IDs and promise phrases ("we will", "by Friday"); narrow with prefix.
    Always read_evidence around a hit before treating it as a commitment."""
    return vault.search_evidence(query, prefix, offset, limit)


@mcp.tool(annotations=READ)
def read_evidence(path: str, start_line: int = 1, max_lines: int = 60) -> dict:
    """Read a bounded window of one export file. Cite path + sha256 + start_line-end_line as the
    follow-up's source (ref = path, lines = 'start-end', sha256 = sha256)."""
    return vault.read_evidence(path, start_line, max_lines)


@mcp.tool(annotations=READ)
def list_follow_ups(account: str = "", status: str = "", limit: int = 20, offset: int = 0) -> dict:
    """List follow-ups already on the board, newest first. Filter by account (substring) and
    status (open|done). Call this before proposing new tasks to avoid duplicates."""
    return store.list_follow_ups(account, status, limit, offset)


@mcp.tool(annotations=READ)
def get_follow_up(follow_up_id: str) -> dict:
    """Read one follow-up by ID (e.g. F001). Use after an uncertain create to check the result."""
    f = store.get(follow_up_id)
    if f is None:
        raise ValueError(f"follow-up {follow_up_id} not found")
    return f


@mcp.tool(annotations=READ)
def preview_follow_up(account: str, title: str, sources: list[Source], details: str = "", owner: str = "",
                      due_date: str = "", requested_by: str = "") -> dict:
    """Validate a proposed follow-up and return exactly what would be created, its idempotency_key,
    and duplicate_of if it already exists. Writes nothing. Leave owner/due_date empty when the
    source does not state them; they are recorded as 'not documented'."""
    return store.preview(**_fields(account, title, sources, details, owner, due_date, requested_by))


@mcp.tool(annotations=WRITE)
def create_follow_up(account: str, title: str, sources: list[Source], idempotency_key: str, details: str = "",
                     owner: str = "", due_date: str = "", requested_by: str = "") -> dict:
    """Create a follow-up on the board ONLY after the user approved the preview. Pass the
    idempotency_key from preview_follow_up. Repeating the call returns the existing task
    (created=false) instead of a duplicate. After a timeout, call get_follow_up or
    list_follow_ups before retrying."""
    return store.create(idempotency_key=idempotency_key,
                        **_fields(account, title, sources, details, owner, due_date, requested_by))


class BearerGate:
    """Reject any request without the exact Bearer token (constant-time compare)."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            supplied = dict(scope.get("headers", [])).get(b"authorization", b"")
            if not hmac.compare_digest(supplied, b"Bearer " + TOKEN):
                await send({"type": "http.response.start", "status": 401,
                            "headers": [(b"content-type", b"application/json"), (b"www-authenticate", b"Bearer")]})
                await send({"type": "http.response.body", "body": b'{"error":"unauthorized"}'})
                return
        await self.app(scope, receive, send)


app = BearerGate(mcp.streamable_http_app())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("BOARD_PORT", "8001")))
