@echo off
rem 雙擊即可啟動。實際檢查／安裝在 start-windows.ps1。
cd /d "%~dp0"
title ADO_2_WORD
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-windows.ps1"
if errorlevel 1 (
  echo.
  echo 啟動失敗。按任意鍵關閉視窗。
  pause >nul
)
