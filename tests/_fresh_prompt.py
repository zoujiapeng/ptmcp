import json, sys, time
sys.path.insert(0, ".")
import ptmcp.pt as pt
spec = json.loads(open("specs/case27.json", encoding="utf-8").read())
r = pt.build(spec)
print("build allUp:", r["link_check"]["allUp"], "| cli_ready:", r.get("cli_ready"))
time.sleep(2)
print("prompt S1:", pt.ask(pt._prelude() + "throw new Error(ipc.network().getDevice('S1').getIpcTerminalLine().getPrompt());"))
print("hostname applied:", "hostname S1" in __import__("ptmcp.state", fromlist=["x"]).running_config("S1"))
