import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ptmcp.pt as pt

raw = pt.ask(pt._prelude() + """
var p = ipc.network().getDevice('S1').getPort('FastEthernet0/13');
throw new Error([p.isPortUp() ? 1 : 0, p.getAdminOpMode(), p.getAccessVlan()].join('~'));
""")
print("RAW:", repr(raw))
print("VERIFY:", pt.verify_l2({"links": [{"a": "S1", "a_port": "FastEthernet0/13",
                                          "b": "S2", "b_port": "FastEthernet0/13"}]}))
