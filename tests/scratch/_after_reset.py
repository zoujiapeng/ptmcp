import json, sys, time
sys.path.insert(0, ".")
import ptmcp.pt as pt, ptmcp.pdu as pdu
spec = json.loads(open("tests/ping_lab.json", encoding="utf-8").read())
r = pt.build(spec)
print("ping_lab build allUp:", r["link_check"]["allUp"])
time.sleep(5)
print("H1->H2:", json.dumps(pdu.ping("H1","H2"), ensure_ascii=False)[:200])
