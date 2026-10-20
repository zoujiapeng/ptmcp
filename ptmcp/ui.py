"""ptmcp.ui - scriptable UI control for Packet Tracer.

What PT 8 actually exposes over IPC (verified on 8.0.0.0212):
    isLogicalMode / isPhysicalMode / isRealtimeMode / isSimulationMode
    getPLSwitch().setLogicalMode(bool)     -> logical <-> physical workspace
    getRSSwitch().setRealtimeMode(bool)    -> realtime <-> simulation
    setPLFrameVisible / setRSFrameVisible  -> show/hide the left & bottom panes
    showMaximized / showNormal / setWindowGeometry / setVisible
    getWidth/getHeight/getX/getY, getClipboardText/setClipboardText, writeToPT

Menu item *enumeration* is deliberately not offered: Qt builds a QMenu's actions
lazily, so before the menu is opened `count()` returns 0 and the item list comes
back empty on PT 8 (confirmed). Everything an agent needs from those menus has a
scriptable equivalent here; anything only reachable by a real click belongs to
the computer-use layer, not to this bridge.
"""
from __future__ import annotations

from . import bridge
from .pt import _prelude


def view_state() -> dict:
    """Workspace/UI state: mode flags and window geometry."""
    js = _prelude() + """
var aw = ipc.appWindow();
throw new Error([
  "logical_mode=" + aw.isLogicalMode(),
  "physical_mode=" + aw.isPhysicalMode(),
  "realtime=" + aw.isRealtimeMode(),
  "simulation=" + aw.isSimulationMode(),
  "width=" + aw.getWidth(), "height=" + aw.getHeight(),
  "x=" + aw.getX(), "y=" + aw.getY()
].join(" "));
"""
    out: dict[str, object] = {}
    for part in bridge.ask(js).split():
        if "=" in part:
            k, _, v = part.partition("=")
            out[k] = v if k in ("width", "height", "x", "y") else v == "true"
    return out


def switch_mode(mode: str) -> str:
    """logical | physical | realtime | simulation."""
    mode = mode.lower()
    js = _prelude() + f"""
var aw = ipc.appWindow();
var what = {bridge.q(mode)};
if (what === "logical") {{ aw.getPLSwitch().showLogicalMode(); }}
else if (what === "physical") {{ aw.getPLSwitch().showPhysicalMode(); }}
else if (what === "realtime") {{ aw.getRSSwitch().showRealtimeMode(); }}
else if (what === "simulation") {{ aw.getRSSwitch().showSimulationMode(); }}
else throw new Error("mode must be logical|physical|realtime|simulation");
throw new Error("mode -> " + what + " (logical=" + aw.isLogicalMode() +
                " realtime=" + aw.isRealtimeMode() + ")");
"""
    return bridge.ask(js)


def panels(left: bool | None = None, bottom: bool | None = None) -> dict:
    """Show/hide the component box (left) and the PDU/event list (bottom)."""
    js = _prelude() + f"""
var aw = ipc.appWindow();
if ({str(left is not None).lower()}) aw.setPLFrameVisible({"true" if left else "false"});
if ({str(bottom is not None).lower()}) aw.setRSFrameVisible({"true" if bottom else "false"});
throw new Error("panels applied");
"""
    bridge.ask(js)
    return view_state()


def window(action: str = "maximize", width: int = 0, height: int = 0) -> dict:
    """Window geometry: maximize | normal | geometry."""
    action = action.lower()
    js = _prelude() + f"""
var aw = ipc.appWindow();
var a = {bridge.q(action)};
if (a === "maximize") aw.showMaximized();
else if (a === "normal") aw.showNormal();
else if (a === "geometry") aw.setWindowGeometry({int(width)}, {int(height)});
else throw new Error("action must be maximize|normal|geometry");
throw new Error("window " + a);
"""
    bridge.ask(js)
    return view_state()


def clipboard(text: str | None = None) -> str:
    """Read or write PT's clipboard."""
    if text is None:
        return bridge.ask(_prelude() + "throw new Error(ipc.appWindow().getClipboardText());")
    return bridge.ask(_prelude() +
                      f"ipc.appWindow().setClipboardText({bridge.q(text)}); throw new Error('clipboard set');")


def status_line(text: str) -> str:
    """Write a line into PT itself (PT's own console/status area)."""
    return bridge.ask(_prelude() +
                      f"ipc.appWindow().writeToPT({bridge.q(text)}); throw new Error('written');")


def controls() -> dict:
    """Everything the UI layer can drive, plus current state - one call."""
    return {
        "modes": ["logical", "physical", "realtime", "simulation"],
        "panels": ["left: device box", "bottom: PDU/event list"],
        "window": ["maximize", "normal", "geometry"],
        "clipboard": True,
        "status_line": True,
        "state": view_state(),
    }

