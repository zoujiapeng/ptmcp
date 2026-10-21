import pathlib
p = pathlib.Path("ptmcp/pdu.py"); s = p.read_text(encoding="utf-8")

s = s.replace('''    seq = [tuple(x.split("|", 1)) for x in data.get("seq", [])]
    reached_dst = any(dev == destination and st == "accepted" for dev, st in seq)
    replied = False
    if reached_dst:
        # reply = an accepted ICMP frame back at the source AFTER that point
        first_hit = next(i for i, (dev, st) in enumerate(seq)
                         if dev == destination and st == "accepted")
        replied = any(dev == source and st == "accepted" for dev, st in seq[first_hit + 1:])''',
'''    seq = [tuple(x.split("|", 1)) for x in data.get("seq", [])]
    # PT marks the frame at the destination as "sent" (it is handed to the host),
    # and the echo reply shows up as "accepted" back at the source.
    reached_dst = any(dev == destination for dev, _ in seq)
    replied = False
    if reached_dst:
        first_hit = next(i for i, (dev, _) in enumerate(seq) if dev == destination)
        replied = any(dev == source and st == "accepted" for dev, st in seq[first_hit + 1:])''')

s = s.replace('''def ping(source: str, destination: str, max_steps: int = 200, timeout: float = 150.0) -> dict:
    """ICMP reachability test through PT's simulation engine."""
    js = _prelude() + _JS.format''','''def ping(source: str, destination: str, max_steps: int = 200, timeout: float = 150.0,
         settle: float = 20.0) -> dict:
    """ICMP reachability test through PT's simulation engine.

    PT needs a moment after the topology is built (hosts boot, switch ports start
    forwarding) before a Simple PDU can leave the source; without the settle the
    first frames are dropped and the verdict is a false negative.
    """
    if settle:
        deadline = time.time() + settle
        while time.time() < deadline:
            if _ports_ready(source, destination):
                break
            time.sleep(2)
    js = _prelude() + _JS.format''')

s = s.replace('''import json

from . import bridge''','''import json
import time

from . import bridge''')

s = s.replace('''def command_log(''','''def _ports_ready(a: str, b: str) -> bool:
    js = _prelude() + f"""
var ok = true;
var names = [{json.dumps(a)}, {json.dumps(b)}];
for (var i = 0; i < names.length; i++) {{
  var d = ipc.network().getDevice(names[i]);
  if (!d) {{ ok = false; continue; }}
  var ports = d.getPorts();
  var any = false;
  for (var p = 0; p < ports.length; p++) {{
    var po = d.getPort(ports[p]);
    if (po && po.isPortUp && po.isPortUp()) {{ any = true; break; }}
  }}
  if (!any) ok = false;
}}
throw new Error(ok ? "1" : "0");
"""
    return (bridge.ask(js, timeout=20) or "").strip() == "1"


def command_log(''')
p.write_text(s, encoding="utf-8")
import ast; ast.parse(s)
print("patched pdu.ping verdict + settle")
