import pathlib, json

p = pathlib.Path("ptmcp/pt.py"); s = p.read_text(encoding="utf-8")
if 'report["cli_ready"]' in s:
    s = "\n".join(l for l in s.splitlines() if 'report["cli_ready"]' not in l)
    p.write_text(s, encoding="utf-8")
import ast; ast.parse(p.read_text(encoding="utf-8"))

# SRV1 lives behind R1 Gi0/2.30 (10.31.0.0/24), not 10.30.0.0/24
p = pathlib.Path("specs/campus.json"); spec = json.loads(p.read_text(encoding="utf-8"))
for ip in spec["ips"]:
    if ip["device"] == "SRV1":
        ip["ip"], ip["gateway"] = "10.31.0.10", "10.31.0.1"
spec["asserts"] = [a for a in spec["asserts"] if "diff_vlan" not in a]
spec["asserts"].append({"same_vlan": ["PC21", "SRV1"]})
p.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")
print("spec: SRV1 moved to 10.31.0.0/24, added same_vlan(PC21,SRV1)")
