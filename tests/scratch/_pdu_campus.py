import json, sys, time
sys.path.insert(0, ".")
import ptmcp.pt as pt, ptmcp.pdu as pdu

spec = json.loads(open("specs/campus.json", encoding="utf-8").read())
t0 = time.time()
r = pt.build(spec)
print("build:", r["link_check"]["allUp"], "asserts:", r.get("asserts", {}).get("ok"), f'{round(time.time()-t0,1)}s')
for a, b, expect in (("PC11", "PC12", True), ("PC11", "SRV1", False), ("PC11", "PC41", True)):
    res = pdu.ping(a, b)
    verdict = "PASS" if res["ok"] == expect else "MISMATCH"
    print(f'{a} -> {b}: ok={res["ok"]} (expect {expect}) {verdict}  trace_tail={res["trace"][-3:]}')
