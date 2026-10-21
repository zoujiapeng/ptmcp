import pathlib
p = pathlib.Path("ptmcp/pdu.py"); s = p.read_text(encoding="utf-8")

s = s.replace('''var total = sim.getFrameInstanceCount();
var frames = [];
var accepted = 0, dropped = 0;''', '''var total = sim.getFrameInstanceCount();
var frames = [];
var accepted = 0, dropped = 0, lastIcmp = "none", lastIcmpIndex = -1;''')

s = s.replace('''  if (status === "accepted" && tName === "ICMP") accepted++;
  if (status === "dropped" && tName === "ICMP") dropped++;
  if (tName === "ICMP") {
    frames.push(i + " " + fi.getSourceString() + "->" + fi.getDestinationString() + " " + status);
  }''', '''  if (tName === "ICMP") {
    if (status === "accepted") accepted++;
    if (status === "dropped") dropped++;
    lastIcmp = status; lastIcmpIndex = i;
    frames.push(i + " " + status);
  }''')

s = s.replace('''out.steps = steps; out.totalFrames = total; out.accepted = accepted; out.dropped = dropped;''',
'''out.steps = steps; out.totalFrames = total; out.accepted = accepted; out.dropped = dropped;
out.lastIcmp = lastIcmp; out.lastIcmpIndex = lastIcmpIndex;''')

s = s.replace('''out.simModeRestored = wasSim ? false : true;
throw new Error(JSON.stringify(out));''', '''if (!wasSim) { try { sim.setSimulationMode(false); } catch (e) {} }
throw new Error(JSON.stringify(out));''')

s = s.replace('''    ok = data.get("accepted", 0) > 0 and data.get("addError") in ("0", "undefined", "")''',
'''    # verdict = status of the LAST ICMP frame: a completed exchange ends accepted,
    # a broken path ends dropped/not_forwarded (an accepted ARP/no-reply does not count)
    ok = data.get("lastIcmp") == "accepted" and data.get("addError") in ("0", "undefined", "")''')

s = s.replace('''        "accepted": data.get("accepted"),
        "dropped": data.get("dropped"),''','''        "accepted": data.get("accepted"),
        "dropped": data.get("dropped"),
        "last_icmp": data.get("lastIcmp"),''')

s = s.replace("def ping_pdu(source: str, destination: str, max_steps: int = 400, timeout: float = 120.0) -> dict:",
              "def ping_pdu(source: str, destination: str, max_steps: int = 160, timeout: float = 120.0) -> dict:")
p.write_text(s, encoding="utf-8")
print("patched verdict logic")
