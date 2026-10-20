"""End-to-end check: build a spec, wait for links, read VLAN state, run ping."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ptmcp.pt as pt  # noqa: E402


def run(spec_path: str) -> None:
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    res = pt.build(spec)
    print("BUILD:", res["build"][:500])
    print("LINKS:", json.dumps(res.get("link_check"), ensure_ascii=False))
    print("SAVE :", res.get("save"))
    for l in pt.verify_l2(spec)["links"]:
        print("  {a}(up={au},mode={am},vlan={av}) <-> {b}(up={bu},mode={bm},vlan={bv})".format(
            a=l["a"], au=l["a_up"], am=l["a_mode"], av=l["a_vlan"],
            b=l["b"], bu=l["b_up"], bm=l["b_mode"], bv=l["b_vlan"]))
    if spec.get("ping"):
        print("PING :", json.dumps(pt.ping(*spec["ping"]), ensure_ascii=False))


if __name__ == "__main__":
    run(sys.argv[1])
