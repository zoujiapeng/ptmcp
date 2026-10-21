# install.ps1 - put ptmcp on a fresh Windows machine with Packet Tracer.
#
#   powershell -ExecutionPolicy Bypass -File install.ps1
#
# What it does (everything that *can* be automated):
#   1. finds Packet Tracer and reports its version
#   2. installs the Python package (pip install -e .)
#   3. copies the PT-side script module into <PT>\extensions\MCPBuilder\
#   4. launches PT and waits for the script engine (no clicks)
#   5. smoke test: build a 3-device lab, check links, save a .pkt
#
# What it cannot do, and will tell you:
#   * PT 8 asks for a NetAcad login the first time; a human must click
#     "Continue as a Guest" once (after that it is remembered).
#   * writing into Program Files needs an elevated shell; without it the
#     copy step reports and stops.
#   * only PT 8.x is verified; PT 9 has a different script API surface.

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

function Say($msg) { Write-Host $msg }
function Fail($msg) { Write-Host "FAIL: $msg" -ForegroundColor Red; exit 1 }

Say "== 1/5 Packet Tracer =="
$ptRoots = Get-ChildItem 'C:\Program Files' -Directory -Filter 'Cisco Packet Tracer*' -ErrorAction SilentlyContinue
if (-not $ptRoots) { Fail "Packet Tracer not found under C:\Program Files" }
$pt = $ptRoots | Sort-Object Name -Descending | Select-Object -First 1
$exe = Join-Path $pt.FullName 'bin\PacketTracer.exe'
if (-not (Test-Path $exe)) { Fail "PacketTracer.exe missing in $($pt.FullName)" }
$ver = (Get-Item $exe).VersionInfo.FileVersion
Say "   found $($pt.FullName)  version $ver"
if ($ver -notlike '8.*') { Say "   WARNING: only PT 8.x is verified" }

Say "== 2/5 Python package =="
try { $py = (Get-Command python -ErrorAction Stop).Source } catch { Fail "python not found on PATH (3.10+ required)" }
Say "   python: $py"
& $py -m pip install --quiet --upgrade pip 2>$null | Out-Null
& $py -m pip install --quiet -e . 2>&1 | Select-Object -Last 3
if ($LASTEXITCODE -ne 0) { Fail "pip install -e . failed" }
Say "   package installed"

Say "== 3/5 PT script module =="
$asset = Join-Path $root 'assets\V5.2.pts'
$dest  = Join-Path $pt.FullName 'extensions\MCPBuilder'
if (-not (Test-Path $asset)) { Fail "assets\V5.2.pts missing from the repo" }
try {
    New-Item -ItemType Directory -Force $dest | Out-Null
    Copy-Item $asset (Join-Path $dest 'V5.2.pts') -Force
    Say "   copied to $dest"
} catch {
    Say "   FAIL: cannot write into Program Files. Re-run this script in an ADMIN shell." -ForegroundColor Yellow
    Say "   ($($_.Exception.Message))"
    exit 1
}

Say "== 4/5 start Packet Tracer =="
& $py -m ptmcp start
if ($LASTEXITCODE -ne 0) {
    Say "   the script engine did not come up." -ForegroundColor Yellow
    Say "   Most likely: first-run login dialog. Click 'Continue as a Guest' once, then re-run."
    exit 1
}

Say "== 5/5 smoke test =="
& $py tests\e2e.py specs\case27.json
if ($LASTEXITCODE -ne 0) { Fail "smoke test failed (see output above)" }

Say ""
Say "OK. Try:  python -m ptmcp build specs\campus.json"
Say "MCP:      python -m ptmcp serve   (register as a stdio MCP server)"
