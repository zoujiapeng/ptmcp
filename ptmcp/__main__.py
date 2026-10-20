#!/usr/bin/env python
"""ptmcp - "Packet Tracer as a CLI" for agents.

    python -m ptmcp bootstrap
    python -m ptmcp status | new | ui | view
    python -m ptmcp precheck spec.json [--fix]
    python -m ptmcp build spec.json [--save out.pkt]
    python -m ptmcp show S1 run|vlan|vtp|mac|interfaces
    python -m ptmcp routing R1
    python -m ptmcp cli S1 "vlan 2" "exit"
    python -m ptmcp batch ops.json
    python -m ptmcp ping S1 192.168.2.1
    python -m ptmcp power R1 on|off | rename S1 CORE | module R1 0 HWIC-2T
    python -m ptmcp mode simulation | panels --left 0 --bottom 1 | window maximize
    python -m ptmcp clip "text" | save C:\\pt\\lab.pkt | serve
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import bridge, ops, pt, state, ui


def _print(obj) -> None:
    print(obj if isinstance(obj, str) else json.dumps(obj, indent=2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="ptmcp", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    for name in ("bootstrap", "status", "new", "serve", "view", "ui"):
        sub.add_parser(name)

    pc = sub.add_parser("precheck")
    pc.add_argument("spec")
    pc.add_argument("--fix", action="store_true")

    b = sub.add_parser("build")
    b.add_argument("spec")
    b.add_argument("--save")
    b.add_argument("--no-new", action="store_true")

    s = sub.add_parser("show")
    s.add_argument("device")
    s.add_argument("what", nargs="?", default="run")

    asrt = sub.add_parser("asserts")
    asrt.add_argument("spec")

    rt = sub.add_parser("routing")
    rt.add_argument("device")

    c = sub.add_parser("cli")
    c.add_argument("device")
    c.add_argument("commands", nargs="+")

    ba = sub.add_parser("batch")
    ba.add_argument("ops")

    p = sub.add_parser("ping")
    p.add_argument("source")
    p.add_argument("target")
    p.add_argument("--count", type=int, default=4)

    pw = sub.add_parser("power")
    pw.add_argument("device")
    pw.add_argument("state", choices=["on", "off"])

    rn = sub.add_parser("rename")
    rn.add_argument("device")
    rn.add_argument("new_name")

    md = sub.add_parser("module")
    md.add_argument("device")
    md.add_argument("slot", type=int)
    md.add_argument("model")

    mo = sub.add_parser("mode")
    mo.add_argument("mode")

    pn = sub.add_parser("panels")
    pn.add_argument("--left", type=int, default=1)
    pn.add_argument("--bottom", type=int, default=1)

    win = sub.add_parser("window")
    win.add_argument("action", nargs="?", default="maximize")
    win.add_argument("--width", type=int, default=0)
    win.add_argument("--height", type=int, default=0)

    cl = sub.add_parser("clip")
    cl.add_argument("text", nargs="?", default=None)

    sv = sub.add_parser("save")
    sv.add_argument("path")

    args = ap.parse_args(argv)

    if args.cmd == "serve":
        from .server import mcp
        mcp.run(transport="stdio")
        return 0
    if args.cmd == "bootstrap":
        from . import bootstrap
        return bootstrap.main()

    if not bridge.alive():
        _print("PT script engine is not polling. Run `python -m ptmcp bootstrap`.")
        return 1

    if args.cmd == "precheck":
        from .precheck import precheck
        sp = json.loads(Path(args.spec).read_text(encoding="utf-8"))
        _print(precheck(sp, fix=args.fix))
        return 0

    if args.cmd == "asserts":
        from .asserts import check
        sp = json.loads(Path(args.spec).read_text(encoding="utf-8"))
        _print(check(sp))
        return 0

    if args.cmd == "build":
        spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
        _print(pt.build(spec, new=not args.no_new, save_to=args.save or spec.get("save")))
        return 0

    dispatch = {
        "status": lambda: pt.status(),
        "new": lambda: pt.new_canvas(),
        "ui": lambda: ui.controls(),
        "view": lambda: ui.view_state(),
        "show": lambda: state.show(args.device, args.what),
        "routing": lambda: state.routing(args.device),
        "cli": lambda: pt.cli(args.device, args.commands),
        "batch": lambda: ops.batch(json.loads(Path(args.ops).read_text(encoding="utf-8"))),
        "ping": lambda: pt.ping(args.source, args.target, args.count),
        "power": lambda: ops.power(args.device, args.state == "on"),
        "rename": lambda: ops.rename(args.device, args.new_name),
        "module": lambda: ops.add_module(args.device, args.slot, args.model),
        "mode": lambda: ui.switch_mode(args.mode),
        "panels": lambda: ui.panels(bool(args.left), bool(args.bottom)),
        "window": lambda: ui.window(args.action, args.width, args.height),
        "clip": lambda: ui.clipboard(args.text),
        "save": lambda: pt.save(args.path),
    }
    if args.cmd in dispatch:
        _print(dispatch[args.cmd]())
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
