@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title Travel Blue – Atualizar Backpack ^& Luggage Dashboard

echo.
echo  ====================================================
echo   Travel Blue – Backpack ^& Luggage Dashboard
echo   Gerador de Dashboard Offline
echo  ====================================================
echo.

:: ── Verifica Python ─────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERRO: Python nao encontrado!
    echo  Instale em: https://www.python.org/downloads/
    echo.
    pause
    exit /b
)

:: ── Verifica pandas ─────────────────────────────────────────────────────────
python -c "import pandas" >nul 2>&1
if errorlevel 1 (
    echo  Instalando pandas e openpyxl...
    pip install pandas openpyxl --quiet
)

:: ── Se arquivo foi arrastado sobre o bat ────────────────────────────────────
if not "%~1"=="" (
    set "EXCEL=%~1"
    goto :gerar
)

:: ── Sem arquivo: busca o mais recente em Downloads ──────────────────────────
echo  Buscando arquivo Excel em Downloads...
set "EXCEL="

for /f "delims=" %%f in ('powershell -NoProfile -Command "Get-ChildItem $env:USERPROFILE\Downloads\*.xlsx | Where-Object {$_.Name -like '*BACKPACK*' -or $_.Name -like '*SALES*' -or $_.Name -like '*TB*'} | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName" 2^>nul') do (
    set "EXCEL=%%f"
)

:: fallback: qualquer xlsx recente
if "!EXCEL!"=="" (
    for /f "delims=" %%f in ('powershell -NoProfile -Command "Get-ChildItem $env:USERPROFILE\Downloads\*.xlsx | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName" 2^>nul') do (
        set "EXCEL=%%f"
    )
)

if "!EXCEL!"=="" (
    echo.
    echo  Nenhum arquivo .xlsx encontrado em Downloads.
    echo.
    echo  OPCOES:
    echo    1. Arraste o arquivo Excel (SALES ALL TB GROUP...) sobre este .bat
    echo    2. Coloque o arquivo na pasta Downloads
    echo.
    set /p "EXCEL=Ou cole aqui o caminho do arquivo Excel: "
    if "!EXCEL!"=="" goto :erro
)

:gerar
echo.
echo  Arquivo: !EXCEL!
echo.
echo  Gerando dashboard offline...
echo.
python "%~dp0generate_backpack_dashboard.py" "!EXCEL!"

if errorlevel 1 (
    echo.
    echo  ERRO ao gerar o dashboard.
    echo  Verifique se o arquivo Excel tem a aba DATABASE.
    echo.
    pause
    exit /b
)

echo.
echo  ====================================================
echo   Dashboard atualizado com sucesso!
echo   Arquivo: backpack-lugagge\dashboard-local.html
echo  ====================================================
echo.
timeout /t 3 /nobreak >nul
goto :fim

:erro
echo  Operacao cancelada.
pause
exit /b

:fim
endlocal
