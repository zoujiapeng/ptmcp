import pathlib
p = pathlib.Path("ptmcp/shot.py"); s = p.read_text(encoding="utf-8")
old = """                rect = wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                area = (rect.right - rect.left) * (rect.bottom - rect.top)
                found.append((area, hwnd))"""
new = """                rect = wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                area = (rect.right - rect.left) * (rect.bottom - rect.top)
                title = buf.value
                # prefer the main app window; skip tool windows (Logs, Scripting, dialogs)
                rank = 2 if title.startswith("Cisco Packet Tracer") else 1
                if any(bad in title for bad in ("Logs", "Scripting -", "Configure PT", "Login", "Overwrite", "New --")):
                    rank = 0
                found.append((rank, area, hwnd))"""
assert old in s
s = s.replace(old, new)
s = s.replace("return max(found)[1] if found else None", "return max(found)[2] if found else None")
p.write_text(s, encoding="utf-8")
print("patched window ranking")
