import json, sys
sys.path.insert(0, ".")
import ptmcp.term as term
print("state     :", json.dumps(term.state("S1"), ensure_ascii=False))
print("run       :", json.dumps(term.run("S1", ["enable", "configure terminal", "hostname CORE1", "exit"]), ensure_ascii=False)[:300])
print("type_     :", json.dumps(term.type_("S1", "show vlan brief", enter=True), ensure_ascii=False)[:200])
print("println   :", term.println("S1", "== ptmcp: terminal under agent control =="))
print("show run  :", "hostname CORE1" in __import__("ptmcp.state", fromlist=["x"]).running_config("S1"))
