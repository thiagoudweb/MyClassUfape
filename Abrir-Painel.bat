@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Abrindo o painel do SAC... (feche esta janela para encerrar)
where py >nul 2>nul
if %errorlevel%==0 (
  py scripts\sac.py painel
) else (
  python scripts\sac.py painel
)
echo.
echo Se apareceu erro de Python: instale em python.org marcando Add python.exe to PATH.
pause
