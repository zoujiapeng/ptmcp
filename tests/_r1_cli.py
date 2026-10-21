import json, sys
sys.path.insert(0, ".")
import ptmcp.term as term
spec = json.loads(open("specs/campus.json", encoding="utf-8").read())
cmds = spec["cli"]["R1"]
res = term.run("R1", cmds)
for t in res["trace"]:
    print("  ", t)
