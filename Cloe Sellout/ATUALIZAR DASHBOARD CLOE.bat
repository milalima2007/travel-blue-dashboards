@echo off
cd /d "%~dp0"
python gerar_dashboard.py
python gerar_cronograma.py
python gerar_cronograma_promocional.py
python gerar_cronograma_peanuts.py
pause
