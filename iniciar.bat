@echo off
title Lanzador - Impulso Digital
echo ========================================================
echo   Iniciando Impulso Digital (Backend + Frontend)
echo ========================================================

set "PATH=C:\Program Files\nodejs;%PATH%"

echo [1/2] Iniciando Backend FastAPI en http://127.0.0.1:8000 ...
start "Impulso Digital - Backend" cmd /k "cd /d "%~dp0backend" && .venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"

echo [2/2] Iniciando Frontend Vite en http://localhost:5173 ...
start "Impulso Digital - Frontend" cmd /k "set "PATH=C:\Program Files\nodejs;%%PATH%%" && cd /d "%~dp0frontend" && npm.cmd run dev"

echo.
echo Todo listo! Puedes acceder a:
echo  - Aplicacion Web (Diagnostico): http://localhost:5173/
echo  - CRM Interno:                  http://localhost:5173/crm
echo  - Documentacion Swagger:        http://127.0.0.1:8000/docs
echo ========================================================
pause
