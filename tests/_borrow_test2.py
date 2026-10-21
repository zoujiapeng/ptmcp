import sys
sys.path.insert(0, ".")
import ptmcp.borrow as borrow, ptmcp.term as term, ptmcp.state as st

lines = borrow.vlan_cli(
    vlans=[{"vlan_id": 40, "name": "CAMPUS"}],
    access_ports=[{"switch": "CORE1", "port": "FastEthernet0/3", "vlan_id": 40}],
    trunks=[{"switch": "CORE1", "port": "GigabitEthernet0/1"}],
    switch_model="2960-24TT")
print("borrowed lines:", len(lines))
for l in lines:
    print("   ", l)

res = term.run("CORE1", ["enable", "configure terminal"] + lines + ["exit"])
print("terminal trace (last 6):")
for t in res["trace"][-6:]:
    print("   ", t)
print("vlan 40 present:", any(v["id"] == 40 for v in st.vlans("CORE1")))
