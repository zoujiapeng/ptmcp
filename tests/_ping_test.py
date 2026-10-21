import json, sys
sys.path.insert(0, ".")
import ptmcp.pt as pt, ptmcp.pdu as pdu
print("devices:", len(pt.status()["devices"]))
print("same-VLAN ping   PC11 -> PC12 :", json.dumps(pdu.ping_pdu("PC11", "PC12"), ensure_ascii=False)[:400])
print("cross-VLAN ping  PC11 -> SRV1 :", json.dumps(pdu.ping_pdu("PC11", "SRV1"), ensure_ascii=False)[:400])
