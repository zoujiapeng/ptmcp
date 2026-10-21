import pathlib

# 1) build(): always enter enable+config before the spec's CLI lines
p = pathlib.Path("ptmcp/pt.py"); s = p.read_text(encoding="utf-8")
old = '''try {{ d.enterCommand("!", "global"); }} catch (e) {{}}
var cmds = [{arr}];'''
new = '''try {{ d.enterCommand("enable", ""); d.enterCommand("configure terminal", ""); }} catch (e) {{}}
var cmds = [{arr}];'''
assert old in s
p.write_text(s.replace(old, new), encoding="utf-8")

# 2) ops.batch cli op: same hardening
p = pathlib.Path("ptmcp/ops.py"); s = p.read_text(encoding="utf-8")
old2 = '''  try {{ d.enterCommand("!", "global"); }} catch (e) {{}}
  var c = [{arr}];'''
new2 = '''  try {{ d.enterCommand("enable", ""); d.enterCommand("configure terminal", ""); }} catch (e) {{}}
  var c = [{arr}];'''
assert old2 in s
p.write_text(s.replace(old2, new2), encoding="utf-8")

# 3) term.run(): allow a "config" convenience
import ast
for f in ("ptmcp/pt.py", "ptmcp/ops.py"):
    ast.parse(pathlib.Path(f).read_text(encoding="utf-8"))
print("CLI now always enters enable+config first")
