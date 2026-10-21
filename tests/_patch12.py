import pathlib
p = pathlib.Path("ptmcp/pt.py"); s = p.read_text(encoding="utf-8")
old = '''    if spec.get("asserts"):
        from .asserts import check as _check
        try:
            report["asserts"] = _check(spec)
        except Exception as exc:                               # noqa: BLE001
            report["asserts"] = {"ok": None, "error": str(exc)}'''
new = '''    if spec.get("asserts"):
        from .asserts import check as _check
        try:
            report["asserts"] = _check(spec)
            # Self-heal: cold starts can drop a few CLI lines, so re-run the
            # declared assertions and repair instead of reporting a half-built lab.
            if not report["asserts"].get("ok"):
                from .fix import fix_loop as _fix
                report["self_heal"] = _fix(spec, rounds=2)
                report["asserts_after_heal"] = _check(spec)
                report["asserts"] = report["asserts_after_heal"]
        except Exception as exc:                               # noqa: BLE001
            report["asserts"] = {"ok": None, "error": str(exc)}'''
assert old in s
p.write_text(s.replace(old, new), encoding="utf-8")
import ast; ast.parse(pathlib.Path("ptmcp/pt.py").read_text(encoding="utf-8"))
print("build() now self-heals")
