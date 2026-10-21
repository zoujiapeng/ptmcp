"""ptmcp.fix - close the loop: assert -> repair -> re-assert, unattended.

`fix_loop(spec, rounds=3)` reads the spec's "asserts", compares them with the
live device state, turns every mismatch it knows how to repair into `ops`
(the same shape `pt_batch` takes), applies them in ONE round-trip, and re-checks.
It stops when the lab is correct, when nothing more can be repaired, or when the
round budget is gone - and reports the diff of every round.

Repairable automatically: access vlan, trunk mode/native, trunk consistency,
missing VLAN, VTP mode/domain, administratively down interfaces (no shutdown).
Reported as manual: broadcast-domain expectations (same_vlan/diff_vlan) that
contradict the cabling, wrong cable type (needs a rebuild), missing hardware.
"""
from __future__ import annotations

import json

from . import bridge, ops as ops_mod
from .asserts import HOST_TYPES, SWITCH_TYPES, _host_vlan, _snapshot, check
from .catalog import DEVICE_TYPES


def _desired_native(spec: dict, d1: str, p1: str, d2: str, p2: str, snap: dict) -> int | None:
    """Which native VLAN both trunk ends should use.

    Priority: an explicit {"trunk": {... "native": N}} assert for either end,
    otherwise the value already present on the first end.
    """
    for rule in spec.get("asserts", []):
        t = rule.get("trunk")
        if not t:
            continue
        if (t.get("device"), t.get("port")) in ((d1, p1), (d2, p2)) and "native" in t:
            return int(t["native"])
    left = snap["ports"].get(d1, {}).get(p1, {})
    return left.get("native") if left else None


def plan(spec: dict) -> dict:
    """Current mismatches and the ops that would repair them (no changes made)."""
    snap = _snapshot(spec)
    ops: list[dict] = []
    manual: list[str] = []
    seen: set[str] = set()

    def add(op: dict) -> None:
        key = json.dumps(op, sort_keys=True)
        if key not in seen:
            seen.add(key)
            ops.append(op)

    for rule in spec.get("asserts", []):
        kind = next(iter(rule))
        arg = rule[kind]

        if kind == "access":
            st = snap["ports"].get(arg["device"], {}).get(arg["port"], {})
            if st.get("vlan") != arg.get("vlan") or st.get("mode") == 2:
                add({"op": "port", "device": arg["device"], "port": arg["port"],
                     "mode": 1, "access_vlan": int(arg["vlan"])})
                if "cli" not in seen:
                    add({"op": "cli", "device": arg["device"],
                         "commands": ["enable", "configure terminal",
                                      f'interface {_short(arg["port"])}',
                                      "switchport mode access",
                                      f'switchport access vlan {int(arg["vlan"])}', "exit"]})

        elif kind == "trunk":
            st = snap["ports"].get(arg["device"], {}).get(arg["port"], {})
            bad = st.get("mode") != 2 or ("native" in arg and st.get("native") != arg["native"])
            if bad:
                op = {"op": "port", "device": arg["device"], "port": arg["port"], "mode": 2}
                if "native" in arg:
                    op["native_vlan"] = int(arg["native"])
                add(op)
                cmds = ["enable", "configure terminal", f'interface {_short(arg["port"])}',
                        "switchport mode trunk"]
                if "native" in arg:
                    cmds.append(f'switchport trunk native vlan {int(arg["native"])}')
                cmds.append("exit")
                add({"op": "cli", "device": arg["device"], "commands": cmds})

        elif kind == "trunk_consistency":
            ends = None
            for link in spec.get("links", []):
                if f'{link["a"]}:{link["a_port"]}-{link["b"]}:{link["b_port"]}' == str(arg):
                    ends = (link["a"], link["a_port"], link["b"], link["b_port"])
                    break
            if ends is None:
                manual.append(f"trunk_consistency target {arg!r} is not a link in this spec")
                continue
            d1, p1, d2, p2 = ends
            a = snap["ports"].get(d1, {}).get(p1, {})
            b = snap["ports"].get(d2, {}).get(p2, {})
            if not (a.get("mode") == 2 and b.get("mode") == 2 and a.get("native") == b.get("native")):
                native = _desired_native(spec, d1, p1, d2, p2, snap)
                for dev, port in ((d1, p1), (d2, p2)):
                    op = {"op": "port", "device": dev, "port": port, "mode": 2}
                    if native is not None:
                        op["native_vlan"] = int(native)
                    add(op)
                    cmds = ["enable", "configure terminal", f"interface {_short(port)}",
                            "switchport mode trunk"]
                    if native is not None:
                        cmds.append(f"switchport trunk native vlan {int(native)}")
                    cmds.append("exit")
                    add({"op": "cli", "device": dev, "commands": cmds})

        elif kind == "vlan_exists":
            add({"op": "cli", "device": arg["device"],
                 "commands": ["enable", "configure terminal",
                              f'vlan {int(arg["vlan"])}'] +
                             ([f'name {arg["name"]}'] if arg.get("name") else []) +
                             ["exit"]})

        elif kind == "vtp":
            cmds = ["enable", "configure terminal"]
            if arg.get("mode"):
                cmds.append(f'vtp mode {arg["mode"]}')
            if arg.get("domain"):
                cmds.append(f'vtp domain {arg["domain"]}')
            add({"op": "cli", "device": arg["device"], "commands": cmds})

        elif kind == "link_up":
            for link in spec.get("links", []):
                for dev, port in ((link["a"], link["a_port"]), (link["b"], link["b_port"])):
                    st = snap["ports"].get(dev, {}).get(port, {})
                    dtype = snap["devices"].get(dev, {}).get("type")
                    if st.get("up") and st.get("proto"):
                        continue
                    if dtype in SWITCH_TYPES or dtype == 0 or dtype == 16:
                        add({"op": "cli", "device": dev,
                             "commands": ["enable", "configure terminal",
                                          f"interface {_short(port)}", "no shutdown", "exit"]})
                    else:
                        manual.append(f"{dev}:{port} down - check the cable type")

        elif kind in ("same_vlan", "diff_vlan"):
            h1, h2 = arg
            s1, v1 = _host_vlan(spec, snap, h1)
            s2, v2 = _host_vlan(spec, snap, h2)
            graph = _trunk_graph_safe(spec, snap)
            same = bool(s1 and s2 and v1 == v2 and graph.get(s1) == graph.get(s2))
            if same != (kind == "same_vlan"):
                manual.append(
                    f"{h1} ({v1}@{s1}) vs {h2} ({v2}@{s2}): the expected "
                    f"{'shared' if kind == 'same_vlan' else 'separated'} domain does not "
                    "follow from the cabling - fix the design, not the device state")

    return {"ops": ops, "manual": manual}


def _trunk_graph_safe(spec: dict, snap: dict) -> dict:
    from .asserts import _trunk_graph
    return _trunk_graph(spec, snap)


def _short(port: str) -> str:
    """FastEthernet0/1 -> f0/1, GigabitEthernet0/2 -> g0/2 (IOS shorthand)."""
    return port.replace("FastEthernet", "f").replace("GigabitEthernet", "g")


def fix_loop(spec: dict, rounds: int = 3, quiet: bool = False) -> dict:
    history: list[dict] = []
    for n in range(1, rounds + 1):
        before = check(spec)
        if before["ok"]:
            history.append({"round": n, "result": "already correct",
                            "passed": before["passed"], "failed": 0})
            return {"ok": True, "rounds": history, "applied": len(history) - 1,
                    "final": {"passed": before["passed"], "failed": 0, "failures": []}}
        todo = plan(spec)
        if not todo["ops"]:
            history.append({"round": n, "result": "nothing auto-repairable",
                            "failures": [f["assert"] for f in before["failures"]],
                            "manual": todo["manual"]})
            return {"ok": False, "rounds": history, "applied": 0,
                    "final": {"passed": before["passed"], "failed": before["failed"],
                              "failures": before["failures"], "manual": todo["manual"]}}
        res = ops_mod.batch(todo["ops"])
        history.append({"round": n, "applied_ops": len(todo["ops"]),
                        "ops": [f'{o["op"]}:{o.get("device", "")}' for o in todo["ops"]],
                        "log": res.get("result", "")[:400],
                        "manual": todo["manual"]})
        if quiet:
            continue
    final = check(spec)
    return {"ok": final["ok"], "rounds": history,
            "applied": len(history),
            "final": {"passed": final["passed"], "failed": final["failed"],
                      "failures": final["failures"]}}

