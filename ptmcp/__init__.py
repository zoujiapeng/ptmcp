"""ptmcp - dialog-free, agent-friendly control of Cisco Packet Tracer 8.x."""
from . import asserts, bridge, catalog, fix, ops, pt, shot, state, ui  # noqa: F401

__version__ = "1.6.0"
__all__ = ["asserts", "fix", "shot", "bridge", "catalog", "ops", "pt", "state", "ui", "__version__"]
