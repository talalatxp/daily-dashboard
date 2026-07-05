@echo off
:: =====================================================================
:: AGENTE DE IA - SCRIPT DE ACTUALIZACION AUTOMATICA (WINDOWS)
:: Coloca este archivo junto a "generar_dashboard.py" y "tareas.json"
:: =====================================================================
title Agente Daily AI Dashboard - Actualizador

:: Navegar de forma segura a la carpeta donde reside este archivo .bat
cd /d "%~dp0"

:: === CONFIGURACIÓN DE TU UBICACIÓN (VARIABLES DE ENTORNO) ===
:: Cambia estos valores para personalizar tu ciudad y coordenadas.
:: ¡El script de Python los leerá automáticamente!
set "DASHBOARD_CIUDAD=Madrid, España"
set "DASHBOARD_LATITUD=40.4168"
set "DASHBOARD_LONGITUD=-3.7038"

echo =====================================================================
echo  INICIANDO ACTUALIZACION DEL DAILY AI DASHBOARD
echo =====================================================================
echo.

:: 1. Intentar con 'python' primero
set PYTHON_CMD=python
python --version >nul 2>nul
if %errorlevel% equ 0 goto check_script

:: 2. Si falla, intentar con 'py' (lanzador estándar de Windows)
set PYTHON_CMD=py
py --version >nul 2>nul
if %errorlevel% equ 0 goto check_script

:: Si ambos fallan, mostrar error
echo [ERROR] No se pudo encontrar Python en tu sistema.
echo.
echo Esto suele ocurrir por una de estas razones:
echo 1. Al mover los archivos de carpeta, has abierto el script desde un programa
echo    que no tiene cargadas tus variables de entorno globales de Windows.
echo    Solucion: Ve a la carpeta con el Explorador de Archivos de Windows
echo    y haz DOBLE CLIC directamente sobre actualizar.bat.
echo.
echo 2. Python no esta instalado globalmente o falta marcar Add Python to PATH en la instalacion.
echo    Solucion: Descarga Python 3 de python.org y vuelvelo a instalar.
echo.
pause
exit /b

:check_script
:: 3. Verificar si existe el archivo del agente de Python
if exist "generar_dashboard.py" goto run_agent
echo [ERROR] No se encuentra generar_dashboard.py en esta carpeta.
echo.
echo Asegurate de tener actualizar.bat, generar_dashboard.py y tareas.json en la misma carpeta.
echo.
pause
exit /b

:run_agent
echo [1/3] Ejecutando el Agente de Python...
%PYTHON_CMD% generar_dashboard.py

if %errorlevel% neq 0 goto agent_error

echo.
echo [2/3] index.html generado con exito!
echo.

:: --- CONTROL DE PUERTO OCUPADO (LOCALHOST) ---
echo [3/3] Iniciando el servidor local...
netstat -ano | findstr :8000 > nul
if %errorlevel% equ 0 goto port_busy

echo [INFO] El puerto 8000 esta libre. Levantando nuevo servidor local...
start "Servidor Daily AI Dashboard" cmd /c "%PYTHON_CMD% -m http.server 8000"
timeout /t 2 > nul
echo Abriendo http://localhost:8000 en tu navegador...
start http://localhost:8000
goto end_process

:port_busy
echo [INFO] El puerto 8000 ya esta en uso. El servidor local ya esta corriendo.
echo Abriendo http://localhost:8000 en tu navegador...
start http://localhost:8000

:end_process
echo.
echo =====================================================================
echo  PROCESO COMPLETADO CON EXITO
echo =====================================================================
timeout /t 5
exit /b

:agent_error
echo.
echo [ERROR] Hubo un fallo al ejecutar el script de Python.
echo Revisa los mensajes de error de arriba para saber la causa exacta.
echo.
pause
exit /b
