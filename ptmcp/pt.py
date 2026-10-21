"""ptmcp.pt - high-level, dialog-free control of a running Packet Tracer.

Every public function returns plain text/JSON so an agent can act on it.

Design notes (learned the hard way on PT 8.0.0.0212):
  * switch<->switch copper MUST be a crossover cable (8101); straight-through
    leaves both ports down and the canvas shows a red link.
  * fileSaveAs() on an existing path opens "Overwrite File?" which *blocks the
    script engine*; save() therefore writes to a fresh temp name and renames.
  * fileNew() prompts to save; fileNew(false) does not.
  * removeDevice() can leave a modal behind; new canvas + rebuild is safer.
  * CLI text is read back through terminal.getCurrentHistory().history.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from . import bridge
from .bridge import ask, q
from .catalog import cable_id, device_type

# --------------------------------------------------------------------- helpers

_HISTORY = """
function __hist(dev) {
  try {
    var t = dev.getIpcTerminalLine();
    var h = t.getCurrentHistory();
    var lines = h && h.history ? h.history : null;
    if (!lines) return String(t.getCommandInput ? t.getCommandInput() : "");
    var s = [];
    for (var i = 0; i < lines.length; i++) s.push(String(lines[i]));
    return s.join("\\n");
  } catch (e) { return "[no-cli:" + e + "]"; }
}
"""


def _prelude() -> str:
    return "var log=[];var lw=ipc.appWindow().getActiveWorkspace().getLogicalWorkspace();" + _HISTORY


# ------------------------------------------------------------------ lifecycle


def status() -> dict:
    """Snapshot of the running PT instance (no GUI touched)."""
    js = _prelude() + """
var n = ipc.network();
var devs = [];
for (var i = 0; i < n.getDeviceCount(); i++) {
  var d = n.getDeviceAt(i);
  devs.push({name: d.getName(), type: d.getType(), model: (d.getModel ? d.getModel() : "")});
}
throw new Error(JSON.stringify({devices: devs, links: n.getLinkCount()}));
"""
    raw = ask(js)
    data = json.loads(raw)
    data["alive"] = True
    return data


def new_canvas() -> str:
    """Fresh, empty workspace (fileNew(false): no 'save changes?' dialog)."""
    return ask("ipc.appWindow().fileNew(false); throw new Error('new canvas');")


def save(path: str) -> str:
    """Save the topology as .pkt without ever raising a dialog.

    PT prompts when the target exists, and that prompt freezes the script
    engine. So we always save to a path that does not exist, then rename.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()
    tmp = target.with_suffix(target.suffix + f".{int(time.time()*1000)}.tmp.pkt")
    js = f"throw new Error('save=' + ipc.appWindow().fileSaveAs({q(str(tmp))}));"
    res = ask(js, timeout=40)
    if not tmp.exists():
        return f"save FAILED ({res}); target {tmp} was not created"
    os.replace(tmp, target)
    return f"saved {target} ({target.stat().st_size} bytes)"


# --------------------------------------------------------------------- build


def build(spec: dict, new: bool = True, save_to: str | None = None) -> dict:
    """Create devices, links (auto cable), IPv4 addresses and CLI config.

    spec = {
      "devices": [{"name": "S1", "model": "2950T-24", "x": 200, "y": 150}, ...],
      "links":   [{"a": "S1", "a_port": "FastEthernet0/1",
                   "b": "PC0", "b_port": "FastEthernet0",
                   "cable": "auto"|"straight"|"cross"|...}, ...],
      "ips":     [{"device": "PC0", "port": "FastEthernet0",
                   "ip": "192.168.2.1", "mask": "255.255.255.0",
                   "gateway": "192.168.2.1"}, ...],
      "cli":     {"S1": ["vlan 2", "name VLAN2", "exit"], ...}
    }
    """
    from .precheck import precheck as _pre
    pre = _pre(spec, live=not new)
    types: dict[str, int] = {}
    for dev in spec.get("devices", []):
        types[dev["name"]] = device_type(dev["model"])
    for link in spec.get("links", []):
        for side, port in (("a", "a_port"), ("b", "b_port")):
            if link[side] not in types:
                raise ValueError(f"link references unknown device {link[side]!r}")

    # fileNew() invalidates every cached workspace handle, so it must run before
    # the prelude grabs `lw`.
    lines: list[str] = []
    if new:
        lines.append("ipc.appWindow().fileNew(false);")
    lines.append(_prelude())

    for dev in spec.get("devices", []):
        t = types[dev["name"]]
        x, y = int(dev.get("x", 200)), int(dev.get("y", 200))
        lines.append(f"""
(function() {{
  var orig = lw.addDevice({t}, {q(dev["model"])}, {x}, {y});
  if (!orig) {{ log.push("FAIL add " + {q(dev["name"])}); return; }}
  var d = ipc.network().getDevice(orig);
  d.setName({q(dev["name"])});
  if ({t} <= 1 || {t} === 16) {{ try {{ d.skipBoot(); }} catch (e) {{}} }}
  log.push("+" + {q(dev["name"])} + "(" + {q(dev["model"])} + ")");
}})();""")

    for link in spec.get("links", []):
        ta, tb = types[link["a"]], types[link["b"]]
        cid = cable_id(link.get("cable"), ta, tb)
        lines.append(f"""
(function() {{
  var ok = lw.createLink({q(link['a'])}, {q(link['a_port'])}, {q(link['b'])}, {q(link['b_port'])}, {cid});
  log.push("link {link['a']}:{link['a_port']}-{link['b']}:{link['b_port']} cable={cid} -> " + ok);
}})();""")

    for entry in spec.get("ips", []):
        gw = q(entry.get("gateway", ""))
        lines.append(f"""
(function() {{
  var d = ipc.network().getDevice({q(entry['device'])});
  var p = d && d.getPort({q(entry['port'])});
  if (!p) {{ log.push("FAIL ip {entry['device']}:{entry['port']}"); return; }}
  p.setIpSubnetMask({q(entry['ip'])}, {q(entry['mask'])});
  if ({gw}) p.setDefaultGateway({gw});
  log.push("ip {entry['device']}:{entry['port']}={entry['ip']}");
}})();""")

    lines.append("""
(function() {
  var n = ipc.network();
  log.push("devices=" + n.getDeviceCount() + " links=" + n.getLinkCount());
})();""")
    lines.append('throw new Error(log.join(" | "));')

    report = {
        "precheck": {"ok": pre["ok"], "errors": pre["errors"], "warnings": pre["warnings"],
                     "issues": pre["issues"][:8]},
        "build": ask("\n".join(lines), timeout=float(spec.get("timeout", 90))),
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
        report["ready_after_cli"] = wait_ready(sorted(spec["cli"]), timeout=15)
    failed = [seg.split(" -> ")[0].strip().strip("link ")
              for seg in report["build"].split("|") if seg.strip().endswith("-> false")]
    if failed:
        report["failed_links"] = failed
    if spec.get("links") and spec.get("wait", True):
        report["link_check"] = wait_links_up(spec)
    if spec.get("asserts"):
        from .asserts import check as _check
        try:
            report["asserts"] = _check(spec)
        except Exception as exc:                               # noqa: BLE001
            report["asserts"] = {"ok": None, "error": str(exc)}
    if save_to:
        report["save"] = save(save_to)
    return report


def wait_ready(names: list[str], timeout: float = 45.0, interval: float = 2.0) -> dict:
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


def wait_links_up(spec: dict, timeout: float = 45.0, interval: float = 3.0) -> dict:
    """Poll until every declared link's both ports report up (STP needs seconds)."""
    pairs = [(l["a"], l["a_port"], l["b"], l["b_port"]) for l in spec.get("links", [])]
    if not pairs:
        return {"up": True, "detail": "no links"}
    arr = ", ".join(f"['{a}','{ap}','{b}','{bp}']" for a, ap, b, bp in pairs)
    js = _prelude() + f"""
var __r;
try {{
var pairs = [{arr}];
var out = [];
var allUp = true;
for (var i = 0; i < pairs.length; i++) {{
  var d1 = ipc.network().getDevice(pairs[i][0]);
  var d2 = ipc.network().getDevice(pairs[i][2]);
  var p1 = d1 && d1.getPort(pairs[i][1]);
  var p2 = d2 && d2.getPort(pairs[i][3]);
  var u1 = !!(p1 && p1.isPortUp()), u2 = !!(p2 && p2.isPortUp());
  if (!u1 || !u2) allUp = false;
  out.push(pairs[i][0] + ":" + pairs[i][1] + "=" + (u1 ? "up" : "DOWN") + " " +
           pairs[i][2] + ":" + pairs[i][3] + "=" + (u2 ? "up" : "DOWN"));
}}
__r = JSON.stringify({{allUp: allUp, detail: out}});
}} catch (e) {{
  __r = JSON.stringify({{allUp: null, error: String(e)}});
}}
throw new Error(__r);
"""
    deadline = time.time() + timeout
    last = {"allUp": False, "detail": []}
    while time.time() < deadline:
        raw = ask(js, timeout=20)
        try:
            last = json.loads(raw)
        except json.JSONDecodeError:
            return {"allUp": None, "detail": [], "raw": raw[:400]}
        if last.get("allUp"):
            return last
        time.sleep(interval)
    return last


# ---------------------------------------------------------------- CLI & ping


def cli(device: str, commands: list[str], wait: float = 1.5) -> str:
    """Run IOS CLI lines on a device and return the terminal text."""
    arr = ", ".join(q(c) for c in commands)
    js = _prelude() + f"""
var d = ipc.network().getDevice({q(device)});
if (!d) throw new Error("no device " + {q(device)});
var cmds = [{arr}];
for (var i = 0; i < cmds.length; i++) {{ try {{ d.enterCommand(cmds[i], ""); }} catch (e) {{}} }}
throw new Error(__hist(d));
"""
    text = ask(js, timeout=30)
    time.sleep(wait)
    js2 = _prelude() + f"""
var d = ipc.network().getDevice({q(device)});
throw new Error(__hist(d));
"""
    return ask(js2, timeout=30) or text


def ping(source: str, target_ip: str, count: int = 4) -> dict:
    """Run `ping` inside the device's own CLI.

    PT's script API exposes no terminal *output* (getCurrentHistory() holds the
    command strings, not the screen), so this cannot parse "Reply from ...":
    it executes the ping the way a human would, leaving the transcript in the
    device's CLI, and reports what was executed. Use verify_l2() for a
    machine-checkable verdict on L2 reachability.
    """
    js = _prelude() + f"""
var d = ipc.network().getDevice({q(source)});
if (!d) throw new Error("no device " + {q(source)});
var has = (typeof d.enterCommand === "function");
var cmd = "ping {target_ip} repeat {count}";
var ok = false;
if (has) {{ try {{ ok = d.enterCommand(cmd, ""); }} catch (e) {{ throw new Error("enterCommand failed: " + e); }} }}
throw new Error(JSON.stringify({{has_cli: has, sent: ok, cmd: cmd}}));
"""
    meta = json.loads(ask(js, timeout=30))
    return {
        "source": source,
        "target": target_ip,
        "executed": bool(meta.get("sent")),
        "command": meta.get("cmd"),
        "note": (
            "ping is running in the device CLI - open that device to read "
            "'Reply from ...'; PT's IPC does not expose terminal output."
            if meta.get("sent") else
            "device has no CLI (PC/Laptop hosts are driven through their Desktop "
            "app, which has no script API) - use an IOS device as the source, or "
            "click the PC's Command Prompt manually."
        ),
    }


def verify_l2(spec: dict) -> dict:
    """Machine-checkable L2 verdict: link state + VLAN membership per link.

    For every declared link: both ports must be up, and for host links the
    switch port's access VLAN is reported. Hosts that share an access VLAN (or
    a trunk) can reach each other; hosts on different VLANs cannot - which is
    exactly what cases 27/28/29 teach.
    """
    ports = []
    for link in spec.get("links", []):
        ports.append((link["a"], link["a_port"], link["b"], link["b_port"]))
    arr = ", ".join(f"['{a}','{ap}','{b}','{bp}']" for a, ap, b, bp in ports)
    js = _prelude() + f"""
var out = [];
var pairs = [{arr}];
for (var i = 0; i < pairs.length; i++) {{
  var d1 = ipc.network().getDevice(pairs[i][0]);
  var d2 = ipc.network().getDevice(pairs[i][2]);
  var p1 = d1 && d1.getPort(pairs[i][1]);
  var p2 = d2 && d2.getPort(pairs[i][3]);
  out.push([pairs[i][0], pairs[i][1], (p1 && p1.isPortUp()) ? 1 : 0,
            p1 ? p1.getAdminOpMode() : -1, p1 ? p1.getAccessVlan() : -1,
            pairs[i][2], pairs[i][3], (p2 && p2.isPortUp()) ? 1 : 0,
            p2 ? p2.getAdminOpMode() : -1, p2 ? p2.getAccessVlan() : -1].join("~"));
}}
throw new Error(out.join(";"));
"""
    rows = []
    for chunk in (ask(js, timeout=30) or "").split(";"):
        f = chunk.split("~")
        if len(f) != 10:
            continue
        rows.append({
            "a": f"{f[0]}:{f[1]}", "a_up": f[2] == "1", "a_mode": int(f[3]), "a_vlan": int(f[4]),
            "b": f"{f[5]}:{f[6]}", "b_up": f[7] == "1", "b_mode": int(f[8]), "b_vlan": int(f[9]),
        })
    return {"links": rows}


