import pathlib

p = pathlib.Path("ptmcp/__init__.py"); s = p.read_text(encoding="utf-8")
s = s.replace("from . import asserts, bridge, catalog, ops, pt, state, ui",
              "from . import asserts, bridge, catalog, fix, ops, pt, state, ui")
s = s.replace('__all__ = ["asserts", "bridge"', '__all__ = ["asserts", "fix", "bridge"')
s = s.replace('__version__ = "1.3.0"', '__version__ = "1.4.0"')
p.write_text(s, encoding="utf-8")

p = pathlib.Path("ptmcp/__main__.py"); s = p.read_text(encoding="utf-8")
s = s.replace('''    rt = sub.add_parser("routing")''',
'''    fl = sub.add_parser("fixloop")
    fl.add_argument("spec")
    fl.add_argument("--rounds", type=int, default=3)
    fl.add_argument("--plan", action="store_true")

    rt = sub.add_parser("routing")''')
s = s.replace('''    if args.cmd == "asserts":''',
'''    if args.cmd == "fixloop":
        from .fix import fix_loop, plan
        sp = json.loads(Path(args.spec).read_text(encoding="utf-8"))
        _print(plan(sp) if args.plan else fix_loop(sp, rounds=args.rounds))
        return 0

    if args.cmd == "asserts":''')
p.write_text(s, encoding="utf-8")

p = pathlib.Path("ptmcp/server.py"); s = p.read_text(encoding="utf-8")
s += '''

@mcp.tool()
def pt_fix_plan(spec_json: str) -> str:
    """Show which assertion failures are auto-repairable and the ops that would fix them."""
    from .fix import plan
    return json.dumps(plan(json.loads(spec_json)), ensure_ascii=False, indent=2)


@mcp.tool()
def pt_fix_loop(spec_json: str, rounds: int = 3) -> str:
    """Assert -> repair -> re-assert, unattended, up to `rounds` times.

    Repairs access VLANs, trunk mode/native, trunk consistency, missing VLANs,
    VTP mode/domain and administratively-down interfaces. Anything that needs a
    design decision (or a re-cable) is returned under "manual" instead of being
    silently "fixed".
    """
    from .fix import fix_loop
    return json.dumps(fix_loop(json.loads(spec_json), rounds=rounds),
                      ensure_ascii=False, indent=2)
'''
p.write_text(s, encoding="utf-8")
print("patched")
