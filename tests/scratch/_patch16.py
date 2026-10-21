import pathlib
p = pathlib.Path("ptmcp/pdu.py"); s = p.read_text(encoding="utf-8")
old = '''    if settle:
        deadline = time.time() + settle
        while time.time() < deadline:
            if _ports_ready(source, destination):
                break
            time.sleep(2)'''
new = '''    if settle:
        # Hosts finish booting (and answer ARP) in REALTIME; switching PT to
        # simulation freezes that clock, so wait here before touching the engine.
        t0 = time.time()
        while time.time() - t0 < settle:
            if _booted(source) and _booted(destination):
                break
            time.sleep(2)
        time.sleep(min(8.0, settle))'''
assert old in s
s = s.replace(old, new)
s = s.replace('''def _ports_ready(a: str, b: str) -> bool:''','''def _booted(name: str) -> bool:
    js = _prelude() + f"""
var d = ipc.network().getDevice({json.dumps(name)});
if (!d) throw new Error("0");
var b = false;
try {{ b = (typeof d.isBooting === "function") ? d.isBooting() : false; }} catch (e) {{}}
throw new Error(b ? "0" : "1");
"""
    return (bridge.ask(js, timeout=20) or "").strip() == "1"


def _ports_ready(a: str, b: str) -> bool:''')
p.write_text(s, encoding="utf-8")
import ast; ast.parse(p.read_text(encoding="utf-8"))
print("settle now waits for boot in realtime")
