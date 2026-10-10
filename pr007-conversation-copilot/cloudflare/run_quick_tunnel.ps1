# Nimad Copilot — Cloudflare Quick Tunnel Launcher
# Generates a free public HTTPS & WSS URL via Cloudflare in seconds with zero configuration!

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path "$ScriptDir\.."
$BinDir = "$ScriptDir\bin"
$CloudflaredExe = "$BinDir\cloudflared.exe"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   NIMAD COPILOT — CLOUDFLARE PUBLIC TUNNEL LAUNCHER      " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Verify backend server is alive on port 8000
Write-Host "`n[1/3] Checking if Nimad backend is running on port 8000..." -ForegroundColor Yellow
try {
    $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8000/healthz" -UseBasicParsing -TimeoutSec 3
    Write-Host " -> Backend is ONLINE and responding! (Status 200 OK)" -ForegroundColor Green
} catch {
    Write-Host " -> WARNING: Backend not detected on http://127.0.0.1:8000/healthz" -ForegroundColor Yellow
    Write-Host "    Make sure your FastAPI server is started: python -m uvicorn app.main:app --host 127.0.0.1 --port 8000" -ForegroundColor DarkGray
}

# 2. Check for cloudflared executable
Write-Host "`n[2/3] Checking Cloudflare Tunnel executable (cloudflared)..." -ForegroundColor Yellow
if (-not (Test-Path $CloudflaredExe)) {
    # Check system PATH
    $SystemCloudflared = Get-Command "cloudflared" -ErrorAction SilentlyContinue
    if ($SystemCloudflared) {
        $CloudflaredExe = $SystemCloudflared.Source
        Write-Host " -> Found system cloudflared: $CloudflaredExe" -ForegroundColor Green
    } else {
        Write-Host " -> Downloading official cloudflared binary from Cloudflare GitHub..." -ForegroundColor Cyan
        if (-not (Test-Path $BinDir)) { New-Item -ItemType Directory -Path $BinDir | Out-Null }
        $DownloadUrl = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        Invoke-WebRequest -Uri $DownloadUrl -OutFile $CloudflaredExe -UseBasicParsing
        Write-Host " -> Download complete: $CloudflaredExe" -ForegroundColor Green
    }
} else {
    Write-Host " -> Using existing cloudflared binary at: $CloudflaredExe" -ForegroundColor Green
}

# 3. Launch the Quick Tunnel
Write-Host "`n[3/3] Starting Cloudflare Quick Tunnel forwarding to http://127.0.0.1:8000..." -ForegroundColor Yellow
Write-Host "----------------------------------------------------------" -ForegroundColor DarkGray
Write-Host "Look for the public link ending with .trycloudflare.com below!" -ForegroundColor Green
Write-Host "Both HTTPS and WSS (WebSockets) are enabled automatically." -ForegroundColor Green
Write-Host "Press Ctrl+C anytime to stop the tunnel." -ForegroundColor DarkGray
Write-Host "----------------------------------------------------------`n" -ForegroundColor DarkGray

& "$CloudflaredExe" tunnel --url http://127.0.0.1:8000
