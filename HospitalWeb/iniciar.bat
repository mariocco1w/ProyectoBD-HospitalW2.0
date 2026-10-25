@echo off
REM ============================================================
REM  Hospital W 2.0 - Panel de Administracion
REM  Inicia el servidor de pruebas y abre el navegador.
REM ============================================================
cd /d "%~dp0"

echo Instalando dependencias (solo la primera vez)...
python -m pip install --quiet -r requirements.txt

echo.
echo Abriendo http://127.0.0.1:5000 ...
start "" http://127.0.0.1:5000

python app.py
pause
