"""ptmcp.catalog - PT 8 device types and cable rules (from PT's own catalogs)."""
from __future__ import annotations

# PT internal device type ids (LogicalWorkspace.addDevice's first argument).
DEVICE_TYPES: dict[str, int] = {
    # routers (type 0)
    "1841": 0, "1941": 0, "2620XM": 0, "2621XM": 0, "2811": 0, "2901": 0,
    "2911": 0, "819HG-4G-IOX": 0, "819HGW": 0, "829": 0, "CGR1240": 0,
    "ISR4321": 0, "ISR4331": 0, "Router-PT": 0, "Router-PT-Empty": 0,
    # switches (1) / multilayer (16)
    "2950-24": 1, "2950T-24": 1, "2960-24TT": 1, "Switch-PT": 1, "Switch-PT-Empty": 1,
    "3560-24PS": 16, "3650-24PS": 16, "IE-2000": 16,
    # infrastructure
    "Cloud-PT": 2, "Cloud-PT-Empty": 2, "Bridge-PT": 3, "Hub-PT": 4, "Repeater-PT": 5,
    "AccessPoint-PT": 7, "AccessPoint-PT-A": 7, "AccessPoint-PT-AC": 7, "AccessPoint-PT-N": 7,
    # end devices
    "PC-PT": 8, "Server-PT": 9, "Printer-PT": 10, "Laptop-PT": 17, "TabletPC-PT": 18,
    "SMARTPHONE-PT": 20, "TV-PT": 22, "IP-Phone": 12, "7960": 12,
    # wireless / controllers
    "WLC-2504": 41, "WLC-3504": 41, "WLC-PT": 41, "3702i": 44, "LAP-PT": 44,
    "Linksys-WRT300N": 11, "HomeRouter-PT-AC": 30,
    # security
    "5505": 27, "5506-X": 27, "Sniffer": 35,
}

# PT internal link type ids (LogicalWorkspace.createLink's last argument).
CABLES: dict[str, int] = {
    "straight": 8100, "ethernet-straight": 8100,
    "cross": 8101, "crossover": 8101, "ethernet-cross": 8101,
    "roll": 8102, "fiber": 8103, "phone": 8104, "cable": 8105, "serial": 8106,
    "auto": 8107, "console": 8108, "wireless": 8109, "coaxial": 8110,
    "octal": 8111, "cellular": 8112, "usb": 8113,
}

SWITCH_LIKE = {1, 3, 4, 5, 16}      # switch / bridge / hub / repeater / MLS
ROUTER_LIKE = {0}
HOST_LIKE = {8, 9, 10, 12, 17, 18, 19, 20, 22, 23, 24, 25}


def device_type(model: str) -> int:
    try:
        return DEVICE_TYPES[model]
    except KeyError:
        raise ValueError(
            f"unknown PT model {model!r}. Known: " + ", ".join(sorted(DEVICE_TYPES))
        ) from None


def pick_cable(a_type: int, b_type: int) -> int:
    """Copper cable PT will actually bring up (the #1 cause of red links).

    PT enforces MDI/MDI-X: same-class copper peers (switch<->switch,
    router<->router, hub<->hub, switch<->hub...) need a crossover; host links
    and router<->switch need straight-through.
    """
    if a_type in SWITCH_LIKE and b_type in SWITCH_LIKE:
        return CABLES["cross"]
    if a_type in ROUTER_LIKE and b_type in ROUTER_LIKE:
        return CABLES["cross"]
    if a_type in HOST_LIKE and b_type in HOST_LIKE:
        return CABLES["cross"]
    return CABLES["straight"]


def cable_id(name: str | int | None, a_type: int, b_type: int) -> int:
    if name in (None, "", "auto", "choose"):
        return pick_cable(a_type, b_type)
    if isinstance(name, int):
        return name
    key = str(name).lower()
    if key not in CABLES:
        raise ValueError(f"unknown cable {name!r}; known: {', '.join(sorted(CABLES))}")
    return CABLES[key]
