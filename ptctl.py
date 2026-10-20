#!/usr/bin/env python
"""ptctl.py - background control of Cisco Packet Tracer 8.x from Python.

Transport: the file-bridge mailbox the MCP-BUILDER extension polls
    %LOCALAPPDATA%\\packet-tracer-mcp\\bridge\\req_<id>.js  -> executed in PT
    %LOCALAPPDATA%\\packet-tracer-mcp\\bridge\\res_<id>.txt  <- result

Everything runs inside Packet Tracer's own Script Engine (Qt5Script) through its
native IPC API, so PT never needs to be focused, raised or even visible:

    lw = ipc.appWindow().getActiveWorkspace().getLogicalWorkspace()
    name = lw.addDevice(typeInt, model, x, y)      # returns the auto name
    ipc.network().getDevice(name).setName("R1")
    lw.createLink("R1", "GigabitEthernet0/0", "SW1", "GigabitEthernet0/1", 8100)
    ipc.appWindow().fileSaveAs("C:\\\\pt\\\\lab.pkt")

Device types (PT internal ids) and cable ids are taken from PT's own catalogs.

CLI:
    python ptctl.py status
    python ptctl.py build spec.json [--save C:\\pt\\x.pkt]
    python ptctl.py save  C:\\pt\\x.pkt
    python ptctl.py js "return ipc.network().getDeviceCount();"
    python ptctl.py shot  out.png          # canvas PNG (needs PT window alive)
    python ptctl.py new                    # File > New (discards current canvas)

Result channel note: the engine returns text only through a thrown Error
(`PT_ERROR: Error: <text>`), so every helper ends with `throw new Error(...)`.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------- transport

DEVICE_TYPES = {
    "2911": 0, "2901": 0, "2811": 0, "1941": 0, "1841": 0, "2620XM": 0,
    "2621XM": 0, "ISR4321": 0, "ISR4331": 0, "819HGW": 0, "819HG-4G-IOX": 0,
    "829": 0, "CGR1240": 0, "Router-PT": 0, "Router-PT-Empty": 0,
    "2960-24TT": 1, "2950-24": 1, "2950T-24": 1, "Switch-PT": 1,
    "Switch-PT-Empty": 1,
    "3560-24PS": 16, "3650-24PS": 16, "IE-2000": 16,
    "Cloud-PT": 2, "Bridge-PT": 3, "Hub-PT": 4, "Repeater-PT": 5,
    "AccessPoint-PT": 7, "AccessPoint-PT-A": 7, "AccessPoint-PT-AC": 7,
    "AccessPoint-PT-N": 7,
    "PC-PT": 8, "Server-PT": 9, "Printer-PT": 10, "Laptop-PT": 17,
    "TabletPC-PT": 18, "SMARTPHONE-PT": 20, "TV-PT": 22,
    "WLC-2504": 41, "WLC-3504": 41, "3702i": 44, "LAP-PT": 44,
}

CABLES = {
    "straight": 8100, "ethernet-straight": 8100,
    "cross": 8101, "crossover": 8101, "ethernet-cross": 8101,
    "roll": 8102, "fiber": 8103, "phone": 8104, "cable": 8105,
    "serial": 8106, "auto": 8107, "console": 8108, "wireless": 8109,
    "coaxial": 8110, "octal": 8111, "cellular": 8112, "usb": 8113,
}


def mailbox() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    root = Path(base) / "packet-tracer-mcp" if base else Path.home() / ".packet-tracer-mcp"
    d = root / "bridge"
    d.mkdir(parents=True, exist_ok=True)
    return d


def pt_alive(window: float = 8.0) -> bool:
    try:
        return (time.time() - (mailbox() / "alive.txt").stat().st_mtime) < window
    except OSError:
        return False


def run_js(js: str, timeout: float = 15.0) -> str:
    """Execute JS in PT's script engine and return the textual result."""
    d = mailbox()
    stamp = f"{os.getpid()}_{int(time.time() * 1000) % 10**7:07d}"
    req, res = d / f"req_{stamp}.js", d / f"res_{stamp}.txt"
    tmp = req.with_suffix(".js.tmp")
    tmp.write_bytes(js.encode("utf-8"))
    os.replace(tmp, req)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if res.exists():
            body = res.read_text(encoding="utf-8", errors="replace")
            res.unlink(missing_ok=True)
            return body.strip()
        time.sleep(0.08)
    res.unlink(missing_ok=True)
    raise TimeoutError(
        "no result from Packet Tracer. Is PT open and the MCP BUILDER module "
        "started (Extensions > Scripting > Configure PT Script Modules)?"
    )


def _unwrap(raw: str) -> str:
    for prefix in ("PT_ERROR: Error: ", "PT_ERROR: "):
        if raw.startswith(prefix):
            return raw[len(prefix):]
    return raw


def ask(js_body: str, timeout: float = 15.0) -> str:
    """Run a JS body that must end with `throw new Error(<text>)`."""
    return _unwrap(run_js(js_body, timeout=timeout))


def _q(text: str) -> str:
    return json.dumps(text)


# ---------------------------------------------------------------- operations


def status() -> str:
    js = """
var out = [];
var n = ipc.network();
for (var i = 0; i < n.getDeviceCount(); i++) {
  var d = n.getDeviceAt(i);
  out.push(d.getName() + " [" + d.getType() + "]");
}
throw new Error("devices=" + n.getDeviceCount() + " links=" + n.getLinkCount() +
                " :: " + out.join(", "));
"""
    return ask(js)


def save(path: str) -> str:
    win_path = path.replace("/", "\\\\")
    js = f"""
var ok = ipc.appWindow().fileSaveAs({_q(win_path)});
throw new Error("fileSaveAs(" + {_q(path)} + ") => " + ok);
"""
    return ask(js, timeout=25)


def new_canvas() -> str:
    js = """
try { ipc.appWindow().fileNew(); } catch (e) { throw new Error("fileNew ERR: " + e); }
throw new Error("new canvas requested");
"""
    return ask(js)


def screenshot(path: str) -> str:
    """Capture the logical workspace image through PT itself."""
    win_path = path.replace("/", "\\\\")
    js = f"""
var lw = ipc.appWindow().getActiveWorkspace().getLogicalWorkspace();
var img = lw.getWorkspaceImage();
var ok = false;
try {{ ok = img.save({_q(win_path)}); }} catch (e) {{ throw new Error("save ERR: " + e); }}
throw new Error("workspace image saved=" + ok + " -> " + {_q(path)});
"""
    return ask(js, timeout=25)


def build(spec: dict, save_to: str | None = None) -> str:
    """Create devices, links and IP settings from a JSON spec."""
    lines: list[str] = ["var log = [];", "var lw = ipc.appWindow().getActiveWorkspace().getLogicalWorkspace();"]

    for dev in spec.get("devices", []):
        name, model = dev["name"], dev["model"]
        x, y = int(dev.get("x", 200)), int(dev.get("y", 200))
        if model not in DEVICE_TYPES:
            raise ValueError(f"unknown model {model!r}; known: {sorted(set(DEVICE_TYPES))[:12]}...")
        t = DEVICE_TYPES[model]
        lines.append(f"""
(function() {{
  var orig = lw.addDevice({t}, {_q(model)}, {x}, {y});
  if (!orig) {{ log.push("FAIL add {name}"); return; }}
  var d = ipc.network().getDevice(orig);
  d.setName({_q(name)});
  try {{ if ({t} <= 1 || {t} === 16) d.skipBoot(); }} catch (e) {{}}
  log.push("add {name}(" + {_q(model)} + ") as " + orig);
}})();""")

    for ln in spec.get("links", []):
        cable = CABLES.get(str(ln.get("cable", "straight")).lower())
        if cable is None:
            raise ValueError(f"unknown cable {ln.get('cable')!r}")
        lines.append(f"""
(function() {{
  var ok = lw.createLink({_q(ln['a'])}, {_q(ln['a_port'])}, {_q(ln['b'])}, {_q(ln['b_port'])}, {cable});
  log.push("link {ln['a']}:{ln['a_port']} <-> {ln['b']}:{ln['b_port']} => " + ok);
}})();""")

    for ip in spec.get("ips", []):
        lines.append(f"""
(function() {{
  var d = ipc.network().getDevice({_q(ip['device'])});
  if (!d) {{ log.push("FAIL ip: no {ip['device']}"); return; }}
  var p = d.getPort({_q(ip['port'])});
  if (!p) {{ log.push("FAIL ip: no port {ip['port']} on {ip['device']}"); return; }}
  try {{
    p.setIpSubnetMask({_q(ip['ip'])}, {_q(ip['mask'])});
    if ({_q(ip.get('gateway', ''))}) p.setDefaultGateway({_q(ip.get('gateway', ''))});
    log.push("ip {ip['device']}:{ip['port']}=" + {_q(ip['ip'])});
  }} catch (e) {{ log.push("ip ERR {ip['device']}: " + e); }}
}})();""")

    lines.append('log.push("devices=" + ipc.network().getDeviceCount() + " links=" + ipc.network().getLinkCount());')
    if save_to:
        p = save_to.replace("/", "\\\\")
        lines.append(f'log.push("save=" + ipc.appWindow().fileSaveAs({_q(p)}));')
    lines.append('throw new Error(log.join(" | "));')
    return ask("\n".join(lines), timeout=float(spec.get("timeout", 40)))


# ---------------------------------------------------------------- CLI


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    cmd = argv[0]

    if cmd == "status":
        if not pt_alive():
            print("NOT ALIVE: no heartbeat from PT script engine")
            return 1
        print(status())
        return 0

    if cmd == "build":
        spec = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        out = build(spec, save_to=argv[2] if len(argv) > 2 else spec.get("save"))
        print(out)
        return 0

    if cmd == "save":
        print(save(argv[1]))
        return 0

    if cmd == "js":
        code = Path(argv[1]).read_text(encoding="utf-8") if argv[1].endswith(".js") else argv[1]
        print(_unwrap(run_js(code, timeout=25)))
        return 0

    if cmd == "shot":
        print(screenshot(argv[1]))
        return 0

    if cmd == "new":
        print(new_canvas())
        return 0

    print(f"unknown command {cmd}")
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
