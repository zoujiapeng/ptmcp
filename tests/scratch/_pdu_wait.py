import json, sys, time
sys.path.insert(0, ".")
import ptmcp.pdu as pdu, ptmcp.pt as pt
time.sleep(20)
print("ports up:", pt.wait_links_up(json.loads(open("tests/ping_lab.json", encoding="utf-8").read())).get("allUp"))
print("ping after 20s:", json.dumps(pdu.ping("H1", "H2", max_steps=120), ensure_ascii=False)[:420])
