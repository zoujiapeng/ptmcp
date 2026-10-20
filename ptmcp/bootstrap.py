#!/usr/bin/env python
"""ptmcp bootstrap - install the Packet Tracer side and verify it.

What it does on a fresh machine:
  1. locate the Packet Tracer installation (registry, then Program Files),
  2. fetch the MCP-BUILDER script module (V5.2.pts, MIT, from the upstream
     release) and verify its SHA-256,
  3. copy it into <PT>\\extensions\\MCPBuilder\\ so PT offers it in
     Extensions > Scripting > Configure PT Script Modules,
  4. report the exact state and the one-time GUI step if it is still missing.

The script module is the part that runs inside PT and polls the file mailbox;
without it nothing can be automated. PT has no CLI flag to register modules,
so step 3 is the closest we can get to a silent install - once registered and
started (or set to "On Startup"), it survives PT restarts.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

MODULE_URL = "https://github.com/Mats2208/MCP-Packet-Tracer/releases/download/v0.9.0/V5.2.pts"
MODULE_SHA256 = "175F775560AF7C17348C3D20CFFC81AE5DC8D294D2486CC9E8409FBEAD8BC071"
MODULE_NAME = "V5.2.pts"

PT_GLOBS = [
    r"C:\Program Files\Cisco Packet Tracer *",
    r"C:\Program Files (x86)\Cisco Packet Tracer *",
]


def local_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    d = Path(base) / "packet-tracer-mcp"
    d.mkdir(parents=True, exist_ok=True)
    return d


def find_pt() -> Path | None:
    import glob

    best: tuple[float, Path] | None = None
    for pattern in PT_GLOBS:
        for root in glob.glob(pattern):
            exe = Path(root) / "bin" / "PacketTracer.exe"
            if exe.exists():
                stamp = exe.stat().st_mtime
                if best is None or stamp > best[0]:
                    best = (stamp, exe)
    return best[1].parent.parent if best else None


def _obtain(dest: Path) -> str:
    """Get V5.2.pts: repo asset first, then local cache, then download."""
    repo_asset = Path(__file__).resolve().parents[1] / "assets" / MODULE_NAME
    for src, label in ((repo_asset, "repo asset"), (dest, "cache")):
        if src.exists():
            got = hashlib.sha256(src.read_bytes()).hexdigest().upper()
            if got == MODULE_SHA256:
                if src != dest:
                    dest.write_bytes(src.read_bytes())
                return f"{label} {dest} (sha256 ok)"
    last: Exception | None = None
    for _ in range(3):
        try:
            req = urllib.request.Request(MODULE_URL, headers={"User-Agent": "ptmcp-bootstrap"})
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            got = hashlib.sha256(data).hexdigest().upper()
            if got != MODULE_SHA256:
                raise RuntimeError(f"V5.2.pts checksum mismatch: {got}")
            dest.write_bytes(data)
            return f"downloaded {dest} ({len(data)} bytes, sha256 ok)"
        except Exception as exc:                               # noqa: BLE001
            last = exc
            time.sleep(2)
    raise RuntimeError(
        f"cannot fetch {MODULE_NAME} ({last}). Put it in ./assets/{MODULE_NAME} "
        "or copy it from another machine - it is the MIT-licensed MCP-BUILDER "
        "script module from github.com/Mats2208/MCP-Packet-Tracer"
    )


def install_module(pt_root: Path) -> str:
    src = local_dir() / MODULE_NAME
    msg = _obtain(src)
    target_dir = pt_root / "extensions" / "MCPBuilder"
    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, target_dir / MODULE_NAME)
    return f"{msg}; copied to {target_dir / MODULE_NAME}"


def main() -> int:
    from . import bridge

    print("== ptmcp bootstrap ==")
    pt_root = find_pt()
    if not pt_root:
        print("FAIL: Packet Tracer not found in Program Files")
        return 1
    print(f"PT install : {pt_root}")
    try:
        print("module     : " + install_module(pt_root))
    except PermissionError as exc:
        print(f"module     : FAIL (needs admin to write into Program Files): {exc}")
    except Exception as exc:                                   # noqa: BLE001
        print(f"module     : FAIL ({exc})")

    running = any("PacketTracer" in p.name for p in _procs())
    print(f"PT running : {running}")
    print(f"engine     : {'ALIVE' if bridge.alive() else 'not polling'}")
    if not bridge.alive():
        print(
            "\nOne-time GUI step (PT has no silent module registration):\n"
            "  Packet Tracer > Extensions > Scripting > Configure PT Script Modules\n"
            "  > select 'MCP BUILDER' > Settings > 'On Startup' > Start\n"
            "After that, every later session is fully headless."
        )
        return 2
    print("ready: run `python -m ptmcp serve` for the MCP server")
    return 0


def _procs():
    if os.name != "nt":
        return []
    try:
        out = subprocess.run(
            ["tasklist", "/fo", "csv", "/nh"], capture_output=True, text=True, timeout=20
        ).stdout
    except Exception:                                          # noqa: BLE001
        return []

    class P:
        def __init__(self, name: str):
            self.name = name

    return [P(line.split('","')[0].strip('"')) for line in out.splitlines() if line.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
