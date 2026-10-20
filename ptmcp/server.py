"""ptmcp.server - MCP (stdio) server for background Packet Tracer control.

Register in any MCP client, e.g.:

    claude mcp add --scope user --transport stdio ptmcp -- python -m ptmcp serve

Tools are deliberately few and text-returning, so an agent can chain them
without guessing: status -> build -> ping -> save.
"""
from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from . import bridge, ops, pt, state, ui

mcp = FastMCP(
    "packet-tracer",
    instructions=(
        "Control a running Cisco Packet Tracer 8.x in the background (no focus, "
        "no dialogs). Build topologies with pt_build (devices/links/ips/cli), "
        "wait for links to come up with pt_wait_links, verify reachability with "
        "pt_ping, persist with pt_save. Cables are auto-selected (switch<->switch "
        "gets a crossover), which is what makes links turn green."
    ),
)


def _need_engine() -> None:
    if not bridge.alive():
        raise RuntimeError(
            "Packet Tracer script engine is not polling. Open PT and start the "
            "MCP BUILDER module (Extensions > Scripting > Configure PT Script "
            "Modules), or run `python -m ptmcp bootstrap` on the host."
        )


@mcp.tool()
def pt_status() -> str:
    """Devices/links on the active PT canvas, plus engine liveness."""
    if not bridge.alive():
        return json.dumps({"alive": False, "hint": "start the MCP BUILDER module in PT"})
    return json.dumps(pt.status(), ensure_ascii=False)


@mcp.tool()
def pt_new() -> str:
    """Discard the current canvas and start a clean topology (no dialogs)."""
    _need_engine()
    return pt.new_canvas()


@mcp.tool()
def pt_build(spec_json: str, save_path: str = "") -> str:
    """Build a topology from JSON and report per-link up/down.

    {"devices":[{"name":"S1","model":"2950T-24","x":260,"y":140},
                {"name":"PC0","model":"PC-PT","x":150,"y":400}],
     "links":[{"a":"S1","a_port":"FastEthernet0/1","b":"PC0","b_port":"FastEthernet0"}],
     "ips":[{"device":"PC0","port":"FastEthernet0","ip":"192.168.2.1","mask":"255.255.255.0"}],
     "cli":{"S1":["vlan 2","name VLAN2","exit"]}}

    `cable` may be omitted: cross is chosen automatically for switch<->switch
    and router<->router, straight-through otherwise.
    """
    _need_engine()
    spec = json.loads(spec_json)
    return json.dumps(pt.build(spec, save_to=save_path or spec.get("save")),
                      ensure_ascii=False, indent=2)


@mcp.tool()
def pt_wait_links(spec_json: str, timeout_s: int = 45) -> str:
    """Poll until every link in the spec has both ports up (STP convergence)."""
    _need_engine()
    return json.dumps(pt.wait_links_up(json.loads(spec_json), timeout=timeout_s),
                      ensure_ascii=False, indent=2)


@mcp.tool()
def pt_cli(device: str, commands: str) -> str:
    """Run CLI lines on an IOS device (newline-separated) and return its screen."""
    _need_engine()
    return pt.cli(device, [c for c in commands.splitlines() if c.strip()])


@mcp.tool()
def pt_ping(source: str, target_ip: str, count: int = 4) -> str:
    """Ping from `source` and return verdict UP/DOWN with the raw CLI output."""
    _need_engine()
    return json.dumps(pt.ping(source, target_ip, count), ensure_ascii=False, indent=2)


@mcp.tool()
def pt_save(path: str) -> str:
    """Save the topology as .pkt. Never raises an overwrite dialog."""
    _need_engine()
    return pt.save(path)


@mcp.tool()
def pt_run_js(code: str) -> str:
    """Escape hatch: run JS in PT's script engine; end with `throw new Error(text)`."""
    _need_engine()
    return bridge.ask(code, timeout=30)

# ---------------------------------------------------------------- read back


@mcp.tool()
def pt_show(device: str, what: str = "run") -> str:
    """Read device state like the CLI does: run | vlan | vtp | mac | interfaces.

    This is real read-back, not screen scraping: PT serialises each device to
    XML and we parse the running-config lines, the VLAN database, VTP status
    and per-port state out of it.
    """
    _need_engine()
    return json.dumps(state.show(device, what), ensure_ascii=False, indent=2)


@mcp.tool()
def pt_batch(ops_json: str) -> str:
    """Run many operations in ONE round-trip (fast path for complex scripts).

    [{"op":"cli","device":"S1","commands":["vlan 2","exit"]},
     {"op":"ip","device":"PC1","port":"FastEthernet0","ip":"10.0.0.1","mask":"255.255.255.0"},
     {"op":"port","device":"S1","port":"FastEthernet0/1","mode":1,"access_vlan":20},
     {"op":"power","device":"R1","on":true},
     {"op":"rename","device":"S1","to":"CORE"},
     {"op":"module","device":"R1","slot":0,"model":"HWIC-2T"}]
    """
    _need_engine()
    return json.dumps(ops.batch(json.loads(ops_json)), ensure_ascii=False, indent=2)


@mcp.tool()
def pt_power(device: str, on: bool = True) -> str:
    """Power a device on or off (the physical switch)."""
    _need_engine()
    return ops.power(device, on)


@mcp.tool()
def pt_rename(device: str, new_name: str) -> str:
    """Rename a device (display name + IOS hostname)."""
    _need_engine()
    return ops.rename(device, new_name)


@mcp.tool()
def pt_add_module(device: str, slot: int, model: str) -> str:
    """Insert a hardware module, e.g. HWIC-2T / NM-ESW-161 into a slot."""
    _need_engine()
    return ops.add_module(device, slot, model)


# ------------------------------------------------------------------- the UI


@mcp.tool()
def pt_ui_controls() -> str:
    """List everything the UI layer can drive (modes, panels, window, state)."""
    _need_engine()
    return json.dumps(ui.controls(), ensure_ascii=False, indent=2)


@mcp.tool()
def pt_view_state() -> str:
    """Workspace/UI state: logical vs physical, realtime vs simulation, geometry."""
    _need_engine()
    return json.dumps(ui.view_state(), ensure_ascii=False)


@mcp.tool()
def pt_switch_mode(mode: str) -> str:
    """Switch mode: logical | physical | realtime | simulation."""
    _need_engine()
    return ui.switch_mode(mode)


@mcp.tool()
def pt_panels(left: bool = True, bottom: bool = True) -> str:
    """Show/hide the device box (left pane) and the PDU/event list (bottom pane)."""
    _need_engine()
    return json.dumps(ui.panels(left, bottom), ensure_ascii=False)


@mcp.tool()
def pt_window(action: str = "maximize", width: int = 0, height: int = 0) -> str:
    """Window geometry: maximize | normal | geometry."""
    _need_engine()
    return json.dumps(ui.window(action, width, height), ensure_ascii=False)


@mcp.tool()
def pt_clipboard(text: str = "") -> str:
    """Read PT's clipboard, or write `text` into it when given."""
    _need_engine()
    return ui.clipboard(text or None)


@mcp.tool()
def pt_status_line(text: str) -> str:
    """Write a line into PT's own console/status area."""
    _need_engine()
    return ui.status_line(text)

@mcp.tool()
def pt_precheck(spec_json: str, fix: bool = False) -> str:
    """Validate a topology spec before building it (ports, cables, duplicates).

    Catches the three failure modes that used to turn links red or make them
    disappear: a port that does not exist, a port already in use, and a
    switch<->switch link on a straight-through cable. fix=true repairs cables and
    moves links to the next free port, returning a patched spec.
    """
    from .precheck import precheck
    return json.dumps(precheck(json.loads(spec_json), fix=fix), ensure_ascii=False, indent=2)


@mcp.tool()
def pt_routing(device: str) -> str:
    """Routing configuration of a device (protocols, networks, static routes).

    Config-level only: PT's engine XML has no live routing table or OSPF
    neighbour state, so use pt_ping / pt_verify_l2 for reachability.
    """
    _need_engine()
    return json.dumps(state.routing(device), ensure_ascii=False, indent=2)
