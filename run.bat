@echo off
title SiteGen AI Server
echo Starting SiteGen AI server...
cd /d "%~dp0"
echo Opening website in your browser...
start /b cmd /c "timeout /t 2 >nul && start http://127.0.0.1:8000/"
.\venv\Scripts\python.exe main.py
pause
