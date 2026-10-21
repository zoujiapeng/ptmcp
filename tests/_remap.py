import json, pathlib
p = pathlib.Path("specs/campus.json")
s = json.loads(p.read_text(encoding="utf-8"))

# 3560-24PS has 24x FastEthernet + 2x GigabitEthernet: Gi0/3-4 do not exist.
remap = {"C1": {"GigabitEthernet0/3": "FastEthernet0/1", "GigabitEthernet0/4": "FastEthernet0/2"},
         "C2": {"GigabitEthernet0/3": "FastEthernet0/3", "GigabitEthernet0/4": "FastEthernet0/4"}}
for link in s["links"]:
    for side, key in (("a", "a_port"), ("b", "b_port")):
        dev = link[side]
        if dev in remap and link[key] in remap[dev]:
            link[key] = remap[dev][link[key]]

for dev, mapping in remap.items():
    cmds = s["cli"][dev]
    s["cli"][dev] = [mapping.get(c, c) for c in cmds]

def fix_assert(a):
    for k, v in a.items():
        if k == "trunk" and v.get("device") in remap:
            v["port"] = remap[v["device"]].get(v["port"], v["port"])
        elif k == "trunk_consistency":
            for d, m in remap.items():
                for old, new in m.items():
                    v = v.replace(f"{d}:{old}", f"{d}:{new}")
            a[k] = v
    return a

s["asserts"] = [fix_assert(a) for a in s["asserts"]]
p.write_text(json.dumps(s, indent=2, ensure_ascii=False), encoding="utf-8")
print("remapped core uplinks to FastEthernet ports")
print("trunks now:", [(l["a"], l["a_port"], l["b"], l["b_port"]) for l in s["links"] if l["a"] in ("C1", "C2")][:4])
