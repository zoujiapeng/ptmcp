#!/usr/bin/env python
"""ptmcp - CLI entry point.

    python -m ptmcp bootstrap                 # install / verify the PT side
    python -m ptmcp status
    python -m ptmcp new
    python -m ptmcp build spec.json [--save out.pkt]
    python -m ptmcp cli S1 "show vlan"
    python -m ptmcp ping 192.168.2.1 192.168.2.2
    python -m ptmcp save C:\\pt\\lab.pkt
    python -m ptmcp serve                     # MCP server (stdio)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import bridge, pt


def _print(obj) -> None:
    print(obj if isinstance(obj, str) else json.dumps(obj, indent=2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="ptmcp", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("bootstrap")
    sub.add_parser("status")
    sub.add_parser("new")
    b = sub.add_parser("build")
    b.add_argument("spec")
    b.add_argument("--save")
    b.add_argument("--no-new", action="store_true")
    c = sub.add_parser("cli")
    c.add_argument("device")
    c.add_argument("commands", nargs="+")
    p = sub.add_parser("ping")
    p.add_argument("source")
    p.add_argument("target")
    p.add_argument("--count", type=int, default=4)
    s = sub.add_parser("save")
    s.add_argument("path")
    sub.add_parser("serve")

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

    if args.cmd == "status":
        _print(pt.status())
    elif args.cmd == "new":
        _print(pt.new_canvas())
    elif args.cmd == "build":
        spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
        _print(pt.build(spec, new=not args.no_new, save_to=args.save or spec.get("save")))
    elif args.cmd == "cli":
        _print(pt.cli(args.device, args.commands))
    elif args.cmd == "ping":
        _print(pt.ping(args.source, args.target, args.count))
    elif args.cmd == "save":
        _print(pt.save(args.path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
