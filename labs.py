#!/usr/bin/env python
"""labs.py - build the three teaching cases (27 VLAN / 28 Trunk / 29 VTP).

For each case: fresh canvas (fileNew(false) - no modal), place devices, cable
them, push the CLI from the PDF through device.enterCommand(), then read the
resulting state back through the port API and print it.

    python labs.py 27|28|29
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ptctl  # noqa: E402

SW = "2950T-24"

# name -> (model, x, y)
LABS = {
    "27": {
        "file": r"C:\pt\case27_vlan.pkt",
        "devices": {
            "S1": (SW, 300, 150), "PC0": ("PC-PT", 200, 380), "PC1": ("PC-PT", 420, 380),
        },
        "links": [
            ("S1", "FastEthernet0/1", "PC0", "FastEthernet0"),
            ("S1", "FastEthernet0/2", "PC1", "FastEthernet0"),
        ],
        # PC0/PC1 in 192.168.12.0/24 (step 1), VLAN2 -> f0/1, VLAN3 -> f0/2
        "ips": {"PC0": ("192.168.12.1", "255.255.255.0"), "PC1": ("192.168.12.2", "255.255.255.0")},
        "cli": {
            "S1": ["enable", "configure terminal",
                   "hostname S1",
                   "vlan 2", "name VLAN2", "exit",
                   "vlan 3", "name VLAN3", "exit",
                   "interface f0/1", "switchport mode access", "switchport access vlan 2", "exit",
                   "interface f0/2", "switchport mode access", "switchport access vlan 3", "exit"],
        },
        "check_ports": [("S1", "FastEthernet0/1", 2), ("S1", "FastEthernet0/2", 3)],
        "verify": [("S1", "show vlan")],
    },
    "28": {
        "file": r"C:\pt\case28_trunk.pkt",
        "devices": {
            "S1": (SW, 260, 140), "S2": (SW, 620, 140),
            "PC0": ("PC-PT", 150, 400), "PC1": ("PC-PT", 330, 400),
            "PC2": ("PC-PT", 540, 400), "PC3": ("PC-PT", 720, 400),
        },
        "links": [
            ("S1", "FastEthernet0/1", "PC0", "FastEthernet0"),
            ("S1", "FastEthernet0/2", "PC1", "FastEthernet0"),
            ("S2", "FastEthernet0/3", "PC2", "FastEthernet0"),
            ("S2", "FastEthernet0/4", "PC3", "FastEthernet0"),
            ("S1", "FastEthernet0/13", "S2", "FastEthernet0/13"),
        ],
        "ips": {
            "PC0": ("192.168.2.1", "255.255.255.0"), "PC2": ("192.168.2.2", "255.255.255.0"),
            "PC1": ("192.168.3.1", "255.255.255.0"), "PC3": ("192.168.3.2", "255.255.255.0"),
        },
        "cli": {
            "S1": ["enable", "configure terminal", "hostname S1",
                   "vlan 2", "name VLAN2", "exit", "vlan 3", "name VLAN3", "exit",
                   "interface f0/1", "switchport mode access", "switchport access vlan 2", "exit",
                   "interface f0/2", "switchport mode access", "switchport access vlan 3", "exit",
                   "interface f0/13", "switchport mode trunk", "exit"],
            "S2": ["enable", "configure terminal", "hostname S2",
                   "vlan 2", "name VLAN2", "exit", "vlan 3", "name VLAN3", "exit",
                   "interface f0/3", "switchport mode access", "switchport access vlan 2", "exit",
                   "interface f0/4", "switchport mode access", "switchport access vlan 3", "exit",
                   "interface f0/13", "switchport mode trunk", "switchport trunk native vlan 2", "exit"],
        },
        "check_ports": [("S1", "FastEthernet0/1", 2), ("S1", "FastEthernet0/2", 3),
                        ("S2", "FastEthernet0/3", 2), ("S2", "FastEthernet0/4", 3)],
        "verify": [("S1", "show interfaces trunk"), ("S2", "show interfaces trunk")],
    },
    "29": {
        "file": r"C:\pt\case29_vtp.pkt",
        "devices": {"S1": (SW, 180, 140), "S3": (SW, 430, 140), "S2": (SW, 680, 140)},
        "links": [
            ("S1", "FastEthernet0/15", "S3", "FastEthernet0/1"),
            ("S3", "FastEthernet0/2", "S2", "FastEthernet0/15"),
        ],
        "ips": {},
        "cli": {
            "S1": ["enable", "configure terminal", "hostname S1",
                   "interface f0/15", "switchport mode trunk", "exit",
                   "vtp mode server", "vtp domain VTP-TEST", "vtp password cisco",
                   "vlan 2", "exit", "vlan 3", "exit"],
            "S3": ["enable", "configure terminal", "hostname S3",
                   "interface range f0/1 - 2", "switchport mode trunk", "exit",
                   "vtp mode transparent", "vtp domain VTP-TEST", "vtp password cisco"],
            "S2": ["enable", "configure terminal", "hostname S2",
                   "interface f0/15", "switchport mode trunk", "exit",
                   "vtp mode client", "vtp domain VTP-TEST", "vtp password cisco"],
        },
        "check_ports": [("S1", "FastEthernet0/15", None), ("S2", "FastEthernet0/15", None)],
        "verify": [("S1", "show vtp status"), ("S2", "show vlan"), ("S3", "show vlan")],
    },
}


def _js(s: str) -> str:
    return json.dumps(s)


def build_case(num: str) -> str:
    lab = LABS[num]
    L = ["var log = [];", "ipc.appWindow().fileNew(false);",
         "var lw = ipc.appWindow().getActiveWorkspace().getLogicalWorkspace();"]

    for name, (model, x, y) in lab["devices"].items():
        t = ptctl.DEVICE_TYPES[model]
        L.append(f"""
(function() {{
  var orig = lw.addDevice({t}, {_js(model)}, {x}, {y});
  if (!orig) {{ log.push("FAIL add {name}"); return; }}
  var d = ipc.network().getDevice(orig);
  d.setName({_js(name)});
  d.setHostName && d.setHostName({_js(name)});
  try {{ if ({t} <= 1 || {t} === 16) d.skipBoot(); }} catch (e) {{}}
  log.push("+" + {_js(name)});
}})();""")

    for a, ap, b, bp in lab["links"]:
        L.append(f"""
(function() {{
  var ok = lw.createLink({_js(a)}, {_js(ap)}, {_js(b)}, {_js(bp)}, 8100);
  log.push("link {a}:{ap}-{b}:{bp}=" + ok);
}})();""")

    for pc, (ip, mask) in lab["ips"].items():
        L.append(f"""
(function() {{
  var d = ipc.network().getDevice({_js(pc)});
  var p = d && d.getPort("FastEthernet0");
  if (!p) {{ log.push("FAIL ip {pc}"); return; }}
  p.setIpSubnetMask({_js(ip)}, {_js(mask)});
  log.push("ip {pc}={ip}");
}})();""")

    # CLI from the PDF, pushed through the device terminal
    for dev, lines in lab["cli"].items():
        arr = ", ".join(_js(x) for x in lines)
        L.append(f"""
(function() {{
  var d = ipc.network().getDevice({_js(dev)});
  var cmds = [{arr}];
  for (var i = 0; i < cmds.length; i++) {{
    try {{ d.enterCommand(cmds[i], ""); }} catch (e) {{ log.push("cli {dev} '" + cmds[i] + "' ERR " + e); }}
  }}
  log.push("cli {dev} done");
}})();""")

    # read state back
    checks = ", ".join(f"['{d}','{p}','{v}']" for d, p, v in lab["check_ports"])
    L.append(f"""
(function() {{
  var chk = [{checks}];
  for (var i = 0; i < chk.length; i++) {{
    var dev = ipc.network().getDevice(chk[i][0]);
    var po = dev && dev.getPort(chk[i][1]);
    if (!po) {{ log.push("chk " + chk[i][0] + " " + chk[i][1] + " MISSING"); continue; }}
    log.push(chk[i][0] + " " + chk[i][1] + " mode=" + po.getAdminOpMode() +
             " access=" + po.getAccessVlan() + " native=" + po.getNativeVlanId() +
             " up=" + po.isPortUp() + " proto=" + po.isProtocolUp() +
             " link=" + (po.getLink() ? "yes" : "no"));
  }}
}})();""")

    L.append(f'log.push("save=" + ipc.appWindow().fileSaveAs({_js(lab["file"])}));')
    L.append('throw new Error(log.join(" | "));')
    return ptctl.ask("\n".join(L), timeout=90)


def verify(num: str) -> str:
    """Read CLI output of the PDF's verification commands."""
    lab = LABS[num]
    L = ["var out = [];"]
    for dev, cmd in lab["verify"]:
        L.append(f"""
(function() {{
  var d = ipc.network().getDevice({_js(dev)});
  try {{
    d.enterCommand({_js(cmd)}, "");
    var txt = "";
    try {{ txt = d.getIpcTerminalLine(); }} catch (e) {{ txt = "noTerm(" + e + ")"; }}
    out.push({_js(dev)} + ">" + {_js(cmd)} + " :: " + txt);
  }} catch (e) {{ out.push({_js(dev)} + " ERR " + e); }}
}})();""")
    L.append('throw new Error(out.join(" || ").substring(0, 1600));')
    return ptctl.ask("\n".join(L), timeout=60)


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in LABS:
        print("usage: python labs.py 27|28|29 [--verify]")
        return 2
    num = argv[0]
    if "--verify" in argv:
        print(verify(num))
        return 0
    Path(r"C:\pt").mkdir(exist_ok=True)
    target = Path(LABS[num]["file"])
    if target.exists():
        target.unlink()
    print(build_case(num))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
