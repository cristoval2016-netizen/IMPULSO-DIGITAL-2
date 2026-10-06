# Script para iniciar Impulso Digital en PowerShell
$rootDir = $PSScriptRoot

# Añadir Node.js al PATH temporal de la sesión
$env:Path = "C:\Program Files\nodejs;" + $env:Path

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  Iniciando Impulso Digital (Backend + Frontend)       " -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan

Write-Host "[1/2] Iniciando Backend FastAPI en http://127.0.0.1:8000 ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$rootDir\backend'; .\ .venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"

Write-Host "[2/2] Iniciando Frontend Vite en http://localhost:5173 ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$env:Path = 'C:\Program Files\nodejs;' + `$env:Path; Set-Location '$rootDir\frontend'; & 'C:\Program Files\nodejs\npm.cmd' run dev"

Write-Host ""
Write-Host "Servicios iniciados en ventanas separadas." -ForegroundColor Green
Write-Host " - Diagnóstico público: http://localhost:5173/" -ForegroundColor White
Write-Host " - CRM interno:         http://localhost:5173/crm" -ForegroundColor White
Write-Host " - Swagger API docs:    http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "========================================================" -ForegroundColor Cyan
