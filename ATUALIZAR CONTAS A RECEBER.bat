@echo off
chcp 65001 >nul
title Travel Blue – Atualizar Contas a Receber

echo.
echo  ================================================
echo   Travel Blue – Atualizar Contas a Receber
echo  ================================================
echo.

:: Verifica Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERRO: Python nao encontrado!
    echo  Instale em: https://www.python.org/downloads/
    echo.
    pause
    exit /b
)

:: Se arquivo Excel foi arrastado para cima do bat, usa ele diretamente
if not "%~1"=="" (
    set "EXCEL=%~1"
    goto :gerar
)

:: Senao, busca o arquivo Excel mais recente na pasta Downloads
echo  Procurando arquivo Excel na pasta Downloads...
set "EXCEL="
for /f "delims=" %%f in ('powershell -NoProfile -Command "Get-ChildItem $env:USERPROFILE\Downloads\*.xlsx | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName"') do (
    set "EXCEL=%%f"
)

if "%EXCEL%"=="" (
    echo.
    echo  Nenhum arquivo .xlsx encontrado em Downloads.
    echo.
    echo  OPCOES:
    echo    1. Arraste o arquivo Excel para cima deste .bat
    echo    2. Cole o arquivo Excel na pasta Downloads
    echo.
    set /p "EXCEL=Ou cole aqui o caminho completo do arquivo: "
    if "%EXCEL%"=="" goto :erro
)

echo.
echo  Arquivo encontrado:
echo  %EXCEL%
echo.

:gerar
echo  Gerando dashboard...
echo.

python "%~dp0generate_contas_receber.py" "%EXCEL%"

if errorlevel 1 (
    echo.
    echo  ERRO ao gerar o dashboard. Verifique o arquivo Excel.
    echo.
    pause
    exit /b
)

echo.
echo  Abrindo dashboard atualizado...
echo.
start "" "%~dp0contas-receber.html"
goto :fim

:erro
echo  Operacao cancelada.
pause
exit /b

:fim
timeout /t 3 /nobreak >nul
