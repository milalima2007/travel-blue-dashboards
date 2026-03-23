@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title Travel Blue – Atualizar Backpack ^& Luggage Dashboard

echo.
echo  ====================================================
echo   Travel Blue – Backpack ^& Luggage Dashboard
echo   Atualizacao de Dados
echo  ====================================================
echo.
echo  O que este bat faz:
echo    1. Le o arquivo Excel (aba DATABASE)
echo    2. Atualiza os dados no Supabase
echo    3. Reconstroi o viewer.html
echo    4. Publica no GitHub Pages (URL compartilhada)
echo    5. Abre o dashboard para conferencia
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

:: ── Se arquivo foi arrastado sobre o bat ────────────────────────────────────
if not "%~1"=="" (
    set "EXCEL=%~1"
    goto :atualizar
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

:: fallback: arquivo padrao na pasta backpack-lugagge
if "!EXCEL!"=="" (
    set "EXCEL=%~dp0backpack-lugagge\SALES ALL TB GROUP - BACKPACKS&LUGGAGE - TB BRAND.xlsx"
)

:atualizar
echo  Arquivo: !EXCEL!
echo.

python "%~dp0upload_backpack_data.py" "!EXCEL!"

if errorlevel 1 (
    echo.
    echo  ====================================================
    echo   ERRO ao atualizar o dashboard.
    echo   Verifique se o Excel tem a aba DATABASE.
    echo  ====================================================
    echo.
    pause
    exit /b
)

echo.
echo  Pressione qualquer tecla para fechar...
pause >nul
endlocal
