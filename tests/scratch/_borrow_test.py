import sys
sys.path.insert(0, ".")
import ptmcp.borrow as borrow
try:
    lines = borrow.vlan_cli([{"id": 10, "name": "USERS"}, {"id": 30, "name": "SERVERS"}],
                            access_ports=[{"port": "FastEthernet0/1", "vlan": 10}],
                            trunks=[{"port": "GigabitEthernet0/1"}],
                            switch_model="2960-24TT")
    print("vlan_cli OK:", len(lines), "lines")
    for l in lines[:12]:
        print("   ", l)
except Exception as e:
    print("vlan_cli ERR:", type(e).__name__, str(e)[:300])
