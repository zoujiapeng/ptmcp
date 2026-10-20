"""Diagnose why a tier does not reach all-up on the CURRENT canvas."""
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "tests"))

import bench  # noqa: E402
import ptmcp.pt as pt  # noqa: E402

tier = sys.argv[1] if len(sys.argv) > 1 else "4"
spec = bench.TIERS[tier]()
res = pt.verify_l2(spec)
for l in res["links"]:
    flag = "OK " if (l["a_up"] and l["b_up"]) else "DOWN"
    print(f'{flag} {l["a"]:28s} up={l["a_up"]!s:5s} mode={l["a_mode"]:2d} vlan={l["a_vlan"]:3d}'
          f'  <->  {l["b"]:28s} up={l["b_up"]!s:5s} mode={l["b_mode"]:2d} vlan={l["b_vlan"]:3d}')
