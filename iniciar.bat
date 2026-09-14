@echo off
title Laboratorio Clinico - Servidor
color 1F
cls

echo.
echo  ============================================
echo   LABORATORIO CLINICO - Sistema de Gestion
echo  ============================================
echo.
echo  Iniciando servidor...
echo.

cd /d "%~dp0"

REM Verificar que el ambiente virtual existe
if not exist ".venv\Scripts\python.exe" (
    echo  [ERROR] No se encontro el ambiente virtual.
    echo  Ejecute: python -m venv .venv
    pause
    exit /b 1
)

REM Verificar que el archivo .env existe
if not exist ".env" (
    echo  [ERROR] No se encontro el archivo .env
    pause
    exit /b 1
)

REM Activar ambiente virtual y arrancar
echo  Ambiente virtual: OK
echo  Base de datos:    laboratorio_cli @ 127.0.0.1:5432
echo  URL:              http://127.0.0.1:5000
echo.
echo  Abriendo navegador en 3 segundos...
echo  (Presione Ctrl+C para detener el servidor)
echo  ============================================
echo.

REM Abrir el navegador despues de 3 segundos en segundo plano
start /min cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:5000"

REM Iniciar Flask
.venv\Scripts\python run.py

echo.
echo  Servidor detenido.
pause
