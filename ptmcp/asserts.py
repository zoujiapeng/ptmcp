"""ptmcp.asserts - declarative "is this lab actually correct?" checks.

`pt_verify_l2` reports raw state.  This module answers the question an agent
actually cares about: did the lab come out the way the task sheet demands?

Rules live in the spec under "asserts", e.g.

    "asserts": [
      {"link_up": "all"},
      {"access": {"device": "S1", "port": "FastEthernet0/1", "vlan": 2}},
      {"trunk":  {"device": "S1", "port": "FastEthernet0/13", "native": 1}},
      {"same_vlan": ["PC0", "PC2"]},          # must be able to talk
      {"diff_vlan": ["PC0", "PC1"]},          # must NOT be able to talk
      {"vlan_exists": {"device": "S1", "vlan": 3, "name": "VLAN3"}},
      {"vtp": {"device": "S2", "mode": "client", "domain": "VTP-TEST"}}
    ]

With no rules, a sensible default is derived from the spec (all links up, every
trunk consistent on both ends).  Every failure carries a concrete `fix` so the
agent can repair instead of guessing.

Reachability model: two hosts share a broadcast domain when the switch ports
they hang off sit in the same VLAN *and* their switches are joined by trunks
(both ends admin mode 2). This is an L2 model - it deliberately ignores STP
blocking, which PT does not expose.
"""
from __future__ import annotations

import json

from . import bridge
from .catalog import DEVICE_TYPES
from .pt import _prelude

HOST_TYPES = {8, 9, 10, 12, 17, 18, 19, 20, 22}
SWITCH_TYPES = {1, 16}


def _snapshot(spec: dict) -> dict:
    """One round-trip: link/port state for every device touched by the spec."""
    names = sorted({d["name"] for d in spec.get("devices", [])} |
                   {l["a"] for l in spec.get("links", [])} |
                   {l["b"] for l in spec.get("links", [])})
    arr = ", ".join(bridge.q(n) for n in names)
    js = _prelude() + f"""
var out = [];
var names = [{arr}];
for (var i = 0; i < names.length; i++) {{
  var d = ipc.network().getDevice(names[i]);
  if (!d) {{ out.push("D~" + names[i] + "~MISSING"); continue; }}
  out.push("D~" + names[i] + "~" + d.getType() + "~" + (d.getPower() ? 1 : 0));
  var ports = [];
  try {{ ports = d.getPorts(); }} catch (e) {{}}
  for (var p = 0; p < ports.length; p++) {{
    var po = d.getPort(ports[p]);
    var linked = null;
    try {{ var l = po.getLink(); linked = l ? 1 : 0; }} catch (e) {{ linked = -1; }}
    out.push("P~" + names[i] + "~" + ports[p] + "~" + (po.isPortUp() ? 1 : 0) +
             "~" + (po.isProtocolUp() ? 1 : 0) +
             "~" + (po.getAdminOpMode ? po.getAdminOpMode() : -1) +
             "~" + (po.getAccessVlan ? po.getAccessVlan() : -1) +
             "~" + (po.getNativeVlanId ? po.getNativeVlanId() : -1) +
             "~" + linked);
  }}
}}
throw new Error(out.join(";"));
"""
    devices: dict[str, dict] = {}
    ports: dict[str, dict[str, dict]] = {}
    for chunk in (bridge.ask(js, timeout=40) or "").split(";"):
        f = chunk.split("~")
        if f[0] == "D" and len(f) >= 3:
            devices[f[1]] = {"type": int(f[2]) if f[2] != "MISSING" else -1,
                             "missing": f[2] == "MISSING"}
        elif f[0] == "P" and len(f) == 9:
            ports.setdefault(f[1], {})[f[2]] = {
                "up": f[3] == "1", "proto": f[4] == "1", "mode": int(f[5]),
                "vlan": int(f[6]), "native": int(f[7]), "linked": f[8] == "1",
            }
    return {"devices": devices, "ports": ports}


def _host_vlan(spec: dict, snap: dict, host: str) -> tuple[str | None, int | None]:
    """(switch, vlan) the host is attached to."""
    for link in spec.get("links", []):
        for me, my_port, peer, peer_port in (
            (link["a"], link["a_port"], link["b"], link["b_port"]),
            (link["b"], link["b_port"], link["a"], link["a_port"]),
        ):
            if me != host:
                continue
            ptype = snap["devices"].get(peer, {}).get("type")
            port = snap["ports"].get(peer, {}).get(peer_port)
            if ptype in SWITCH_TYPES and port:
                return peer, port["vlan"]
    return None, None


def _trunk_graph(spec: dict, snap: dict) -> dict[str, str]:
    """Union-find over switch<->switch links that are trunk on both ends."""
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for link in spec.get("links", []):
        ta = snap["devices"].get(link["a"], {}).get("type")
        tb = snap["devices"].get(link["b"], {}).get("type")
        if ta not in SWITCH_TYPES or tb not in SWITCH_TYPES:
            continue
        pa = snap["ports"].get(link["a"], {}).get(link["a_port"], {})
        pb = snap["ports"].get(link["b"], {}).get(link["b_port"], {})
        if pa.get("mode") == 2 and pb.get("mode") == 2:
            union(link["a"], link["b"])
    for dev, info in snap["devices"].items():
        if info.get("type") in SWITCH_TYPES:
            find(dev)
    return {d: find(d) for d in parent}


def _default_rules(spec: dict) -> list[dict]:
    rules: list[dict] = [{"link_up": "all"}]
    for link in spec.get("links", []):
        # trunk ends must agree on mode/native or the link is inconsistent
        rules.append({"trunk_consistency": f'{link["a"]}:{link["a_port"]}-{link["b"]}:{link["b_port"]}'})
    return rules


def check(spec: dict, rules: list[dict] | None = None) -> dict:
    snap = _snapshot(spec)
    rules = rules if rules is not None else (spec.get("asserts") or _default_rules(spec))
    passed: list[str] = []
    failed: list[dict] = []

    def ok(msg: str) -> None:
        passed.append(msg)

    def bad(msg: str, fix: str) -> None:
        failed.append({"assert": msg, "fix": fix})

    for rule in rules:
        kind = next(iter(rule))
        arg = rule[kind]

        if kind == "link_up":
            for link in spec.get("links", []):
                for dev, port in ((link["a"], link["a_port"]), (link["b"], link["b_port"])):
                    st = snap["ports"].get(dev, {}).get(port, {})
                    if st.get("up") and st.get("proto"):
                        ok(f"link up {dev}:{port}")
                    else:
                        bad(f"link DOWN {dev}:{port}",
                            f"check the cable type ({link.get('cable', 'auto')}) and "
                            f"`no shutdown` on {dev}:{port}")

        elif kind == "access":
            st = snap["ports"].get(arg["device"], {}).get(arg["port"], {})
            if st.get("vlan") == arg.get("vlan") and st.get("mode") != 2:
                ok(f'{arg["device"]}:{arg["port"]} access vlan {arg["vlan"]}')
            else:
                bad(f'{arg["device"]}:{arg["port"]} vlan={st.get("vlan")} mode={st.get("mode")}, '
                    f'expected access {arg.get("vlan")}',
                    f'switchport mode access + switchport access vlan {arg.get("vlan")}')

        elif kind == "trunk":
            st = snap["ports"].get(arg["device"], {}).get(arg["port"], {})
            problems = []
            if st.get("mode") != 2:
                problems.append(f'mode={st.get("mode")} (need 2)')
            if "native" in arg and st.get("native") != arg["native"]:
                problems.append(f'native={st.get("native")} (need {arg["native"]})')
            if problems:
                bad(f'{arg["device"]}:{arg["port"]} trunk ' + ", ".join(problems),
                    f'switchport mode trunk' +
                    (f' + switchport trunk native vlan {arg["native"]}' if "native" in arg else ""))
            else:
                ok(f'{arg["device"]}:{arg["port"]} trunk ok')

        elif kind == "trunk_consistency":
            left, right = str(arg).split("-")
            (d1, p1), (d2, p2) = left.split(":"), right.split(":")
            a = snap["ports"].get(d1, {}).get(p1, {})
            b = snap["ports"].get(d2, {}).get(p2, {})
            if a.get("mode") == 2 and b.get("mode") == 2 and a.get("native") == b.get("native"):
                ok(f"trunk consistent {arg}")
            else:
                bad(f"trunk mismatch {arg}: {d1} mode={a.get('mode')} native={a.get('native')} / "
                    f"{d2} mode={b.get('mode')} native={b.get('native')}",
                    "both ends: switchport mode trunk and the same native vlan")

        elif kind in ("same_vlan", "diff_vlan"):
            h1, h2 = arg
            s1, v1 = _host_vlan(spec, snap, h1)
            s2, v2 = _host_vlan(spec, snap, h2)
            graph = _trunk_graph(spec, snap)
            same_domain = bool(s1 and s2 and v1 == v2 and graph.get(s1) == graph.get(s2))
            expect = kind == "same_vlan"
            if same_domain == expect:
                ok(f'{h1}(vlan {v1} on {s1}) {"shares" if expect else "is separated from"} '
                   f'{h2}(vlan {v2} on {s2})')
            elif expect:
                bad(f"{h1} and {h2} should share a broadcast domain "
                    f"(vlan {v1}@{s1} vs {v2}@{s2})",
                    "put both access ports in the same vlan and trunk the switch-to-switch link")
            else:
                bad(f"{h1} and {h2} should NOT share a broadcast domain "
                    f"(both vlan {v1})",
                    "assign the two access ports to different vlans")

        elif kind == "vlan_exists":
            from . import state as st_mod
            vl = st_mod.vlans(arg["device"])
            hit = [v for v in vl if v["id"] == arg["vlan"]]
            if hit and (("name" not in arg) or hit[0]["name"] == arg["name"]):
                ok(f'{arg["device"]} has vlan {arg["vlan"]}' +
                   (f' named {arg["name"]}' if "name" in arg else ""))
            else:
                bad(f'{arg["device"]} vlan {arg["vlan"]} missing or misnamed',
                    f'vlan {arg["vlan"]} + name {arg.get("name", "")}')

        elif kind == "vtp":
            from . import state as st_mod
            info = st_mod.vtp(arg["device"])
            want_mode = arg.get("mode")
            want_dom = arg.get("domain")
            good = (want_mode is None or info.get("mode") == want_mode) and \
                   (want_dom is None or info.get("domain") == want_dom)
            if good:
                ok(f'{arg["device"]} vtp {info.get("mode")}/{info.get("domain")}')
            else:
                bad(f'{arg["device"]} vtp is {info.get("mode")}/{info.get("domain")}, '
                    f'expected {want_mode}/{want_dom}',
                    f'vtp mode {want_mode} + vtp domain {want_dom}')

        else:
            bad(f"unknown assert {kind}", "supported: link_up, access, trunk, "
                                          "trunk_consistency, same_vlan, diff_vlan, "
                                          "vlan_exists, vtp")

    return {
        "ok": not failed,
        "passed": len(passed),
        "failed": len(failed),
        "failures": failed,
        "details": passed,
    }
