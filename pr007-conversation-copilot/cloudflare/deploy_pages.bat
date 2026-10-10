@echo off
title Nimad Copilot — Deploy to Cloudflare Pages
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy_pages.ps1"
pause
