# Nimad Copilot — Cloudflare Pages One-Click Deployment Script
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path "$ScriptDir\.."

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "     NIMAD COPILOT — CLOUDFLARE PAGES DEPLOYER            " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan

Set-Location $ProjectRoot

Write-Host "`nDeploying frontend directory to Cloudflare Pages..." -ForegroundColor Yellow
Write-Host "Project Name: nimad-copilot" -ForegroundColor DarkGray
Write-Host "Directory: ./frontend" -ForegroundColor DarkGray

# Runs wrangler pages deploy in non-interactive mode
npx -y wrangler pages deploy ./frontend --project-name=nimad-copilot

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host " Deployment Complete! Check your .pages.dev link above." -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
