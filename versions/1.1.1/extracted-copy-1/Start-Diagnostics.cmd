@echo off
title NewsTicker Diagnostics
cd /d "%~dp0"
runtime\python.exe app\server.py --diagnostics
echo.
echo NewsTicker has stopped. Review any error above and data\app.log.
pause
