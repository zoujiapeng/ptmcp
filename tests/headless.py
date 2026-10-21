"""headless.py - the whole pipeline with ZERO GUI automation.

Cold start: Packet Tracer is not running. This script
  1. launches Packet Tracer (subprocess, no clicks),
  2. waits until the in-process script engine is polling the bridge,
  3. builds the campus topology from JSON,
  4. waits for every link to come up,
  5. runs the declared assertions,
  6. saves the .pkt,
  7. captures a PNG of the window via PrintWindow (no mouse/keyboard).

    python tests/headless.py [spec.json]

Nothing here uses the computer-use layer: no mouse, no keyboard, no UIA.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

from ptmcp import bridge, pt, shot, state  # noqa: E402
from ptmcp.asserts import check  # noqa: E402

PT_EXE = r"C:\Program Files\Cisco Packet Tracer 8.0\bin\PacketTracer.exe"


def kill_pt() -> None:
    subprocess.run(["taskkill", "/F", "/IM", "PacketTracer.exe"],
                   capture_output=True, text=True, timeout=30)


def pids() -> set[int]:
    out = subprocess.run(["tasklist", "/fi", "IMAGENAME eq PacketTracer.exe", "/fo", "csv", "/nh"],
                         capture_output=True, text=True, timeout=20).stdout
    return {int(l.split('","')[1]) for l in out.splitlines() if l.lower().startswith('"packettracer.exe')}


def launch_and_wait(timeout: float = 150.0) -> float:
    """Start PT and wait until the *new* process is polling the bridge."""
    before = pids()
    t0 = time.time()
    subprocess.Popen([PT_EXE])
    alive_file = bridge.bridge_dir() / "alive.txt"
    while time.time() - t0 < timeout:
        now = pids()
        fresh = alive_file.exists() and alive_file.stat().st_mtime >= t0
        if now - before and fresh and bridge.alive():
            return time.time() - t0
        time.sleep(2)
    raise TimeoutError("PT started but the script engine never polled the bridge")


def main() -> int:
    spec_path = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "specs" / "campus.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    report: dict = {"spec": str(spec_path)}

    print("[1/6] killing any running Packet Tracer...")
    kill_pt()
    time.sleep(3)

    print("[2/6] launching Packet Tracer (no GUI automation)...")
    report["engine_ready_s"] = round(launch_and_wait(), 1)
    print(f"      engine alive after {report['engine_ready_s']}s")

    print("[3/6] building the topology...")
    t0 = time.time()
    build = pt.build(spec)
    report["build_s"] = round(time.time() - t0, 1)
    report["devices"] = len(spec["devices"])
    report["links"] = len(spec["links"])
    print(f"      {report['devices']} devices / {report['links']} links in {report['build_s']}s")

    print("[4/6] waiting for every link to come up...")
    t0 = time.time()
    links = pt.wait_links_up(spec, timeout=90)
    report["green_s"] = round(time.time() - t0, 1)
    report["all_up"] = links.get("allUp")
    print(f"      all_up={report['all_up']} after {report['green_s']}s")
    if not links.get("allUp"):
        report["down"] = [d for d in links.get("detail", []) if "DOWN" in d]

    print("[5/6] assertions...")
    asserts = check(spec)
    report["asserts"] = {"ok": asserts["ok"], "passed": asserts["passed"], "failed": asserts["failed"],
                         "failures": asserts["failures"]}
    print(f"      {asserts['passed']} passed / {asserts['failed']} failed")

    print("[5b/6] letting STP settle before the screenshot...")
    time.sleep(float(spec.get("settle", 35)))

    print("[6/6] saving .pkt + screenshot (PrintWindow, no input)...")
    report["save"] = pt.save(spec["save"])
    png = str(Path(spec["save"]).with_suffix(".png"))
    report["screenshot"] = shot.capture(png)

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if (report["all_up"] and asserts["ok"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
