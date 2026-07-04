$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw "Docker Desktop is required." }
docker compose --env-file .env.local up --build -d
docker compose ps
Write-Host "Runtime UI: http://localhost:8080"
