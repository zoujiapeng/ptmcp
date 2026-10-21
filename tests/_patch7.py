import pathlib
p = pathlib.Path("tests/headless.py"); s = p.read_text(encoding="utf-8")

s = s.replace('''def launch_and_wait(timeout: float = 150.0) -> float:
    t0 = time.time()
    subprocess.Popen([PT_EXE])
    while time.time() - t0 < timeout:
        if bridge.alive():
            return time.time() - t0
        time.sleep(2)
    raise TimeoutError("PT started but the script engine never polled the bridge")''',
'''def pids() -> set[int]:
    out = subprocess.run(["tasklist", "/fi", "IMAGENAME eq PacketTracer.exe", "/fo", "csv", "/nh"],
                         capture_output=True, text=True, timeout=20).stdout
    return {int(l.split('","')[1]) for l in out.splitlines() if l.lower().startswith('"packettracer.exe')}


def launch_and_wait(timeout: float = 150.0) -> float:
    """Start PT and wait until the *new* process is polling the bridge."""
    before = pids()
    t0 = time.time()
    subprocess.Popen([PT_EXE])
    alive_file = bridge.bridge_dir() / "alive.txt"
    while time.time() - t0 < timeout:
        now = pids()
        fresh = alive_file.exists() and alive_file.stat().st_mtime >= t0
        if now - before and fresh and bridge.alive():
            return time.time() - t0
        time.sleep(2)
    raise TimeoutError("PT started but the script engine never polled the bridge")''')

s = s.replace('''    print("[6/6] saving .pkt + screenshot (PrintWindow, no input)...")''',
'''    print("[5b/6] letting STP settle before the screenshot...")
    time.sleep(float(spec.get("settle", 35)))

    print("[6/6] saving .pkt + screenshot (PrintWindow, no input)...")''')
p.write_text(s, encoding="utf-8")
print("patched headless test")
