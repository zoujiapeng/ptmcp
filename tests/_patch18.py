import pathlib, re

for f in ("ptmcp/pt.py", "ptmcp/ops.py"):
    p = pathlib.Path(f); s = p.read_text(encoding="utf-8")
    # drop the mode probe that killed the console, restore PTBuilder's trick
    s = s.replace('''(function() {{
  var mode = "";
  try {{ mode = d.getIpcTerminalLine().getMode(); }} catch (e) {{}}
  if (mode !== "global") {{
    try {{ d.enterCommand("enable", ""); d.enterCommand("configure terminal", ""); }} catch (e) {{}}
  }}
}})();''', '''try {{ d.enterCommand("!", "global"); }} catch (e) {{}}''')
    s = s.replace('''  (function() {{
    var mode = "";
    try {{ mode = d.getIpcTerminalLine().getMode(); }} catch (e) {{}}
    if (mode !== "global") {{
      try {{ d.enterCommand("enable", ""); d.enterCommand("configure terminal", ""); }} catch (e) {{}}
    }}
  }})();''', '''  try {{ d.enterCommand("!", "global"); }} catch (e) {{}}''')
    p.write_text(s, encoding="utf-8")
    import ast; ast.parse(s)
print("reverted to enterCommand('!','global')")
