"""ptmcp.state - read device state back out of Packet Tracer.

PT's IPC never exposes the terminal screen, but every device can serialise its
own state: `device.serializeToXml()` returns the engine XML, which contains

    <LINE>  ... </LINE>          the full running-config, one line per tag
    <VLANS><VLAN number name/>   the VLAN database
    <VTP><MODE><DOMAIN_NAME>     VTP status
    <PORT><MACADDRESS>...        per-port hardware state

so `show()` here is the scripting equivalent of `show running-config`,
`show vlan` and `show vtp status` - machine-readable instead of screen text.
"""
from __future__ import annotations

import re

from . import bridge
from .pt import _prelude

_XML_JS = """
var d = ipc.network().getDevice(%s);
if (!d) throw new Error("no device");
throw new Error("<<XML>>" + d.serializeToXml() + "<<END>>");
"""

_VTP_MODES = {"0": "server", "1": "client", "2": "transparent", "3": "off"}


def device_xml(name: str, timeout: float = 40.0) -> str:
    raw = bridge.ask(_prelude() + _XML_JS % bridge.q(name), timeout=timeout)
    if "<<XML>>" not in raw:
        raise RuntimeError(f"unexpected answer for {name}: {raw[:200]}")
    return raw.split("<<XML>>", 1)[1].split("<<END>>", 1)[0]


def running_config(name: str) -> str:
    """`show running-config` equivalent."""
    xml = device_xml(name)
    lines = re.findall(r"<LINE>(.*?)</LINE>", xml, re.S)
    return "\n".join(line.strip() for line in lines)


def vlans(name: str) -> list[dict]:
    """`show vlan` equivalent: [{id, name}]."""
    xml = device_xml(name)
    m = re.search(r"<VLANS>(.*?)</VLANS>", xml, re.S)
    if not m:
        return []
    return [{"id": int(v), "name": nm}
            for v, nm in re.findall(r'<VLAN number="(\d+)"[^>]*name="([^"]*)"', m.group(1))]


def vtp(name: str) -> dict:
    """`show vtp status` equivalent."""
    xml = device_xml(name)
    m = re.search(r"<VTP>(.*?)</VTP>", xml, re.S)
    if not m:
        return {}
    body = m.group(1)

    def tag(t: str) -> str:
        mm = re.search(rf"<{t}>(.*?)</{t}>", body, re.S)
        return mm.group(1).strip() if mm else ""

    mode = tag("MODE")
    return {
        "mode": _VTP_MODES.get(mode, mode),
        "domain": tag("DOMAIN_NAME"),
        "password": tag("PASSWORD"),
        "version": tag("VERSION"),
        "revision": tag("CONFIG_REVISION"),
    }


def mac_table(name: str) -> list[dict]:
    """Port + MAC pairs (the closest thing to `show mac address-table`)."""
    xml = device_xml(name)
    macs = re.findall(r"<MACADDRESS>([0-9A-Fa-f.]*)</MACADDRESS>", xml)
    return [{"index": i, "mac": mac} for i, mac in enumerate(macs) if mac]


def interfaces(name: str) -> list[dict]:
    """Live per-port state (up/protocol/duplex) straight from the IPC objects."""
    js = _prelude() + f"""
var d = ipc.network().getDevice({bridge.q(name)});
if (!d) throw new Error("no device");
var out = [];
var ports = d.getPorts();
for (var i = 0; i < ports.length; i++) {{
  var p = d.getPort(ports[i]);
  out.push([ports[i], p.isPortUp() ? 1 : 0, p.isProtocolUp() ? 1 : 0,
            p.getAdminOpMode ? p.getAdminOpMode() : -1,
            p.getAccessVlan ? p.getAccessVlan() : -1,
            p.getNativeVlanId ? p.getNativeVlanId() : -1,
            p.isFullDuplex ? (p.isFullDuplex() ? 1 : 0) : -1].join("~"));
}}
throw new Error(out.join(";"));
"""
    rows = []
    for chunk in (bridge.ask(js) or "").split(";"):
        f = chunk.split("~")
        if len(f) != 7:
            continue
        rows.append({
            "port": f[0], "up": f[1] == "1", "protocol": f[2] == "1",
            "admin_mode": int(f[3]), "access_vlan": int(f[4]),
            "native_vlan": int(f[5]), "full_duplex": f[6] == "1",
        })
    return rows


def show(name: str, what: str = "run") -> object:
    what = (what or "run").lower()
    if what in ("run", "running", "running-config", "config"):
        return running_config(name)
    if what in ("vlan", "vlans"):
        return vlans(name)
    if what in ("vtp",):
        return vtp(name)
    if what in ("mac", "mac-table", "macs"):
        return mac_table(name)
    if what in ("int", "interface", "interfaces", "ports"):
        return interfaces(name)
    raise ValueError("what must be one of: run, vlan, vtp, mac, interfaces")

def routing(name: str) -> dict:
    """Routing *configuration* (what is configured, not what is learned).

    PT's engine XML carries the running-config but not the live routing table or
    OSPF neighbour state, so this reports the configured blocks and static routes
    - use `pt_ping`/`pt_verify_l2` for reachability, and a real CLI window for
    `show ip route` / `show ip ospf neighbor`.
    """
    cfg = running_config(name)
    out = {"protocols": [], "static_routes": [], "interfaces": []}
    current = None
    for raw in cfg.splitlines():
        line = raw.strip()
        low = line.lower()
        if low.startswith("router "):
            current = {"proto": line[7:].strip(), "lines": []}
            out["protocols"].append(current)
        elif low.startswith("ip route "):
            out["static_routes"].append(line[9:].strip())
        elif low.startswith("ip address "):
            out["interfaces"].append(line[11:].strip())
        elif current is not None:
            if line in ("!", "") or low.startswith("interface ") or low.startswith("line "):
                current = None
            else:
                current["lines"].append(line)
    return out
