"""ptmcp.ops - device-level operations and one-round-trip batch execution."""
from __future__ import annotations

import json

from . import bridge
from .pt import _prelude


def _call(js_body: str, timeout: float = 30.0) -> str:
    return bridge.ask(_prelude() + js_body, timeout=timeout)


def power(name: str, on: bool) -> str:
    """Power a device on/off (simulates the physical power switch)."""
    return _call(f"""
var d = ipc.network().getDevice({bridge.q(name)});
if (!d) throw new Error("no device " + {bridge.q(name)});
d.setPower({"true" if on else "false"});
throw new Error({bridge.q(name)} + " power=" + d.getPower());
""")


def rename(old: str, new: str) -> str:
    return _call(f"""
var d = ipc.network().getDevice({bridge.q(old)});
if (!d) throw new Error("no device " + {bridge.q(old)});
d.setName({bridge.q(new)});
try {{ d.setHostName({bridge.q(new)}); }} catch (e) {{}}
throw new Error({bridge.q(old)} + " -> " + d.getName());
""")


def move(name: str, x: int, y: int) -> str:
    return _call(f"""
var d = ipc.network().getDevice({bridge.q(name)});
if (!d) throw new Error("no device " + {bridge.q(name)});
d.moveToLocation({int(x)}, {int(y)});
throw new Error({bridge.q(name)} + " moved to {int(x)},{int(y)}");
""")


def add_module(name: str, slot: int, model: str) -> str:
    """Insert a hardware module (e.g. HWIC-2T into slot 0) - needs the device off."""
    return _call(f"""
var d = ipc.network().getDevice({bridge.q(name)});
if (!d) throw new Error("no device " + {bridge.q(name)});
var was = d.getPower();
d.setPower(false);
var ok = d.addModule({int(slot)}, {bridge.q(model)});
if (was) {{ d.setPower(true); try {{ d.skipBoot(); }} catch (e) {{}} }}
throw new Error({bridge.q(name)} + " addModule({int(slot)},{bridge.q(model)}) = " + ok);
""")


def remove(name: str) -> str:
    """Remove a device from the canvas (no modal: we do not pass confirm flags)."""
    return _call(f"""
var d = ipc.network().getDevice({bridge.q(name)});
if (!d) throw new Error("no device " + {bridge.q(name)});
var lw = ipc.appWindow().getActiveWorkspace().getLogicalWorkspace();
lw.removeDevice({bridge.q(name)});
throw new Error("removed " + {bridge.q(name)});
""", timeout=20)


def batch(ops: list[dict]) -> dict:
    """Run many operations in ONE bridge round-trip.

    ops = [{"op": "cli", "device": "S1", "commands": ["vlan 2", "exit"]},
           {"op": "ip",  "device": "PC1", "port": "FastEthernet0", "ip": "...", "mask": "..."},
           {"op": "power", "device": "R1", "on": True},
           {"op": "rename", "device": "S1", "to": "CORE"},
           {"op": "module", "device": "R1", "slot": 0, "model": "HWIC-2T"},
           {"op": "port", "device": "S1", "port": "FastEthernet0/1",
            "access_vlan": 20, "mode": 1, "native_vlan": 1}]
    """
    js: list[str] = ["var log=[];"]
    for op in ops:
        kind = op.get("op")
        dev = op.get("device", "")
        if kind == "cli":
            arr = ", ".join(bridge.q(c) for c in op.get("commands", []))
            js.append(f"""
(function() {{
  var d = ipc.network().getDevice({bridge.q(dev)});
  if (!d) {{ log.push("cli {dev}: no device"); return; }}
  try {{ d.enterCommand("!", "global"); }} catch (e) {{}}
  var c = [{arr}];
  for (var i = 0; i < c.length; i++) {{ try {{ d.enterCommand(c[i], ""); }} catch (e) {{ log.push("cli ERR " + c[i]); }} }}
  log.push("cli {dev}: " + c.length);
}})();""")
        elif kind == "ip":
            js.append(f"""
(function() {{
  var d = ipc.network().getDevice({bridge.q(dev)});
  var p = d && d.getPort({bridge.q(op.get('port', 'FastEthernet0'))});
  if (!p) {{ log.push("ip {dev}: no port"); return; }}
  p.setIpSubnetMask({bridge.q(op.get('ip', ''))}, {bridge.q(op.get('mask', '255.255.255.0'))});
  if ({bridge.q(op.get('gateway', ''))}) p.setDefaultGateway({bridge.q(op.get('gateway', ''))});
  log.push("ip {dev}={op.get('ip','')}");
}})();""")
        elif kind == "port":
            js.append(f"""
(function() {{
  var d = ipc.network().getDevice({bridge.q(dev)});
  var p = d && d.getPort({bridge.q(op.get('port', ''))});
  if (!p) {{ log.push("port {dev}: no port"); return; }}
  if ({int(op.get('mode', -1))} >= 0) p.setAdminOpMode({int(op.get('mode', -1))});
  if ({int(op.get('access_vlan', -1))} >= 0) {{ p.setAccessPort(true); p.setAccessVlan({int(op.get('access_vlan', -1))}); }}
  if ({int(op.get('native_vlan', -1))} > 0) p.setNativeVlanId({int(op.get('native_vlan', -1))});
  log.push("port {dev}:{op.get('port','')} mode=" + p.getAdminOpMode() + " vlan=" + p.getAccessVlan());
}})();""")
        elif kind == "power":
            js.append(f"""
(function() {{
  var d = ipc.network().getDevice({bridge.q(dev)});
  if (!d) {{ log.push("power {dev}: no device"); return; }}
  d.setPower({"true" if op.get("on", True) else "false"});
  log.push("power {dev}=" + d.getPower());
}})();""")
        elif kind == "rename":
            js.append(f"""
(function() {{
  var d = ipc.network().getDevice({bridge.q(dev)});
  if (!d) {{ log.push("rename {dev}: no device"); return; }}
  d.setName({bridge.q(op.get('to', dev))});
  log.push("rename {dev} -> {op.get('to', dev)}");
}})();""")
        elif kind == "module":
            js.append(f"""
(function() {{
  var d = ipc.network().getDevice({bridge.q(dev)});
  if (!d) {{ log.push("module {dev}: no device"); return; }}
  var was = d.getPower(); d.setPower(false);
  var ok = d.addModule({int(op.get('slot', 0))}, {bridge.q(op.get('model', ''))});
  if (was) {{ d.setPower(true); try {{ d.skipBoot(); }} catch (e) {{}} }}
  log.push("module {dev} slot{int(op.get('slot', 0))}=" + ok);
}})();""")
        else:
            js.append(f'log.push("unknown op {kind}");')
    js.append('throw new Error(log.join(" | "));')
    return {"result": _call("\n".join(js), timeout=90)}
