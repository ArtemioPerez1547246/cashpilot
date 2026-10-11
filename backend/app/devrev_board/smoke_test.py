"""Remote smoke test for the board connector. Writes nothing. Prints no token.

On the Linode:  cd ~/cashpilot/deploy && docker compose --env-file .env exec board \
                  python -m app.devrev_board.smoke_test https://YOUR-DOMAIN/mcp
(The board container already has MCP_TOKEN set.)
"""
import asyncio
import json
import os
import sys

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main(url):
    async with httpx.AsyncClient(timeout=30) as raw:
        r = await raw.post(url, json={})
        assert r.status_code == 401, f"unauthenticated request was not rejected (got {r.status_code})"
    print("PASS 1/4  no token -> 401")
    headers = {"Authorization": "Bearer " + os.environ["MCP_TOKEN"]}
    async with httpx.AsyncClient(headers=headers, timeout=30) as http, \
            streamable_http_client(url, http_client=http) as (read, write, _):
        async with ClientSession(read, write) as s:
            await s.initialize()
            names = {t.name for t in (await s.list_tools()).tools}
            want = {"list_follow_ups", "get_follow_up", "preview_follow_up", "create_follow_up"}
            assert want <= names, f"missing tools: {want - names}"
            print("PASS 2/4  initialize + 4 tools discovered")
            before = await s.call_tool("list_follow_ups", {})
            assert not before.isError, before.content
            total = (before.structuredContent or json.loads(before.content[0].text))["total"]
            p = await s.call_tool("preview_follow_up", {"account": "SMOKE TEST", "title": "Smoke test only",
                                                        "sources": [{"ref": "smoke/none"}]})
            assert not p.isError, p.content
            after = await s.call_tool("list_follow_ups", {})
            assert (after.structuredContent or json.loads(after.content[0].text))["total"] == total
            print("PASS 3/4  preview works and wrote nothing")
            bad = await s.call_tool("preview_follow_up", {"account": "SMOKE TEST", "title": "No evidence",
                                                          "sources": []})
            assert bad.isError, "a follow-up with no source should be rejected"
            print("PASS 4/4  no-evidence draft rejected")
    print("ALL PASS")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8001/mcp"))
