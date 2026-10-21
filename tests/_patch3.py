import pathlib
p = pathlib.Path("ptmcp/asserts.py"); s = p.read_text(encoding="utf-8")
old = """            ports.setdefault(f[1], {})[f[2]] = {
                "up": f[3] == "1", "proto": f[4] == "1", "mode": int(f[5]),
                "vlan": int(f[6]), "native": int(f[7]), "linked": f[8] == "1",
            }
    return {"devices": devices, "ports": ports}"""
new = """            ports.setdefault(f[1], {})[f[2]] = {
                "up": f[3] == "1", "proto": f[4] == "1", "mode": int(f[5]),
                "vlan": int(f[6]), "native": int(f[7]), "linked": f[8] == "1",
            }
    # Some models (3560 FastEthernet) do not expose admin-mode/VLAN getters at
    # all and answer -1. Fall back to the running-config for those ports.
    from . import state as _st
    for dev, devports in ports.items():
        if not any(p.get("mode", -1) < 0 for p in devports.values()):
            continue
        try:
            cfg = _st.interface_config(dev)
        except Exception:                                      # noqa: BLE001
            continue
        for name, info in devports.items():
            conf = cfg.get(name)
            if not conf:
                continue
            if info.get("mode", -1) < 0:
                info["mode"] = 2 if conf.get("mode") == "trunk" else (1 if conf.get("mode") == "access" else -1)
            if info.get("vlan", -1) < 0 and conf.get("access_vlan"):
                info["vlan"] = conf["access_vlan"]
            if info.get("native", -1) < 0:
                info["native"] = conf.get("native") or 1
    return {"devices": devices, "ports": ports}"""
assert old in s
p.write_text(s.replace(old, new), encoding="utf-8")
print("patched asserts with config fallback")
