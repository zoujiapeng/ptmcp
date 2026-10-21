import pathlib
p = pathlib.Path("ptmcp/state.py"); s = p.read_text(encoding="utf-8")
old = '''    table = (("FastEthernet", "Fa"), ("GigabitEthernet", "Gi"),
             ("Ethernet", "Et"), ("Serial", "Se"), ("Vlan", "Vlan"))
    for long_name, prefix in table:
        if short.startswith(prefix):
            return long_name + short[len(prefix):]
    return short'''
new = '''    longs = ("FastEthernet", "GigabitEthernet", "Ethernet", "Serial", "Vlan")
    if short.startswith(longs):
        return short                      # already long form in running-config
    table = (("FastEthernet", "Fa"), ("GigabitEthernet", "Gi"),
             ("Ethernet", "Et"), ("Serial", "Se"))
    for long_name, prefix in table:
        if short.startswith(prefix):
            return long_name + short[len(prefix):]
    return short'''
assert old in s
p.write_text(s.replace(old, new), encoding="utf-8")
print("fixed _long_if")
