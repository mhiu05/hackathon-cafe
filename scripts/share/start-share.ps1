<#
.SYNOPSIS
  Share the local Biblio demo with judges through ONE ngrok tunnel.

.DESCRIPTION
  Builds the frontend, starts the backend (127.0.0.1:8000) and `vite preview` (127.0.0.1:4173, proxies /api to the
  backend), waits until both answer, then runs `ngrok http 4173` in this window. Press Ctrl+C to stop ngrok;
  the backend and preview windows are closed automatically.

  One-time setup (do it yourself, never paste the token into chat or commit it):
    winget install ngrok.ngrok
    ngrok config add-authtoken <YOUR_TOKEN>      # token from https://dashboard.ngrok.com/get-started/your-authtoken

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts/share/start-share.ps1
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts/share/start-share.ps1 -Domain my-demo.ngrok-free.app -ResetDemo
#>
param(
    [string]$Domain = "",          # optional free static domain from https://dashboard.ngrok.com/domains
    [switch]$SkipBuild,            # reuse the existing frontend/dist
    [switch]$ResetDemo,            # back up and clear demo orders/chats before sharing
    [int]$BackendPort = 8000,
    [int]$PreviewPort = 4173
)
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Root

function Fail($message) { Write-Host "ERROR: $message" -ForegroundColor Red; exit 1 }
function Test-Port($port) { [bool](Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue) }
function Wait-Http($url, $seconds) {
    $deadline = (Get-Date).AddSeconds($seconds)
    while ((Get-Date) -lt $deadline) {
        try { if ((Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 $url).StatusCode -eq 200) { return $true } } catch {}
        Start-Sleep -Milliseconds 700
    }
    return $false
}

# 1. Prerequisites ----------------------------------------------------------------------------------------------
foreach ($tool in "ngrok", "uv", "pnpm") {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        if ($tool -eq "ngrok") { Fail "ngrok not found. Install: winget install ngrok.ngrok ; then: ngrok config add-authtoken <YOUR_TOKEN>" }
        Fail "$tool not found on PATH."
    }
}
# winget ships an old ngrok (3.3.x): it lacks --url and the ngrok service rejects outdated agents (ERR_NGROK_121).
$ngrokVersion = [regex]::Match((& ngrok version 2>&1 | Out-String), "(\d+)\.(\d+)\.(\d+)")
if (-not $ngrokVersion.Success) { Fail "Could not read 'ngrok version'." }
if ([version]$ngrokVersion.Value -lt [version]"3.20.0") { Fail "ngrok $($ngrokVersion.Value) is too old. Run: ngrok update   (then open a new terminal)" }
$envFile = Join-Path $Root ".env"
if (-not (Test-Path $envFile)) { Fail ".env missing. Copy .env.example to .env and fill OPENAI_API_KEY and ADMIN_PIN." }
$envText = Get-Content $envFile -Raw
foreach ($key in "OPENAI_API_KEY", "ADMIN_PIN") {
    $m = [regex]::Match($envText, "(?m)^\s*$key\s*=\s*(\S+)")
    if (-not $m.Success) { Fail "$key is empty in .env (needed by the judges' demo)." }
    if ($key -eq "ADMIN_PIN" -and $m.Groups[1].Value.Length -lt 6) { Fail "ADMIN_PIN must be at least 6 characters." }
}
if (-not (Test-Path (Join-Path $Root "data\cafe.db"))) { Fail "data\cafe.db missing. Run: uv run python scripts/knowledge/ingest.py --offline" }
foreach ($port in $BackendPort, $PreviewPort) {
    if (Test-Port $port) { Fail "Port $port is already in use. Stop the old server there (Ctrl+C in its window) and run this script again." }
}

# 2. Data and build ---------------------------------------------------------------------------------------------
if ($ResetDemo) {
    Write-Host "Resetting demo data (a backup is written to data\backups)..."
    uv run python scripts/demo/reset_demo.py
    if ($LASTEXITCODE -ne 0) { Fail "reset_demo failed." }
}
if (-not $SkipBuild) {
    Write-Host "Building frontend..."
    pnpm --dir frontend build
    if ($LASTEXITCODE -ne 0) { Fail "Frontend build failed." }
}

# 3. Start backend + preview --------------------------------------------------------------------------------------
# --proxy-headers trusts X-Forwarded-For from 127.0.0.1 (the Vite proxy), so rate limits see each judge's real IP.
$backendCmd = "Set-Location '$Root'; uv run uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port $BackendPort --proxy-headers --forwarded-allow-ips 127.0.0.1"
$previewCmd = "Set-Location '$Root\frontend'; `$env:BACKEND_URL='http://127.0.0.1:$BackendPort'; pnpm exec vite preview --host 127.0.0.1 --port $PreviewPort --strictPort"
$backend = Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd -PassThru
$preview = Start-Process powershell -ArgumentList "-NoExit", "-Command", $previewCmd -PassThru

try {
    Write-Host "Waiting for backend and preview..."
    if (-not (Wait-Http "http://127.0.0.1:$BackendPort/api/cafe" 60)) { Fail "Backend did not start; check its window." }
    if (-not (Wait-Http "http://127.0.0.1:$PreviewPort/api/cafe" 60)) { Fail "Preview/proxy did not start; check its window." }
    Write-Host ""
    Write-Host "Local check OK: http://127.0.0.1:$PreviewPort  (admin: /admin.html)" -ForegroundColor Green
    Write-Host "Share the 'Forwarding' https URL that ngrok prints below:" -ForegroundColor Green
    Write-Host "  Customer : <forwarding-url>/"
    Write-Host "  Staff    : <forwarding-url>/admin.html   (PIN = ADMIN_PIN in .env; send it to judges separately)"
    Write-Host "Free plan: judges see an ngrok warning page once, then click 'Visit Site'."
    Write-Host ""

    # 4. Tunnel (blocks until Ctrl+C) -----------------------------------------------------------------------------
    # Explicit IPv4: preview listens on 127.0.0.1 only, and "localhost" may resolve to ::1 first.
    $ngrokArgs = @("http", "127.0.0.1:$PreviewPort")
    if ($Domain) { $ngrokArgs += "--url=$Domain" }
    & ngrok @ngrokArgs
}
finally {
    foreach ($p in $preview, $backend) {
        if ($p -and -not $p.HasExited) {
            # Kill the whole tree (powershell -> uv/pnpm -> python/node) so ports 8000/4173 are released.
            & taskkill /PID $p.Id /T /F | Out-Null
        }
    }
    Write-Host "Stopped backend and preview."
}
