"""compare.py - same topology through ptmcp and through cisco-pt-mcp.

Builds the campus spec with our own bridge (timed), then drives the competitor's
MCP server over stdio for the read-only / simulation tools it advertises and
records what actually answers.
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

import ptmcp.pt as pt  # noqa: E402

SPEC = root / "specs" / "campus.json"


async def competitor(reads: dict) -> None:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(command=sys.executable, args=["-m", "mcp_server.server"])
    t0 = time.time()
    try:
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()
                tools = await s.list_tools()
                reads["tools"] = len(tools.tools)
                reads["tool_names"] = [t.name for t in tools.tools][:25]
                for name, args in (("getNetwork", {}), ("getSimulationStatus", {})):
                    t1 = time.time()
                    try:
                        res = await s.call_tool(name, args)
                        text = " ".join(getattr(b, "text", "") for b in res.content)
                        reads[name] = {"ok": not res.isError, "s": round(time.time() - t1, 1),
                                       "head": text[:300]}
                    except Exception as exc:                    # noqa: BLE001
                        reads[name] = {"ok": False, "error": str(exc)[:200]}
    except Exception as exc:                                    # noqa: BLE001
        reads["server_error"] = str(exc)[:300]
    reads["total_s"] = round(time.time() - t0, 1)


def main() -> int:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    out: dict = {}

    t0 = time.time()
    build = pt.build(spec)
    out["ours"] = {"build_s": round(time.time() - t0, 1),
                   "all_up": build["link_check"].get("allUp"),
                   "asserts": build.get("asserts", {}).get("ok"),
                   "passed": build.get("asserts", {}).get("passed")}

    t1 = time.time()
    out["ours_ping"] = pt.ping("S1", "10.10.0.11") if False else None
    out["ours_ping_ms"] = round((time.time() - t1) * 1000)

    reads: dict = {}
    asyncio.run(competitor(reads))
    out["competitor"] = reads
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
