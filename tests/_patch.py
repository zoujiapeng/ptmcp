import re, pathlib

# 1) package export
p = pathlib.Path("ptmcp/__init__.py"); s = p.read_text(encoding="utf-8")
s = s.replace("from . import bridge, catalog, ops, pt, state, ui",
              "from . import asserts, bridge, catalog, ops, pt, state, ui")
s = s.replace('__all__ = ["bridge", "catalog", "ops", "pt", "state", "ui", "__version__"]',
              '__all__ = ["asserts", "bridge", "catalog", "ops", "pt", "state", "ui", "__version__"]')
s = s.replace('__version__ = "1.1.0"', '__version__ = "1.3.0"')
p.write_text(s, encoding="utf-8")

# 2) build() appends assertion results when the spec declares them
p = pathlib.Path("ptmcp/pt.py"); s = p.read_text(encoding="utf-8")
s = s.replace('''    if save_to:
        report["save"] = save(save_to)''',
'''    if spec.get("asserts"):
        from .asserts import check as _check
        try:
            report["asserts"] = _check(spec)
        except Exception as exc:                               # noqa: BLE001
            report["asserts"] = {"ok": None, "error": str(exc)}
    if save_to:
        report["save"] = save(save_to)''')
p.write_text(s, encoding="utf-8")

# 3) CLI
p = pathlib.Path("ptmcp/__main__.py"); s = p.read_text(encoding="utf-8")
s = s.replace('''    rt = sub.add_parser("routing")''',
'''    asrt = sub.add_parser("asserts")
    asrt.add_argument("spec")

    rt = sub.add_parser("routing")''')
s = s.replace('''        "routing": lambda: state.routing(args.device),''',
'''        "routing": lambda: state.routing(args.device),''')
s = s.replace('''    if args.cmd == "build":''',
'''    if args.cmd == "asserts":
        from .asserts import check
        sp = json.loads(Path(args.spec).read_text(encoding="utf-8"))
        _print(check(sp))
        return 0

    if args.cmd == "build":''')
p.write_text(s, encoding="utf-8")

# 4) MCP tool
p = pathlib.Path("ptmcp/server.py"); s = p.read_text(encoding="utf-8")
s += '''

@mcp.tool()
def pt_asserts(spec_json: str) -> str:
    """Check the lab against declared assertions (same_vlan / diff_vlan / trunk / ...).

    Rules live in the spec under "asserts"; every failure comes with a concrete
    fix, so an agent can repair instead of guessing. This is the difference
    between "links look green" and "the lab is actually correct".
    """
    from .asserts import check
    return json.dumps(check(json.loads(spec_json)), ensure_ascii=False, indent=2)
'''
p.write_text(s, encoding="utf-8")
print("patched")
