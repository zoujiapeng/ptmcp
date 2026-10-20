#!/usr/bin/env python
"""ptc.py - CLI client for the Packet Tracer MCP server (streamable HTTP).

Usage:
    python ptc.py list
    python ptc.py desc <tool>
    python ptc.py call <tool> '<json args>'
    python ptc.py call <tool> @args.json

The server (packet_tracer_mcp) listens on http://127.0.0.1:39000/mcp and
drives the running Cisco Packet Tracer through the MCP-BUILDER script module.
"""
from __future__ import annotations

import asyncio
import json
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

URL = "http://127.0.0.1:39000/mcp"


def _dump(obj):
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return obj


async def _run(cmd: str, argv: list[str]) -> int:
    async with streamablehttp_client(URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            info = await session.initialize()
            srv = info.serverInfo
            print(f"[server] {srv.name} v{getattr(srv, 'version', '?')}")

            if cmd == "list":
                tools = await session.list_tools()
                for t in tools.tools:
                    print(t.name)
                print(f"[count] {len(tools.tools)}")
                return 0

            if cmd == "desc":
                tools = await session.list_tools()
                for t in tools.tools:
                    if t.name == argv[0]:
                        print(json.dumps({"name": t.name,
                                          "description": t.description,
                                          "input_schema": t.inputSchema},
                                         indent=2, ensure_ascii=False))
                        return 0
                print(f"tool not found: {argv[0]}")
                return 2

            if cmd == "call":
                name = argv[0]
                raw = argv[1] if len(argv) > 1 else "{}"
                if raw.startswith("@"):
                    raw = open(raw[1:], encoding="utf-8").read()
                args = json.loads(raw)
                res = await session.call_tool(name, args)
                for block in res.content:
                    text = getattr(block, "text", None)
                    print(text if text is not None else block)
                if res.isError:
                    print("[isError] true")
                    return 1
                return 0

    print(f"unknown command: {cmd}")
    return 2


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    return asyncio.run(_run(sys.argv[1], sys.argv[2:]))


if __name__ == "__main__":
    raise SystemExit(main())
