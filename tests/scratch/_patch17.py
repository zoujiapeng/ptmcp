import pathlib
p = pathlib.Path("ptmcp/pt.py"); s = p.read_text(encoding="utf-8")

# new gate: the device CLI shell must answer with a prompt before we send config
addition = '''def wait_cli_ready(names: list[str], timeout: float = 90.0, interval: float = 2.0) -> dict:
    """Wait until each device's CLI shell reports a prompt.

    `enterCommand` is a silent no-op while the device's console app has not
    started (getPrompt() returns ""), which is what made cold-start config vanish
    even though isBooting() was already false.
    """
    arr = ", ".join(q(n) for n in names)
    js = _prelude() + f"""
var names = [{arr}];
var pending = [];
for (var i = 0; i < names.length; i++) {{
  var d = ipc.network().getDevice(names[i]);
  if (!d) {{ pending.push(names[i] + ":missing"); continue; }}
  var pr = "";
  try {{ pr = d.getIpcTerminalLine().getPrompt(); }} catch (e) {{ pr = ""; }}
  if (!pr) pending.push(names[i]);
}}
throw new Error(pending.join(","));
"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        pending = (ask(js, timeout=20) or "").strip()
        if not pending:
            return {"ready": True}
        time.sleep(interval)
    return {"ready": False, "no_prompt": pending.split(",")}


'''
s = s.replace("def wait_ready(", addition + "def wait_ready(", 1)
s = s.replace('''        report["ready"] = wait_ready(sorted(spec["cli"]))''',
'''        report["ready"] = wait_ready(sorted(spec["cli"]))
        report["cli_ready"] = wait_cli_ready(sorted(spec["cli"]))''')
p.write_text(s, encoding="utf-8")
import ast; ast.parse(p.read_text(encoding="utf-8"))
print("added wait_cli_ready gate")
