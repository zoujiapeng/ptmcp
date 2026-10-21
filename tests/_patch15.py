import pathlib

p = pathlib.Path("ptmcp/pt.py"); s = p.read_text(encoding="utf-8")
s = s.replace('''try {{ d.enterCommand("enable", ""); d.enterCommand("configure terminal", ""); }} catch (e) {{}}
var cmds = [{arr}];''','''(function() {{
  var mode = "";
  try {{ mode = d.getIpcTerminalLine().getMode(); }} catch (e) {{}}
  if (mode !== "global") {{
    try {{ d.enterCommand("enable", ""); d.enterCommand("configure terminal", ""); }} catch (e) {{}}
  }}
}})();
var cmds = [{arr}];''')
p.write_text(s, encoding="utf-8")

p = pathlib.Path("ptmcp/ops.py"); s = p.read_text(encoding="utf-8")
s = s.replace('''  try {{ d.enterCommand("enable", ""); d.enterCommand("configure terminal", ""); }} catch (e) {{}}
  var c = [{arr}];''','''  (function() {{
    var mode = "";
    try {{ mode = d.getIpcTerminalLine().getMode(); }} catch (e) {{}}
    if (mode !== "global") {{
      try {{ d.enterCommand("enable", ""); d.enterCommand("configure terminal", ""); }} catch (e) {{}}
    }}
  }})();
  var c = [{arr}];''')
p.write_text(s, encoding="utf-8")

import ast
for f in ("ptmcp/pt.py", "ptmcp/ops.py"):
    ast.parse(pathlib.Path(f).read_text(encoding="utf-8"))
print("mode-aware CLI prefix")
