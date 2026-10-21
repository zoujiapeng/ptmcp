import pathlib

# pdu.ping: always leave realtime mode (simulation mode distorts later builds)
p = pathlib.Path("ptmcp/pdu.py"); s = p.read_text(encoding="utf-8")
s = s.replace('''if (!wasSim) {{ try {{ sim.setSimulationMode(false); }} catch (e) {{}} }}''',
'''try {{ sim.setSimulationMode(false); }} catch (e) {{}}   // always back to realtime''')
p.write_text(s, encoding="utf-8")

# build(): force realtime mode before touching the canvas
p = pathlib.Path("ptmcp/pt.py"); s = p.read_text(encoding="utf-8")
old = '''    lines: list[str] = []
    if new:
        lines.append("ipc.appWindow().fileNew(false);")'''
new = '''    lines: list[str] = []
    if new:
        lines.append("ipc.appWindow().fileNew(false);")
    lines.append("try { var __sim = ipc.simulation();"
                 " if (__sim.isSimulationMode()) __sim.setSimulationMode(false); } catch (e) {}")'''
assert old in s
p.write_text(s.replace(old, new), encoding="utf-8")

import ast
for f in ("ptmcp/pt.py", "ptmcp/pdu.py"):
    ast.parse(pathlib.Path(f).read_text(encoding="utf-8"))
print("simulation-mode hygiene added")
