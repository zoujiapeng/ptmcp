import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ptmcp.pt as pt  # noqa: E402

xml = pt.ask("""
var d = ipc.network().getDevice('S1');
throw new Error("<<XML>>" + d.serializeToXml() + "<<END>>");
""", timeout=40)
body = xml.split("<<XML>>")[1].split("<<END>>")[0]
Path("tests/_s1.xml").write_text(body, encoding="utf-8")
tags = Counter(re.findall(r"<([A-Za-z0-9_]+)[ >]", body))
print("len:", len(body))
print("tags:", tags.most_common(30))
for key in ("VLAN", "IP", "PORT"):
    i = body.find(f"<{key}>")
    if i >= 0:
        print(f"--- {key} @{i} ---")
        print(body[i:i + 400].replace("\n", " "))
