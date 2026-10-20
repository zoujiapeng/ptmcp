#!/usr/bin/env python
"""ptmcp.py - MCP (stdio) server that drives Cisco Packet Tracer in the background.

Unlike the shipped `packet-tracer-mcp`, this server does not rely on the
extension's JS helper layer (whose `addDevice`/`addLink` globals do not exist on
PT 8.0). It speaks PT 8's native IPC API through the mailbox that the
MCP-BUILDER script module polls, so it works with PT's window closed, minimised
or behind other apps.

Register in any MCP client, e.g. Claude Code:

    claude mcp add --scope user --transport stdio pt8 "--" python C:\\Users\\zou\\八爪鱼下载\\pt-mcp\\ptmcp.py

Tools:
    pt_status()                      devices + links on the active canvas
    pt_build(spec_json, save_path)   build a topology from a JSON spec
    pt_add_device(name, model, x, y)
    pt_add_link(a, a_port, b, b_port, cable)
    pt_set_ip(device, port, ip, mask, gateway)
    pt_save(path)                    File > Save As
    pt_js(code)                      run arbitrary JS in PT's script engine
    pt_alive()                       is the script engine polling?
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ptctl  # noqa: E402

from mcp.server.fastmcp import FastMCP  # noqa: E402

mcp = FastMCP("packet-tracer-8-background")


@mcp.tool()
def pt_alive() -> str:
    """Return whether Packet Tracer's script engine is polling the mailbox."""
    return "alive" if ptctl.pt_alive() else "not alive - open PT and start the MCP BUILDER module"


@mcp.tool()
def pt_status() -> str:
    """List devices and links currently on the logical canvas."""
    return ptctl.status()


@mcp.tool()
def pt_build(spec_json: str, save_path: str = "") -> str:
    """Build a topology from a JSON spec.

    spec_json example:
    {"devices":[{"name":"R1","model":"2911","x":240,"y":140}],
     "links":[{"a":"R1","a_port":"GigabitEthernet0/0","b":"SW1","b_port":"GigabitEthernet0/1","cable":"straight"}],
     "ips":[{"device":"PC1","port":"FastEthernet0","ip":"192.168.1.10","mask":"255.255.255.0","gateway":"192.168.1.1"}]}
    """
    spec = json.loads(spec_json)
    return ptctl.build(spec, save_to=save_path or spec.get("save"))


@mcp.tool()
def pt_add_device(name: str, model: str, x: int = 200, y: int = 200) -> str:
    """Add one device (model e.g. 2911, 2960-24TT, PC-PT, Server-PT, 3560-24PS)."""
    return ptctl.build({"devices": [{"name": name, "model": model, "x": x, "y": y}]})


@mcp.tool()
def pt_add_link(a: str, a_port: str, b: str, b_port: str, cable: str = "straight") -> str:
    """Connect two devices. cable: straight | cross | serial | fiber | console | auto."""
    return ptctl.build(
        {"links": [{"a": a, "a_port": a_port, "b": b, "b_port": b_port, "cable": cable}]}
    )


@mcp.tool()
def pt_set_ip(device: str, port: str, ip: str, mask: str, gateway: str = "") -> str:
    """Set an IPv4 address (and optional default gateway) on a device port."""
    entry = {"device": device, "port": port, "ip": ip, "mask": mask}
    if gateway:
        entry["gateway"] = gateway
    return ptctl.build({"ips": [entry]})


@mcp.tool()
def pt_save(path: str) -> str:
    """Save the topology as a .pkt file (Path must not already exist - PT prompts on overwrite)."""
    return ptctl.save(path)


@mcp.tool()
def pt_js(code: str) -> str:
    """Run raw JavaScript inside Packet Tracer's script engine and return its text.

    The code must end with `throw new Error(<text>)` to return a value.
    """
    return ptctl.ask(code, timeout=25)


if __name__ == "__main__":
    mcp.run(transport="stdio")
