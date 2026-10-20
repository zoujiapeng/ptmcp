"""Benchmark: how fast can ptmcp build + green a topology, at three sizes.

Measures wall-clock per phase and the automation traffic (bridge round-trips and
payload bytes), which is the part that maps to agent cost. Tiers are modelled on
public CCNA-style task sheets (VLAN + trunk + router-on-a-stick + OSPF + DHCP).

    python tests/bench.py            # run all tiers
    python tests/bench.py 2          # run one tier
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ptmcp.pt as pt                      # noqa: E402
from ptmcp import bridge                   # noqa: E402

STATS = {"calls": 0, "bytes": 0}
_real_run = bridge.run_js


def counted(js: str, timeout: float = 20.0) -> str:
    STATS["calls"] += 1
    STATS["bytes"] += len(js)
    return _real_run(js, timeout=timeout)


bridge.run_js = counted
pt.ask = lambda js, timeout=20.0: bridge._unwrap(counted(js, timeout))


def tier1() -> dict:
    """6 devices: router-on-a-stick, VLAN 2/3, two hosts (CCNA 200-301 style)."""
    return {
        "devices": [{"name": "R1", "model": "2911", "x": 300, "y": 120},
                    {"name": "S1", "model": "2960-24TT", "x": 300, "y": 280},
                    {"name": "PC1", "model": "PC-PT", "x": 180, "y": 430},
                    {"name": "PC2", "model": "PC-PT", "x": 420, "y": 430}],
        "links": [{"a": "R1", "a_port": "GigabitEthernet0/0", "b": "S1", "b_port": "GigabitEthernet0/1"},
                  {"a": "S1", "a_port": "FastEthernet0/1", "b": "PC1", "b_port": "FastEthernet0"},
                  {"a": "S1", "a_port": "FastEthernet0/2", "b": "PC2", "b_port": "FastEthernet0"}],
        "ips": [{"device": "PC1", "port": "FastEthernet0", "ip": "192.168.2.10", "mask": "255.255.255.0", "gateway": "192.168.2.1"},
                {"device": "PC2", "port": "FastEthernet0", "ip": "192.168.3.10", "mask": "255.255.255.0", "gateway": "192.168.3.1"}],
        "cli": {"R1": ["enable", "configure terminal", "hostname R1",
                       "interface g0/0", "no shutdown", "exit",
                       "interface g0/0.2", "encapsulation dot1Q 2", "ip address 192.168.2.1 255.255.255.0", "exit",
                       "interface g0/0.3", "encapsulation dot1Q 3", "ip address 192.168.3.1 255.255.255.0", "exit"],
                "S1": ["enable", "configure terminal", "hostname S1",
                       "vlan 2", "name SALES", "exit", "vlan 3", "name ENG", "exit",
                       "interface f0/1", "switchport mode access", "switchport access vlan 2", "exit",
                       "interface f0/2", "switchport mode access", "switchport access vlan 3", "exit",
                       "interface g0/1", "switchport mode trunk", "exit"]},
        "save": r"C:\pt\bench_t1.pkt",
    }


def tier2() -> dict:
    """11 devices: two sites, 2 VLANs each, OSPF between routers, 6 hosts."""
    spec = {
        "devices": [{"name": "R1", "model": "2911", "x": 220, "y": 100},
                    {"name": "R2", "model": "2911", "x": 620, "y": 100},
                    {"name": "S1", "model": "2960-24TT", "x": 220, "y": 260},
                    {"name": "S2", "model": "2960-24TT", "x": 620, "y": 260}],
        "links": [{"a": "R1", "a_port": "GigabitEthernet0/1", "b": "R2", "b_port": "GigabitEthernet0/1"},
                  {"a": "R1", "a_port": "GigabitEthernet0/0", "b": "S1", "b_port": "GigabitEthernet0/1"},
                  {"a": "R2", "a_port": "GigabitEthernet0/0", "b": "S2", "b_port": "GigabitEthernet0/1"}],
        "ips": [], "cli": {},
        "save": r"C:\pt\bench_t2.pkt",
    }
    for site, (rtr, sw, x0) in enumerate((("R1", "S1", 150), ("R2", "S2", 550)), start=1):
        for vlan, dx in ((2, 0), (3, 120)):
            for i, dy in enumerate((0, 90), start=1):
                name = f"PC{site}{vlan}{i}"
                spec["devices"].append({"name": name, "model": "PC-PT", "x": x0 + dx, "y": 420 + dy})
                spec["links"].append({"a": sw, "a_port": f"FastEthernet0/{(vlan - 2) * 2 + i}",
                                      "b": name, "b_port": "FastEthernet0"})
                spec["ips"].append({"device": name, "port": "FastEthernet0",
                                    "ip": f"10.{site}.{vlan}.{10 + i}", "mask": "255.255.255.0",
                                    "gateway": f"10.{site}.{vlan}.1"})
        spec["cli"][sw] = ["enable", "configure terminal", f"hostname {sw}",
                           "vlan 2", "name V2", "exit", "vlan 3", "name V3", "exit",
                           "interface f0/1", "switchport mode access", "switchport access vlan 2", "exit",
                           "interface f0/2", "switchport mode access", "switchport access vlan 2", "exit",
                           "interface f0/3", "switchport mode access", "switchport access vlan 3", "exit",
                           "interface f0/4", "switchport mode access", "switchport access vlan 3", "exit",
                           "interface g0/1", "switchport mode trunk", "exit"]
        spec["cli"][rtr] = ["enable", "configure terminal", f"hostname {rtr}",
                            "interface g0/0", "no shutdown", "exit",
                            "interface g0/0.2", "encapsulation dot1Q 2", f"ip address 10.{site}.2.1 255.255.255.0", "exit",
                            "interface g0/0.3", "encapsulation dot1Q 3", f"ip address 10.{site}.3.1 255.255.255.0", "exit",
                            "interface g0/1", f"ip address 10.0.0.{site} 255.255.255.252", "no shutdown", "exit",
                            "router ospf 1", f"network 10.{site}.0.0 0.0.255.255 area 0",
                            "network 10.0.0.0 0.0.0.3 area 0", "exit"]
    return spec


def tier3() -> dict:
    """24 devices: 4 switches, 2 routers, 12 hosts, 18 links - stress."""
    spec = {
        "devices": [{"name": "R1", "model": "2911", "x": 240, "y": 90},
                    {"name": "R2", "model": "2911", "x": 700, "y": 90},
                    {"name": "S1", "model": "2960-24TT", "x": 120, "y": 240},
                    {"name": "S2", "model": "2960-24TT", "x": 360, "y": 240},
                    {"name": "S3", "model": "2960-24TT", "x": 580, "y": 240},
                    {"name": "S4", "model": "2960-24TT", "x": 820, "y": 240}],
        "links": [{"a": "R1", "a_port": "GigabitEthernet0/1", "b": "R2", "b_port": "GigabitEthernet0/1"},
                  {"a": "R1", "a_port": "GigabitEthernet0/0", "b": "S1", "b_port": "GigabitEthernet0/1"},
                  {"a": "R2", "a_port": "GigabitEthernet0/0", "b": "S4", "b_port": "GigabitEthernet0/1"},
                  {"a": "S1", "a_port": "GigabitEthernet0/2", "b": "S2", "b_port": "GigabitEthernet0/2"},
                  {"a": "S2", "a_port": "GigabitEthernet0/1", "b": "S3", "b_port": "GigabitEthernet0/1"},
                  {"a": "S3", "a_port": "GigabitEthernet0/2", "b": "S4", "b_port": "GigabitEthernet0/2"}],
        "ips": [], "cli": {},
        "save": r"C:\pt\bench_t3.pkt",
    }
    for si, (sw, x0) in enumerate((("S1", 60), ("S2", 300), ("S3", 540), ("S4", 780)), start=1):
        for i in range(3):
            name = f"H{si}{i + 1}"
            spec["devices"].append({"name": name, "model": "PC-PT", "x": x0 + i * 45, "y": 420})
            spec["links"].append({"a": sw, "a_port": f"FastEthernet0/{i + 1}",
                                  "b": name, "b_port": "FastEthernet0"})
            spec["ips"].append({"device": name, "port": "FastEthernet0",
                                "ip": f"172.16.{si}.{10 + i}", "mask": "255.255.255.0"})
        spec["cli"][sw] = ["enable", "configure terminal", f"hostname {sw}",
                           "vlan 10", "name USERS", "exit",
                           "interface range f0/1 - 3", "switchport mode access",
                           "switchport access vlan 10", "exit",
                           "interface range g0/1 - 2", "switchport mode trunk", "exit"]
    spec["cli"]["R1"] = ["enable", "configure terminal", "hostname R1",
                         "interface g0/0", "no shutdown", "exit",
                         "interface g0/1", "ip address 10.0.0.1 255.255.255.252",
                         "no shutdown", "exit"]
    spec["cli"]["R2"] = ["enable", "configure terminal", "hostname R2",
                         "interface g0/0", "no shutdown", "exit",
                         "interface g0/1", "ip address 10.0.0.2 255.255.255.252",
                         "no shutdown", "exit"]
    return spec


def tier4() -> dict:
    """18 devices / 18 links - same size as tier3 but a TREE (no STP blocking)."""
    spec = tier3()
    spec["save"] = r"C:\pt\bench_t4.pkt"
    drop = [("S1", "S2"), ("S4", "R2")]
    spec["links"] = [l for l in spec["links"]
                     if {l["a"], l["b"]} not in ({"S1", "S2"}, {"S4", "R2"})]
    spec["links"].append({"a": "S4", "a_port": "GigabitEthernet0/1", "b": "R2", "b_port": "GigabitEthernet0/0"})
    return spec


TIERS = {"1": tier1, "2": tier2, "3": tier3, "4": tier4}


def run(tier: str) -> dict:
    spec = TIERS[tier]()
    STATS["calls"] = STATS["bytes"] = 0
    spec["wait"] = False
    t0 = time.time()
    res = pt.build(spec, new=True)
    t_build = time.time() - t0
    t1 = time.time()
    again = pt.wait_links_up(spec)
    t_green = time.time() - t1
    ok = again.get("allUp")
    res["link_check"] = again
    size = 0
    saved = pt.save(spec["save"])
    p = Path(spec["save"])
    size = p.stat().st_size if p.exists() else 0
    return {
        "tier": tier,
        "devices": len(spec["devices"]),
        "links": len(spec["links"]),
        "build_s": round(t_build, 1),
        "regreen_s": round(t_green, 1),
        "all_up": ok,
        "down": [d for d in (res["link_check"].get("detail") or []) if "DOWN" in d],
        "failed_links": res.get("failed_links", []),
        "pkt_bytes": size,
        "bridge_calls": STATS["calls"],
        "payload_kb": round(STATS["bytes"] / 1024, 1),
        "save": saved[:60],
    }


if __name__ == "__main__":
    tiers = sys.argv[1:] or ["1", "2", "3"]
    rows = [run(t) for t in tiers]
    print(json.dumps(rows, indent=2, ensure_ascii=False))

