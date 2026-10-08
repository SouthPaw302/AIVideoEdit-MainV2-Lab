@echo off
setlocal
cd /d %~dp0
where python >nul 2>nul
if errorlevel 1 (
  where py >nul 2>nul
  if errorlevel 1 (
    echo Python was not found. Install Python 3 and try again.
    pause
    exit /b 1
  )
  set PY=py -3
) else (
  set PY=python
)
where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo FFmpeg was not found in PATH.
  echo Install FFmpeg, reopen this window, and try again.
  pause
  exit /b 1
)
echo Starting AIVideoEdit Alpha Stack...
%PY% stack.py
pause
