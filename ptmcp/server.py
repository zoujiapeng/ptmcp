"""ptmcp.server - MCP (stdio) server for background Packet Tracer control.

Register in any MCP client, e.g.:

    claude mcp add --scope user --transport stdio ptmcp -- python -m ptmcp serve

Tools are deliberately few and text-returning, so an agent can chain them
without guessing: status -> build -> ping -> save.
"""
from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from . import bridge, pt

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
