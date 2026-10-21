import json, sys
sys.path.insert(0, ".")
import ptmcp.asserts as A, ptmcp.state as st
spec = json.loads(open("specs/campus.json", encoding="utf-8").read())
res = A.check(spec)
print("asserts:", res["ok"], res["passed"], "/", res["failed"])
for f in res["failures"][:8]:
    print("  FAIL:", f["assert"][:100])
cfg = st.running_config("R1")
subs = [l.strip() for l in cfg.splitlines() if "0/0." in l or "encapsulation" in l]
print("R1 subifs:", subs[:8])
print("R1 ospf:", [l.strip() for l in cfg.splitlines() if "ospf" in l.lower() or "network 10" in l][:6])
