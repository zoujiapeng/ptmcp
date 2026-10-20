"""Build the OSPF tier and dump the router XML so we can find route/neighbour tags."""
import sys
from collections import Counter
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "tests"))

import bench  # noqa: E402
import ptmcp.pt as pt  # noqa: E402
import ptmcp.state as st  # noqa: E402

spec = bench.tier2()
spec["save"] = r"C:\pt\ospf_probe.pkt"
print("build:", pt.build(spec)["build"][:200])
xml = st.device_xml("R1")
Path("tests/_r1.xml").write_text(xml, encoding="utf-8")
tags = Counter(re.findall(r"<([A-Za-z0-9_]+)[ >]", xml))
interesting = {k: v for k, v in tags.items()
               if any(w in k.upper() for w in ("ROUT", "OSPF", "NEIGH", "ARP", "TABLE", "STATIC", "RIP", "EIGRP"))}
print("len:", len(xml))
print("interesting:", interesting)
for key in ("ROUTING_TABLE", "ROUTES", "ROUTE", "OSPF", "NEIGHBORS", "ARP"):
    i = xml.find(f"<{key}")
    if i >= 0:
        print(f"--- {key} ---")
        print(xml[i:i + 500].replace("\n", " "))
