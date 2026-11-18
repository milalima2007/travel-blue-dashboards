@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo [%date% %time%] inicio>> publicar.log
python publicar_portal.py>> publicar.log 2>&1
echo [%date% %time%] fim (codigo %errorlevel%)>> publicar.log
exit /b %errorlevel%
