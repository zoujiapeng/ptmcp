"""wire_term.py - add terminal + borrow integrations to the package surfaces."""
import pathlib

# 1) package exports
p = pathlib.Path("ptmcp/__init__.py")
s = p.read_text(encoding="utf-8")
s = s.replace("from . import asserts, bridge, catalog, fix, ops, pt, shot, state, ui",
              "from . import asserts, borrow, bridge, catalog, fix, ops, pdu, pt, shot, state, term, ui")
s = s.replace('__all__ = ["asserts", "fix", "shot", "bridge"',
              '__all__ = ["asserts", "borrow", "fix", "pdu", "shot", "term", "bridge"')
s = s.replace('__version__ = "1.6.0"', '__version__ = "1.8.0"')
p.write_text(s, encoding="utf-8")

# 2) CLI: term / run / type / pdu-ping
p = pathlib.Path("ptmcp/__main__.py")
s = p.read_text(encoding="utf-8")
s = s.replace("from . import bridge, ops, pt, shot, state, ui",
              "from . import bridge, ops, pdu, pt, shot, state, term, ui")
s = s.replace('''    rt = sub.add_parser("routing")''',
'''    tm = sub.add_parser("term")
    tm.add_argument("device")

    rn2 = sub.add_parser("run")
    rn2.add_argument("device")
    rn2.add_argument("lines", nargs="+")

    tp = sub.add_parser("type")
    tp.add_argument("device")
    tp.add_argument("text")

    pp = sub.add_parser("pdu-ping")
    pp.add_argument("source")
    pp.add_argument("destination")

    rt = sub.add_parser("routing")''')
s = s.replace('''        "routing": lambda: state.routing(args.device),''',
'''        "routing": lambda: state.routing(args.device),
        "term": lambda: term.state(args.device),
        "run": lambda: term.run(args.device, args.lines),
        "type": lambda: term.type_(args.device, args.text),
        "pdu-ping": lambda: pdu.ping(args.source, args.destination),''')
p.write_text(s, encoding="utf-8")

# 3) MCP tools
p = pathlib.Path("ptmcp/server.py")
s = p.read_text(encoding="utf-8")
s = s.replace("from . import bridge, ops, pt, shot, state, ui",
              "from . import bridge, ops, pdu, pt, shot, state, term, ui")
s += '''

# ------------------------------------------------------------- terminal (CLI)


@mcp.tool()
def pt_term(device: str) -> str:
    """Prompt, mode and pending input of the device's terminal."""
    _need_engine()
    return json.dumps(term.state(device), ensure_ascii=False)


@mcp.tool()
def pt_term_run(device: str, lines: str) -> str:
    """Execute CLI lines in the device terminal (newline separated), returning the prompt after each."""
    _need_engine()
    return json.dumps(term.run(device, [l for l in lines.splitlines() if l.strip()]),
                      ensure_ascii=False, indent=2)


@mcp.tool()
def pt_term_type(device: str, text: str, enter: bool = True) -> str:
    """Type into the terminal character by character (human-like keystrokes)."""
    _need_engine()
    return json.dumps(term.type_(device, text, enter=enter), ensure_ascii=False)


@mcp.tool()
def pt_term_println(device: str, text: str) -> str:
    """Write a line into the device's terminal display, so a human sees it in the CLI."""
    _need_engine()
    return term.println(device, text)


@mcp.tool()
def pt_pdu_ping(source: str, destination: str) -> str:
    """ICMP reachability through PT's simulation (experimental verdict, see README)."""
    _need_engine()
    return json.dumps(pdu.ping(source, destination), ensure_ascii=False, indent=2)


@mcp.tool()
def pt_borrow_vlan(vlans_json: str, access_ports_json: str = "[]",
                   trunks_json: str = "[]", switch_model: str = "2960-24TT") -> str:
    """Generate VLAN/trunk CLI with the generators of packet-tracer-mcp (MIT).

    Returns the IOS lines; feed them to pt_term_run to apply them.
    """
    from .borrow import vlan_cli
    return json.dumps(vlan_cli(json.loads(vlans_json), json.loads(access_ports_json),
                               json.loads(trunks_json), switch_model),
                      ensure_ascii=False, indent=2)
'''
p.write_text(s, encoding="utf-8")

import ast
for f in ("ptmcp/__init__.py", "ptmcp/__main__.py", "ptmcp/server.py", "ptmcp/term.py", "ptmcp/borrow.py"):
    ast.parse(pathlib.Path(f).read_text(encoding="utf-8"))
print("wired and syntax-checked")
