@echo off
chcp 65001 >nul
title Travel Blue – Contas a Receber

set "HTML=%~dp0contas-receber.html"

if not exist "%HTML%" (
    echo.
    echo  ERRO: Dashboard nao encontrado!
    echo  Execute primeiro: ATUALIZAR CONTAS A RECEBER.bat
    echo.
    pause
    exit /b
)

echo.
echo  Abrindo Dashboard de Contas a Receber...
echo.
start "" "%HTML%"
