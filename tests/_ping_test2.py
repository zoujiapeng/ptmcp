import json, sys
sys.path.insert(0, ".")
import ptmcp.pdu as pdu
for a, b in (("PC11", "PC12"), ("PC11", "SRV1"), ("PC11", "PC42")):
    r = pdu.ping(a, b)
    print(f'{a} -> {b}: ok={r["ok"]} reached={r["reached_destination"]} reply={r["got_reply"]} steps={r["steps"]}')
    print("   trace:", r["trace"][-6:])
