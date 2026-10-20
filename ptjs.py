#!/usr/bin/env python
"""ptjs.py - talk to the Packet Tracer Script Engine over the file-bridge mailbox.

Protocol (from packet_tracer_mcp.infrastructure.execution.file_bridge):
    write  <mailbox>/req_<name>.js     -> the PT Script Engine picks it up
    read   <mailbox>/res_<name>.txt    <- it writes the result here

Usage:
    python ptjs.py "<javascript>"
    python ptjs.py --file script.js
    python ptjs.py --timeout 15 "<javascript>"

Mailbox: %LOCALAPPDATA%\\packet-tracer-mcp\\bridge
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path


def mailbox() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    root = Path(base) / "packet-tracer-mcp" if base else Path.home() / ".packet-tracer-mcp"
    d = root / "bridge"
    d.mkdir(parents=True, exist_ok=True)
    return d


def run(js: str, timeout: float = 12.0) -> str:
    d = mailbox()
    name = f"{os.getpid()}_{int(time.time() * 1000) % 1000000:06d}"
    req = d / f"req_{name}.js"
    res = d / f"res_{name}.txt"
    tmp = req.with_suffix(".js.tmp")
    tmp.write_bytes(js.encode("utf-8"))
    os.replace(tmp, req)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if res.exists():
            body = res.read_text(encoding="utf-8", errors="replace")
            try:
                res.unlink()
            except OSError:
                pass
            return body
        time.sleep(0.08)
    try:
        res.unlink()
    except OSError:
        pass
    return f"[timeout after {timeout}s - no res_{name}.txt]"


def main() -> int:
    args = sys.argv[1:]
    timeout = 12.0
    if args and args[0] == "--timeout":
        timeout = float(args[1])
        args = args[2:]
    if not args:
        print(__doc__)
        return 2
    if args[0] == "--file":
        js = Path(args[1]).read_text(encoding="utf-8")
    else:
        js = args[0]
    print(run(js, timeout))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
