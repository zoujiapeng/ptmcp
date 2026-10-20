import json, pathlib
p = pathlib.Path("specs/case28.json")
spec = json.loads(p.read_text(encoding="utf-8"))
spec["asserts"] = [
    {"access": {"device": "S1", "port": "FastEthernet0/1", "vlan": 2}},
    {"access": {"device": "S1", "port": "FastEthernet0/2", "vlan": 3}},
    {"access": {"device": "S2", "port": "FastEthernet0/3", "vlan": 2}},
    {"access": {"device": "S2", "port": "FastEthernet0/4", "vlan": 3}},
    {"trunk": {"device": "S1", "port": "FastEthernet0/13", "native": 1}},
    {"trunk": {"device": "S2", "port": "FastEthernet0/13", "native": 2}},
    {"same_vlan": ["PC0", "PC2"]},
    {"diff_vlan": ["PC0", "PC1"]},
    {"diff_vlan": ["PC0", "PC3"]},
    {"vlan_exists": {"device": "S1", "vlan": 3, "name": "VLAN3"}}
]
p.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")
print("spec updated with asserts")
