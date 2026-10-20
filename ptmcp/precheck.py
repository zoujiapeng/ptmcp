"""ptmcp.precheck - validate a topology spec BEFORE touching the canvas.

Every failure mode we hit by hand in earlier rounds is checked here first:

  * unknown model                -> catalog.device_type raises
  * duplicate device name        -> PT renames silently, later lookups miss
  * port that does not exist     -> createLink returns false, link missing
  * port already carrying a link -> createLink returns false, silent
  * switch<->switch on a straight-through cable -> both ports stay DOWN (red)
  * two devices on the same spot -> overlapping icons, manual cleanup

`precheck(spec, fix=True)` repairs what can be repaired deterministically:
it picks the correct cable and moves a link to the next free port on the same
device, so an agent can hand over a rough spec and still get a green topology.
"""
from __future__ import annotations

import json

from . import bridge
from .catalog import cable_id, device_type
from .pt import _prelude

# up to this many ports are scanned for a free replacement
_SCAN = 48


def _ports_state(names: list[str]) -> dict[str, dict[str, bool]]:
    """{device: {port: occupied}} for the given devices (one round-trip)."""
    arr = ", ".join(bridge.q(n) for n in names)
    js = _prelude() + f"""
var out = [];
var names = [{arr}];
for (var i = 0; i < names.length; i++) {{
  var d = ipc.network().getDevice(names[i]);
  if (!d) {{ out.push(names[i] + "~~MISSING"); continue; }}
  var ports = [];
  try {{ ports = d.getPorts(); }} catch (e) {{ out.push(names[i] + "~~ERR"); continue; }}
  for (var p = 0; p < ports.length; p++) {{
    var po = d.getPort(ports[p]);
    var busy = 0;
    try {{ busy = po.getLink() ? 1 : 0; }} catch (e) {{ busy = -1; }}
    out.push(names[i] + "~" + ports[p] + "~" + busy);
  }}
}}
throw new Error(out.join(";"));
"""
    state: dict[str, dict[str, bool]] = {}
    for chunk in (bridge.ask(js, timeout=30) or "").split(";"):
        parts = chunk.split("~")
        if len(parts) == 3 and parts[1] != "":
            state.setdefault(parts[0], {})[parts[1]] = parts[2] == "1"
    return state


def precheck(spec: dict, fix: bool = False, live: bool = True) -> dict:
    issues: list[dict] = []
    patched = json.loads(json.dumps(spec))          # deep copy

    # ---- static checks (no PT round-trip) --------------------------------
    names: set[str] = set()
    types: dict[str, int] = {}
    for dev in patched.get("devices", []):
        name = dev.get("name", "")
        if not name:
            issues.append({"level": "error", "code": "no-name", "device": dev,
                           "fix": "give the device a name"})
            continue
        if name in names:
            issues.append({"level": "error", "code": "dup-name", "device": name,
                           "fix": "PT silently renames duplicates"})
        names.add(name)
        try:
            types[name] = device_type(dev["model"])
        except ValueError as exc:
            issues.append({"level": "error", "code": "bad-model", "device": name,
                           "message": str(exc)})

    spots: dict[tuple[int, int], str] = {}
    for dev in patched.get("devices", []):
        key = (int(dev.get("x", 200)), int(dev.get("y", 200)))
        if key in spots:
            issues.append({"level": "warn", "code": "overlap",
                           "message": f'{spots[key]} and {dev.get("name")} share {key}'})
        spots[key] = str(dev.get("name"))

    # ---- live checks (one round-trip) -----------------------------------
    live = _ports_state(sorted(names)) if (names and live) else {}
    for link in patched.get("links", []):
        a, ap, b, bp = link["a"], link["a_port"], link["b"], link["b_port"]
        for dev, port in ((a, ap), (b, bp)):
            if not live or dev not in types:
                continue
            ports = live.get(dev)
            if ports is None:
                issues.append({"level": "error", "code": "no-device", "device": dev,
                               "message": f"{dev} is not on the canvas"})
                continue
            if port not in ports:
                free = _first_free(ports, port)
                issues.append({"level": "error", "code": "no-port", "device": dev,
                               "port": port,
                               "message": f"{dev} has no port {port}",
                               "suggest": free})
            elif ports[port]:
                free = _first_free(ports, port)
                issues.append({"level": "error", "code": "port-busy", "device": dev,
                               "port": port,
                               "message": f"{dev}:{port} already has a link",
                               "suggest": free})
        if a in types and b in types:
            want = cable_id(None, types[a], types[b])
            got = link.get("cable")
            got_id = cable_id(got, types[a], types[b]) if got else want
            if got_id != want:
                issues.append({"level": "error", "code": "bad-cable",
                               "link": f"{a}:{ap}-{b}:{bp}",
                               "message": f"cable {got} would leave the link red; "
                                          f"need {'cross' if want == 8101 else 'straight'}",
                               "fix": {"cable": "cross" if want == 8101 else "straight"}})

    # ---- apply the deterministic fixes ----------------------------------
    if fix:
        # Reserve ports already used by *this* spec so two repairs never land on
        # the same port (that would trade one silent failure for another).
        reserved: dict[str, set[str]] = {d: set() for d in types}
        for link in patched.get("links", []):
            reserved.setdefault(link["a"], set()).add(link["a_port"])
            reserved.setdefault(link["b"], set()).add(link["b_port"])

        for link in patched.get("links", []):
            a, b = link["a"], link["b"]
            if a in types and b in types:
                want = cable_id(None, types[a], types[b])
                link["cable"] = "cross" if want == 8101 else "straight"
            for side, key, dev in (("a", "a_port", a), ("b", "b_port", b)):
                ports = live.get(dev) or {}
                port = link[key]
                if port in ports and not ports[port]:
                    continue                       # exists and free: keep it
                replacement = _next_free(ports, reserved.setdefault(dev, set()))
                if replacement:
                    reserved[dev].discard(port)
                    reserved[dev].add(replacement)
                    link[key] = replacement

    errors = [i for i in issues if i["level"] == "error"]
    result = {
        "ok": not errors,
        "errors": len(errors),
        "warnings": len(issues) - len(errors),
        "issues": issues,
        "patched_spec": patched if fix else None,
    }
    if fix:
        after = precheck(patched, fix=False)          # what is STILL wrong
        result["issues_before_fix"] = len(issues)
        result["issues"] = after["issues"]
        result["ok"] = after["ok"]
        result["errors"] = after["errors"]
        result["warnings"] = after["warnings"]
    return result


def _first_free(ports: dict[str, bool], avoid: str) -> str | None:
    """Next free access-ish port on the same device, skipping the one asked for."""
    for name, busy in list(ports.items())[:_SCAN]:
        if name == avoid or busy:
            continue
        if "Vlan" in name:
            continue
        return name
    return None

def _next_free(ports: dict[str, bool], reserved: set[str]) -> str | None:
    """First port that is free on the device and not reserved by another link."""
    for name, busy in list(ports.items())[:_SCAN]:
        if busy or name in reserved or "Vlan" in name:
            continue
        return name
    return None


