import pathlib
p = pathlib.Path("ptmcp/bootstrap.py"); s = p.read_text(encoding="utf-8")
s = s.replace('''    if not bridge.alive():
        print(
            "\\nOne-time GUI step (PT has no silent module registration):\\n"
            "  Packet Tracer > Extensions > Scripting > Configure PT Script Modules\\n"
            "  > select 'MCP BUILDER' > Settings > 'On Startup' > Start\\n"
            "After that, every later session is fully headless."
        )
        return 2''',
'''    if not bridge.alive():
        print("\\nPT is not polling yet. Run `python -m ptmcp start` - PT auto-loads "
              "script modules from <install>\\\\extensions\\\\ at launch, so no GUI step "
              "is normally needed. If it still does not poll, register once via\\n"
              "  Extensions > Scripting > Configure PT Script Modules > MCP BUILDER > Start")
        return 2''')
p.write_text(s, encoding="utf-8")
print("bootstrap text updated")
