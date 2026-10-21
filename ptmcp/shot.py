"""ptmcp.shot - capture the Packet Tracer window without any GUI automation.

No mouse, no keyboard, no accessibility calls: this asks Windows to render the
window into a bitmap (PrintWindow with PW_RENDERFULLCONTENT), which works even
when PT is behind other windows. Output goes through Pillow to PNG.

    from ptmcp.shot import capture
    capture(r"C:\\pt\\canvas.png")
"""
from __future__ import annotations

import ctypes
import subprocess
from ctypes import wintypes
from pathlib import Path

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

PW_RENDERFULLCONTENT = 0x00000002
BI_RGB = 0
DIB_RGB_COLORS = 0


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


def _pt_pid() -> int | None:
    out = subprocess.run(["tasklist", "/fi", "IMAGENAME eq PacketTracer.exe", "/fo", "csv", "/nh"],
                         capture_output=True, text=True, timeout=20).stdout
    for line in out.splitlines():
        if line.lower().startswith('"packettracer.exe'):
            return int(line.split('","')[1])
    return None


def _main_window(pid: int) -> int | None:
    found: list[tuple[int, int]] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _):
        wpid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
        if wpid.value == pid and user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                rect = wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                area = (rect.right - rect.left) * (rect.bottom - rect.top)
                title = buf.value
                # prefer the main app window; skip tool windows (Logs, Scripting, dialogs)
                rank = 2 if title.startswith("Cisco Packet Tracer") else 1
                if any(bad in title for bad in ("Logs", "Scripting -", "Configure PT", "Login", "Overwrite", "New --")):
                    rank = 0
                found.append((rank, area, hwnd))
        return True

    user32.EnumWindows(cb, 0)
    return max(found)[2] if found else None


def capture(path: str, hwnd: int | None = None) -> str:
    """Render PT's window to `path` (PNG). Returns the path."""
    from PIL import Image  # local import: Pillow is optional for the rest

    pid = _pt_pid()
    if not pid:
        raise RuntimeError("Packet Tracer is not running")
    hwnd = hwnd or _main_window(pid)
    if not hwnd:
        raise RuntimeError("no visible Packet Tracer window")

    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    width, height = rect.right - rect.left, rect.bottom - rect.top
    if width <= 0 or height <= 0:
        raise RuntimeError(f"window has no drawable size ({width}x{height})")

    hdc = user32.GetWindowDC(hwnd)
    mem_dc = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, width, height)
    gdi32.SelectObject(mem_dc, bmp)

    ok = user32.PrintWindow(hwnd, mem_dc, PW_RENDERFULLCONTENT)
    if not ok:
        user32.PrintWindow(hwnd, mem_dc, 0)      # older fallback

    info = BITMAPINFO()
    info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    info.bmiHeader.biWidth = width
    info.bmiHeader.biHeight = -height            # top-down
    info.bmiHeader.biPlanes = 1
    info.bmiHeader.biBitCount = 32
    info.bmiHeader.biCompression = BI_RGB

    buf_len = width * height * 4
    buffer = ctypes.create_string_buffer(buf_len)
    gdi32.GetDIBits(mem_dc, bmp, 0, height, buffer, ctypes.byref(info), DIB_RGB_COLORS)

    img = Image.frombuffer("RGB", (width, height), buffer, "raw", "BGRX", 0, 1)

    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mem_dc)
    user32.ReleaseDC(hwnd, hdc)

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return str(out)
