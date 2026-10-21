import json, pathlib
p = pathlib.Path("specs/case28.json"); s = json.loads(p.read_text(encoding="utf-8"))
s["asserts"] = [a for a in s["asserts"] if not (list(a)[0] == "trunk" and a["trunk"]["device"] == "S1")]
s["asserts"].insert(4, {"trunk": {"device": "S1", "port": "FastEthernet0/13", "native": 2}})
cli = s["cli"]["S1"]
if "switchport trunk native vlan 2" not in cli:
    i = cli.index("switchport mode trunk")
    cli.insert(i + 1, "switchport trunk native vlan 2")
p.write_text(json.dumps(s, indent=2, ensure_ascii=False), encoding="utf-8")
print("case28 spec: native 2 on both ends")
