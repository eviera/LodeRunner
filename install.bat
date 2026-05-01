@echo off
echo === Lode Runner - Instalacion de dependencias (Windows) ===
echo.

python -m venv venv
if errorlevel 1 (
    echo ERROR: No se encontro Python. Instala Python 3 desde python.org
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

pip install pygame
pip install -e "%USERPROFILE%\workspace\evgamelib"

echo.
echo Generando assets...
python make_assets.py

echo.
echo === Instalacion completa! Usa lode.bat para jugar ===
pause
