"""ptmcp.term - drive the device's own terminal (the CLI window in PT).

* `run()`    executes whole lines through the IOS engine and reports the prompt
             after each one - proof the command really ran in that terminal.
* `type_()`  feeds text character by character via `enterChar`, i.e. exactly what
             a human typing on the keyboard does.
* `println()` writes a line into the terminal display, so an operator looking at
             the CLI sees the agent's note.

PT does not expose the terminal *scrollback*: `TerminalLine` gives prompt, mode,
pending input and a history wrapper whose entries are not text. So the result of
a command has to be read from device state (show run / vlan / ports) or from the
PDU simulation - never by scraping the console.
"""
from __future__ import annotations

import json
import time

from . import bridge
from .pt import _prelude


def state(device: str) -> dict:
    """Prompt, mode and pending input line of the device terminal."""
    js = _prelude() + f"""
var out = {{device: {bridge.q(device)}}};
try {{
  var d = ipc.network().getDevice({bridge.q(device)});
  if (!d) throw new Error("no device");
  var t = d.getIpcTerminalLine();
  out.prompt = t.getPrompt();
  out.mode = t.getMode();
  out.input = t.getCommandInput();
}} catch (e) {{ out.error = String(e); }}
throw new Error(JSON.stringify(out));
"""
    return json.loads(bridge.ask(js, timeout=30))


def run(device: str, lines: list[str]) -> dict:
    """Execute lines in the device terminal and record the prompt after each."""
    cmds = ", ".join(bridge.q(str(c).strip()) for c in lines)
    js = _prelude() + f"""
var out = {{device: {bridge.q(device)}, trace: []}};
try {{
  var d = ipc.network().getDevice({bridge.q(device)});
  if (!d) throw new Error("no device " + {bridge.q(device)});
  var t = d.getIpcTerminalLine();
  var cmds = [{cmds}];
  for (var i = 0; i < cmds.length; i++) {{
    var prompt = "";
    try {{
      d.enterCommand(cmds[i], "");
      prompt = t.getPrompt();
    }} catch (e) {{ prompt = "ERR " + e; }}
    out.trace.push(cmds[i] + " :: " + prompt);
  }}
  try {{ out.prompt = t.getPrompt(); out.mode = t.getMode(); }} catch (e) {{}}
}} catch (e) {{ out.fatal = String(e); }}
throw new Error(JSON.stringify(out));
"""
    data = json.loads(bridge.ask(js, timeout=90))
    data["sent"] = len(lines)
    return data


def type_(device: str, text: str, delay_ms: int = 0, enter: bool = True) -> dict:
    """Type text into the terminal one character at a time (human-like)."""
    js = _prelude() + f"""
var d = ipc.network().getDevice({bridge.q(device)});
if (!d) throw new Error("no device " + {bridge.q(device)});
var t = d.getIpcTerminalLine();
var s = {bridge.q(text)};
for (var i = 0; i < s.length; i++) {{ try {{ t.enterChar(s.charAt(i)); }} catch (e) {{}} }}
if ({str(enter).lower()}) {{ try {{ t.enterChar("\\r"); }} catch (e) {{}} }}
throw new Error("typed " + s.length);
"""
    bridge.ask(js, timeout=30)
    if delay_ms:
        time.sleep(delay_ms / 1000.0)
    return state(device)


def println(device: str, text: str) -> str:
    """Write a line into the device's terminal display (visible to a human)."""
    js = _prelude() + f"""
var d = ipc.network().getDevice({bridge.q(device)});
if (!d) throw new Error("no device " + {bridge.q(device)});
d.getIpcTerminalLine().println({bridge.q(text)});
throw new Error("printed");
"""
    return bridge.ask(js, timeout=30)


def ping(device: str, target: str, count: int = 4) -> dict:
    """Run `ping` inside the device terminal; the transcript stays in its CLI."""
    res = run(device, [f"ping {target} repeat {count}"])
    return {
        "device": device,
        "target": target,
        "executed": "fatal" not in res,
        "prompt_after": res.get("prompt"),
        "note": "open the device CLI to read 'Reply from ...'; use pdu.ping() for a verdict",
    }
