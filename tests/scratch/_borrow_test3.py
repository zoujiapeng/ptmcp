import sys
sys.path.insert(0, ".")
import ptmcp.borrow as borrow, ptmcp.term as term, ptmcp.state as st

lines = borrow.vlan_cli(
    vlans=[{"vlan_id": 40, "name": "CAMPUS"}],
    access_ports=[{"switch": "S1", "port": "FastEthernet0/3", "vlan_id": 40}],
    trunks=[{"switch": "S1", "port": "GigabitEthernet0/1"}],
    switch_model="2960-24TT")
res = term.run("S1", ["enable", "configure terminal"] + lines + ["exit"])
print("terminal trace:")
for t in res["trace"]:
    print("   ", t)
print("vlan 40 present:", any(v["id"] == 40 for v in st.vlans("S1")))
cfg = st.interface_config("S1")
print("f0/3:", cfg.get("FastEthernet0/3"), "| g0/1:", cfg.get("GigabitEthernet0/1"))
