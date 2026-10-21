"""ptmcp.pdu - real ping verification through PT's simulation engine.

PT exposes the simulation and its PDU queue over IPC (the exact calls were
learned from cisco-pt-mcp's public extension source, MIT):

    ipc.simulation()                       -> setSimulationMode/forward/reset/
                                              getFrameInstanceCount/getFrameInstanceAt
    ipc.appWindow().getUserCreatedPDU()    -> addSimplePdu(src, dst)
    frameInstance                          -> getDevice(), getPreviousDevice(),
                                              getUserTrafficType(), isFrameAccepted(),
                                              isFrameDropped(), ...

A ping is *proven* rather than inferred: an ICMP echo request must be accepted
at the destination AND an echo reply must later be accepted back at the source.
Intermediate "accepted" hops (ARP, per-hop forwarding) do not count.
"""
from __future__ import annotations

import json

from . import bridge
from .pt import _prelude

_JS = """
var src = {src};
var dst = {dst};
var out = {{}};
var sim = ipc.simulation();
var wasSim = sim.isSimulationMode();
if (!wasSim) sim.setSimulationMode(true);
try {{ sim.resetSimulation(); }} catch (e) {{}}

if (!ipc.network().getDevice(src) || !ipc.network().getDevice(dst)) {{
  throw new Error(JSON.stringify({{error: "device not found", ok: false}}));
}}

var base = sim.getFrameInstanceCount();
var addErr = ipc.appWindow().getUserCreatedPDU().addSimplePdu(src, dst);
out.addError = String(addErr);

var traffic = {{"0": "ICMP", "5": "ARP", "7": "DHCP", "12": "OSPF", "11": "STP",
               "13": "DTP", "1": "TCP", "2": "UDP", "6": "CDP"}};
var lastCount = -1, stable = 0, steps = 0;
while (steps < {steps} && stable < 4) {{
  try {{ sim.forward(); }} catch (e) {{ out.forwardError = String(e); break; }}
  steps++;
  var c = sim.getFrameInstanceCount();
  if (c === lastCount) stable++; else {{ stable = 0; lastCount = c; }}
}}

var total = sim.getFrameInstanceCount();
var seq = [];
for (var i = base; i < total; i++) {{
  var fi = sim.getFrameInstanceAt(i);
  if (!fi) continue;
  var tName = traffic[String(fi.getUserTrafficType())] || String(fi.getUserTrafficType());
  if (tName !== "ICMP") continue;
  var status = "unknown";
  try {{
    if (fi.isFrameAccepted()) status = "accepted";
    else if (fi.isFrameDropped()) status = "dropped";
    else if (fi.isFrameNotForwarded()) status = "not_forwarded";
    else if (fi.isFrameUnexpected()) status = "unexpected";
    else if (fi.isFrameCollidedOnLink() || fi.isFrameCollidedAtDevice()) status = "collision";
    else if (fi.isFrameBuffered()) status = "buffered";
    else if (fi.isFrameOnTransit()) status = "in_transit";
    else if (fi.isFrameSent()) status = "sent";
  }} catch (e) {{}}
  var dev = "";
  try {{ var dv = fi.getDevice(); dev = (dv && dv.getName) ? dv.getName() : String(dv); }} catch (e) {{}}
  seq.push(dev + "|" + status);
  if (seq.length > 200) break;
}}

out.steps = steps;
out.totalFrames = total - base;
out.seq = seq;
if (!wasSim) {{ try {{ sim.setSimulationMode(false); }} catch (e) {{}} }}
throw new Error(JSON.stringify(out));
"""


def ping(source: str, destination: str, max_steps: int = 200, timeout: float = 150.0) -> dict:
    """ICMP reachability test through PT's simulation engine."""
    js = _prelude() + _JS.format(src=json.dumps(source), dst=json.dumps(destination),
                                 steps=int(max_steps))
    data = json.loads(bridge.ask(js, timeout=timeout))
    if data.get("error"):
        raise RuntimeError(data["error"])

    seq = [tuple(x.split("|", 1)) for x in data.get("seq", [])]
    reached_dst = any(dev == destination and st == "accepted" for dev, st in seq)
    replied = False
    if reached_dst:
        # reply = an accepted ICMP frame back at the source AFTER that point
        first_hit = next(i for i, (dev, st) in enumerate(seq)
                         if dev == destination and st == "accepted")
        replied = any(dev == source and st == "accepted" for dev, st in seq[first_hit + 1:])

    return {
        "source": source,
        "destination": destination,
        "ok": bool(reached_dst and replied),
        "reached_destination": reached_dst,
        "got_reply": replied,
        "add_error": data.get("addError"),
        "steps": data.get("steps"),
        "icmp_frames": len(seq),
        "trace": ["%s:%s" % (d, s) for d, s in seq[-14:]],
    }


def command_log(device: str | None = None, limit: int = 50) -> dict:
    """Read PT's own CLI command log (device, prompt, command)."""
    want = json.dumps(device) if device else "null"
    js = _prelude() + f"""
var log = ipc.commandLog();
try {{ log.setEnabled(true); }} catch (e) {{}}
var total = log.getEntryCount();
var want = {want};
var cap = {int(limit)};
var out = [];
for (var i = total - 1; i >= 0 && out.length < cap; i--) {{
  var e = log.getEntryAt(i);
  if (!e) continue;
  var dev = "";
  try {{ dev = e.getDeviceName(); }} catch (err) {{}}
  if (want && dev !== want) continue;
  var row = {{device: dev}};
  try {{ row.time = e.getTimeToString(); }} catch (err) {{}}
  try {{ row.command = e.getCommand(); }} catch (err) {{}}
  try {{ row.resolved = e.getResolvedCommand(); }} catch (err) {{}}
  out.push(row);
}}
throw new Error(JSON.stringify({{total: total, entries: out}}));
"""
    data = json.loads(bridge.ask(js, timeout=60))
    return {"total": data.get("total", 0), "entries": data.get("entries", [])}
