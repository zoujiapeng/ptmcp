import pathlib

p = pathlib.Path("ptmcp/__init__.py"); s = p.read_text(encoding="utf-8")
s = s.replace("from . import asserts, bridge, catalog, fix, ops, pt, state, ui",
              "from . import asserts, bridge, catalog, fix, ops, pt, shot, state, ui")
s = s.replace('__all__ = ["asserts", "fix", "bridge"', '__all__ = ["asserts", "fix", "shot", "bridge"')
s = s.replace('__version__ = "1.4.0"', '__version__ = "1.6.0"')
p.write_text(s, encoding="utf-8")

# CLI: shot + start
p = pathlib.Path("ptmcp/__main__.py"); s = p.read_text(encoding="utf-8")
s = s.replace('''    mo = sub.add_parser("mode")''',
'''    sh = sub.add_parser("shot")
    sh.add_argument("path")

    st = sub.add_parser("start")

    mo = sub.add_parser("mode")''')
s = s.replace('''        "save": lambda: pt.save(args.path),''',
'''        "shot": lambda: shot.capture(args.path),
        "start": lambda: start_pt(),
        "save": lambda: pt.save(args.path),''')
s = s.replace("from . import bridge, ops, pt, state, ui",
              "from . import bridge, ops, pt, shot, state, ui")
s = s.replace('''def _print(obj) -> None:''',
'''def start_pt() -> str:
    """Launch Packet Tracer (if needed) and wait for the script engine."""
    import subprocess
    import time as _t
    if bridge.alive():
        return "already running and polling"
    exe = r"C:\\\\Program Files\\\\Cisco Packet Tracer 8.0\\\\bin\\\\PacketTracer.exe"
    if not Path(exe).exists():
        from .bootstrap import find_pt
        root = find_pt()
        if not root:
            return "Packet Tracer not found"
        exe = str(root / "bin" / "PacketTracer.exe")
    subprocess.Popen([exe])
    for _ in range(40):
        _t.sleep(3)
        if bridge.alive():
            return "started, engine alive"
    return "started, but the MCP BUILDER module is not polling (check bootstrap)"


def _print(obj) -> None:''')
p.write_text(s, encoding="utf-8")

# MCP: screenshot tool
p = pathlib.Path("ptmcp/server.py"); s = p.read_text(encoding="utf-8")
s += '''

@mcp.tool()
def pt_screenshot(path: str) -> str:
    """Save a PNG of the Packet Tracer window. No mouse/keyboard involved."""
    from .shot import capture
    return capture(path)
'''
s = s.replace("from . import bridge, ops, pt, state, ui", "from . import bridge, ops, pt, shot, state, ui")
p.write_text(s, encoding="utf-8")
print("patched")
