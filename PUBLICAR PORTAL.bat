@echo off
chcp 65001 >nul
cd /d "%~dp0"
python publicar_portal.py
echo.
pause
