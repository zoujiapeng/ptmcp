import json, sys, time
sys.path.insert(0, ".")
import ptmcp.pt as pt, ptmcp.pdu as pdu
spec = json.loads(open("tests/ping_lab.json", encoding="utf-8").read())
print("build:", pt.build(spec)["link_check"]["allUp"])
time.sleep(3)
print("ping H1->H2:", json.dumps(pdu.ping("H1", "H2"), ensure_ascii=False)[:400])
