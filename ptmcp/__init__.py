"""ptmcp - dialog-free, agent-friendly control of Cisco Packet Tracer 8.x."""
from . import bridge, catalog, pt  # noqa: F401

__version__ = "1.0.0"
__all__ = ["bridge", "catalog", "pt", "__version__"]
