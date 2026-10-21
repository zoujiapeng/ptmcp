import json, sys, time
sys.path.insert(0, ".")
import ptmcp.pt as pt, ptmcp.pdu as pdu
spec = json.loads(open("specs/campus.json", encoding="utf-8").read())
t0=time.time(); r = pt.build(spec)
print("build:", r["link_check"]["allUp"], "asserts:", r.get("asserts",{}).get("ok"), f'{round(time.time()-t0,1)}s')
print("waiting 45s for OSPF/STP...")
time.sleep(45)
for a,b,exp in (("PC11","PC12",True),("PC21","SRV1",True),("PC11","PC41",True)):
    res = pdu.ping(a,b)
    print(f'{a}->{b}: ok={res["ok"]} expect={exp} {"PASS" if res["ok"]==exp else "MISMATCH"} {res["trace"][-2:]}')
