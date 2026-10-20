"""ptmcp.bridge - dialog-free transport into Packet Tracer's Script Engine.

The PT Script Module "MCP BUILDER" polls a mailbox on disk:

    %LOCALAPPDATA%\\packet-tracer-mcp\\bridge\\req_<id>.js   -> executed by PT
    %LOCALAPPDATA%\\packet-tracer-mcp\\bridge\\res_<id>.txt  <- result written back
    %LOCALAPPDATA%\\packet-tracer-mcp\\bridge\\alive.txt     <- heartbeat

Nothing here touches the GUI, so the automation never needs focus and - as long
as we only use the calls below - never opens a modal dialog:

  * new canvas        -> fileNew(false)        (fileNew() prompts to save)
  * save              -> fileSaveAs(<unused>)  (overwriting an existing path
                        opens "Overwrite File?" and blocks the engine, so callers
                        must pass a path that does not exist yet; see save_pkt)
  * never call        -> removeDevice()/fileOpen() while a request is in flight

The engine returns text only by throwing an Error, so every payload ends with
`throw new Error(<text>)` and the result is unwrapped here.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

ALIVE_MAX_AGE = 8.0
DEFAULT_TIMEOUT = 20.0


class PTNotReady(RuntimeError):
    """The Packet Tracer script engine is not polling the mailbox."""


class PTTimeout(RuntimeError):
    """No answer from PT before the deadline."""


def bridge_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    root = Path(base) / "packet-tracer-mcp" if base else Path.home() / ".packet-tracer-mcp"
    d = root / "bridge"
    d.mkdir(parents=True, exist_ok=True)
    return d


def alive(max_age: float = ALIVE_MAX_AGE) -> bool:
    try:
        return (time.time() - (bridge_dir() / "alive.txt").stat().st_mtime) < max_age
    except OSError:
        return False


def run_js(js: str, timeout: float = DEFAULT_TIMEOUT) -> str:
    d = bridge_dir()
    stamp = f"{os.getpid()}_{int(time.time() * 1000) % 10**8:08d}"
    req, res = d / f"req_{stamp}.js", d / f"res_{stamp}.txt"
    tmp = req.with_suffix(".js.tmp")
    tmp.write_bytes(js.encode("utf-8"))          # binary: no CRLF translation
    os.replace(tmp, req)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if res.exists():
            body = res.read_text(encoding="utf-8", errors="replace")
            res.unlink(missing_ok=True)
            return _unwrap(body.strip())
        time.sleep(0.05)
    res.unlink(missing_ok=True)
    raise PTTimeout(
        "Packet Tracer did not answer. Check: PT is running, the MCP BUILDER "
        "script module is started (Extensions > Scripting > Configure PT Script "
        "Modules), and no modal dialog is waiting (a dialog blocks the engine)."
    )


def ask(js_body: str, timeout: float = DEFAULT_TIMEOUT) -> str:
    """Send a payload that must end with `throw new Error(<text>)`."""
    return run_js(js_body, timeout=timeout)


def _unwrap(raw: str) -> str:
    for prefix in ("PT_ERROR: Error: ", "PT_ERROR: "):
        if raw.startswith(prefix):
            return raw[len(prefix):]
    return raw


def q(text: str) -> str:
    """JSON-quote a Python string for embedding in JS."""
    return json.dumps(text)
