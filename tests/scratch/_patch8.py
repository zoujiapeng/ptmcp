import pathlib
p = pathlib.Path("ptmcp/pt.py"); s = p.read_text(encoding="utf-8")

# 1) add wait_ready() next to wait_links_up
anchor = "def wait_links_up("
addition = '''def wait_ready(names: list[str], timeout: float = 45.0, interval: float = 2.0) -> dict:
    """Block until every device has finished booting (CLI is dropped before that).

    Cold-start runs showed `vlan 10 / name USERS` silently vanishing when the
    switch was still booting; this gate is what makes CLI reliable.
    """
    arr = ", ".join(q(n) for n in names)
    js = _prelude() + f"""
var names = [{arr}];
var busy = [];
for (var i = 0; i < names.length; i++) {{
  var d = ipc.network().getDevice(names[i]);
  if (!d) {{ busy.push(names[i] + ":missing"); continue; }}
  var b = false;
  try {{ b = (typeof d.isBooting === "function") ? d.isBooting() : false; }} catch (e) {{ b = false; }}
  if (b) busy.push(names[i]);
}}
throw new Error(busy.join(","));
"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        busy = (ask(js, timeout=20) or "").strip()
        if not busy:
            return {"ready": True, "waited": round(timeout - (deadline - time.time()), 1)}
        time.sleep(interval)
    return {"ready": False, "still_booting": busy.split(",")}


'''
s = s.replace(anchor, addition + anchor, 1)

# 2) build(): split the CLI phase out so it runs after boot
old_cli = '''    for dev, cmds in (spec.get("cli") or {}).items():
        arr = ", ".join(q(c) for c in cmds)
        lines.append(f"""
(function() {{
  var d = ipc.network().getDevice({q(dev)});
  if (!d) {{ log.push("FAIL cli {dev}"); return; }}
  try {{ d.enterCommand("!", "global"); }} catch (e) {{}}
  var cmds = [{arr}];
  for (var i = 0; i < cmds.length; i++) {{
    try {{ d.enterCommand(cmds[i], ""); }} catch (e) {{ log.push("cli ERR " + cmds[i]); }}
  }}
  log.push("cli {dev}: " + cmds.length + " cmds");
}})();""")

'''
assert old_cli in s
s = s.replace(old_cli, "")

old_tail = '''    lines.append("""
(function() {
  var n = ipc.network();
  log.push("devices=" + n.getDeviceCount() + " links=" + n.getLinkCount());
})();""")
    lines.append('throw new Error(log.join(" | "));')'''
new_tail = '''    lines.append("""
(function() {
  var n = ipc.network();
  log.push("devices=" + n.getDeviceCount() + " links=" + n.getLinkCount());
})();""")
    lines.append('throw new Error(log.join(" | "));')'''
s = s.replace(old_tail, new_tail)

# insert CLI phase after the build payload is sent
old_report = '''    report = {
        "precheck": {"ok": pre["ok"], "errors": pre["errors"], "warnings": pre["warnings"],
                     "issues": pre["issues"][:8]},
        "build": ask("\\n".join(lines), timeout=float(spec.get("timeout", 90))),
    }'''
new_report = '''    report = {
        "precheck": {"ok": pre["ok"], "errors": pre["errors"], "warnings": pre["warnings"],
                     "issues": pre["issues"][:8]},
        "build": ask("\\n".join(lines), timeout=float(spec.get("timeout", 90))),
    }

    # CLI must wait for boot, otherwise config is silently dropped (cold start).
    if spec.get("cli"):
        report["ready"] = wait_ready(sorted(spec["cli"]))
        cli_log = []
        for dev, cmds in spec["cli"].items():
            arr = ", ".join(q(c) for c in cmds)
            cli_log.append(ask(f"""
var d = ipc.network().getDevice({q(dev)});
if (!d) throw new Error("cli {dev}: no device");
try {{ d.enterCommand("!", "global"); }} catch (e) {{}}
var cmds = [{arr}];
for (var i = 0; i < cmds.length; i++) {{ try {{ d.enterCommand(cmds[i], ""); }} catch (e) {{}} }}
throw new Error("cli {dev}: " + cmds.length + " cmds");
""", timeout=60))
        report["cli"] = cli_log
        report["ready_after_cli"] = wait_ready(sorted(spec["cli"]), timeout=15)'''
assert old_report in s
s = s.replace(old_report, new_report)
p.write_text(s, encoding="utf-8")
print("build() now gates CLI on boot")
