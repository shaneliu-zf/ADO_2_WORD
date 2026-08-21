@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
title ADO_2_WORD

rem 雙擊即可啟動。檢查／安裝 Python、Node 與套件，然後一次開前後端。
set "ROOT=%CD%"
set "PY="
set "NODE_MIN_MAJOR=18"

call :run
if errorlevel 1 (
  echo.
  echo 啟動失敗。按任意鍵關閉視窗。
  pause >nul
)
exit /b

:run
if not exist "%ROOT%\backend\app.py" (
  echo 錯誤：請把腳本放在專案根目錄再執行
  exit /b 1
)

call :refresh_path
echo === 檢查環境 ===
call :ensure_python
if errorlevel 1 exit /b 1
call :ensure_python_packages
if errorlevel 1 exit /b 1
call :ensure_node
if errorlevel 1 exit /b 1
call :ensure_frontend
if errorlevel 1 exit /b 1

echo === 啟動前後端 ===
echo 5173 就緒後會自動打開：http://127.0.0.1:5173/
echo 按 Ctrl+C 會同時停止 Flask 與 Vite
echo.

cd /d "%ROOT%"
set PYTHONUNBUFFERED=1
start "ADO_2_WORD_BACKEND" /D "%ROOT%" /B "!PY!" -m backend.app
start "ADO_2_WORD_FRONTEND" /D "%ROOT%\frontend" /B cmd /c npm run dev
call :wait_for_port 5173
if errorlevel 1 (
  echo 警告：等待 http://127.0.0.1:5173/ 啟動逾時，請手動打開瀏覽器。
) else (
  start "" "http://127.0.0.1:5173/"
)
cd /d "%ROOT%"
call :wait_forever
call :kill_port 5000
call :kill_port 5173
exit /b 0

:die
echo 錯誤：%~1
exit /b 1

:refresh_path
set "MACHINE_PATH="
set "USER_PATH="
for /f "skip=2 tokens=2*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "MACHINE_PATH=%%B"
for /f "skip=2 tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USER_PATH=%%B"
set "PATH=%USERPROFILE%\.local\bin;%USER_PATH%;%MACHINE_PATH%;%PATH%"
if exist "%LOCALAPPDATA%\Programs\Python" (
  for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
    set "PATH=%%D;%%D\Scripts;!PATH!"
  )
)
if exist "%ProgramFiles%\nodejs" set "PATH=%ProgramFiles%\nodejs;!PATH!"
if exist "%LOCALAPPDATA%\Programs\Python\Launcher" set "PATH=%LOCALAPPDATA%\Programs\Python\Launcher;!PATH!"
exit /b 0

:python_ok
if not exist "%~1" exit /b 1
set "CAND=%~1"
if /i not "!CAND:WindowsApps=!"=="!CAND!" exit /b 1
"%CAND%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)" 2>nul
if errorlevel 1 exit /b 1
exit /b 0

:find_python
set "PY="
for %%N in (python3 python) do (
  for /f "delims=" %%I in ('where %%N 2^>nul') do (
    call :python_ok "%%I"
    if not errorlevel 1 (
      set "PY=%%I"
      exit /b 0
    )
  )
)
where py >nul 2>&1
if not errorlevel 1 (
  for /f "delims=" %%I in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do (
    call :python_ok "%%I"
    if not errorlevel 1 (
      set "PY=%%I"
      exit /b 0
    )
  )
)
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
  if exist "%%D\python.exe" (
    call :python_ok "%%D\python.exe"
    if not errorlevel 1 (
      set "PY=%%D\python.exe"
      exit /b 0
    )
  )
)
exit /b 0

:ensure_python
call :find_python
if not defined PY (
  echo 找不到 Python 3.9+，開始安裝…
  call :ensure_winget
  if errorlevel 1 exit /b 1
  winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
  call :refresh_path
  call :find_python
)
if not defined PY (
  call :die "無法使用 Python 3.9+"
  exit /b 1
)
call :python_ok "!PY!"
if errorlevel 1 (
  call :die "無法使用 Python 3.9+"
  exit /b 1
)
for /f "delims=" %%V in ('"!PY!" -c "import sys; print(sys.version.split()[0])"') do set "PY_VER=%%V"
echo Python：!PY_VER!（!PY!）
exit /b 0

:ensure_python_packages
echo 檢查 Python 套件…
"!PY!" -c "import flask, docx, lxml, markdown" 2>nul
if not errorlevel 1 (
  echo Python 套件：已就緒
  exit /b 0
)
echo 安裝 Python 套件（requirements.txt）…
"!PY!" -m pip install -r "%ROOT%\requirements.txt"
if errorlevel 1 (
  call :die "Python 套件安裝失敗"
  exit /b 1
)
"!PY!" -c "import flask, docx, lxml, markdown"
if errorlevel 1 (
  call :die "Python 套件安裝失敗"
  exit /b 1
)
exit /b 0

:node_ok
where node >nul 2>&1
if errorlevel 1 exit /b 1
node -e "process.exit(Number(process.versions.node.split('.')[0]) >= 18 ? 0 : 1)" 2>nul
if errorlevel 1 exit /b 1
exit /b 0

:ensure_winget
where winget >nul 2>&1
if not errorlevel 1 exit /b 0
if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\winget.exe" exit /b 0
echo 錯誤：找不到 winget，請先安裝 Python 3.9+ 與 Node.js 18+
echo   Python：https://www.python.org/downloads/
echo   Node.js：https://nodejs.org/
exit /b 1

:ensure_node
call :refresh_path
call :node_ok
if not errorlevel 1 (
  for /f "delims=" %%V in ('node -v') do echo Node：%%V
  exit /b 0
)
echo 找不到 Node.js %NODE_MIN_MAJOR%+，開始安裝…
call :ensure_winget
if errorlevel 1 exit /b 1
winget install -e --id OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
call :refresh_path
call :node_ok
if errorlevel 1 (
  call :die "Node.js 安裝失敗，請關閉此視窗後再雙擊一次"
  exit /b 1
)
for /f "delims=" %%V in ('node -v') do echo Node：%%V
exit /b 0

:ensure_frontend
where npm >nul 2>&1
if errorlevel 1 (
  call :die "找不到 npm"
  exit /b 1
)
if exist "%ROOT%\frontend\node_modules\vite" (
  echo 前端套件：已就緒
  exit /b 0
)
echo 安裝前端套件（npm install）…
pushd "%ROOT%\frontend"
call npm install
set "NPM_EC=!errorlevel!"
popd
if not exist "%ROOT%\frontend\node_modules\vite" (
  call :die "npm install 失敗"
  exit /b 1
)
if not "!NPM_EC!"=="0" (
  call :die "npm install 失敗"
  exit /b 1
)
exit /b 0

:wait_for_port
set "PORT=%~1"
set /a RETRIES=120
:wait_for_port_loop
for /f "tokens=5" %%P in ('netstat -ano 2^>nul ^| findstr ":%PORT%" ^| findstr "LISTENING"') do (
  if not "%%P"=="0" exit /b 0
)
set /a RETRIES-=1
if %RETRIES% LEQ 0 exit /b 1
timeout /t 1 /nobreak >nul
goto wait_for_port_loop

:wait_forever
:wait_forever_loop
timeout /t 86400 /nobreak >nul
goto wait_forever_loop

:kill_port
for /f "tokens=5" %%P in ('netstat -ano 2^>nul ^| findstr ":%~1" ^| findstr "LISTENING"') do (
  if not "%%P"=="0" taskkill /F /PID %%P /T >nul 2>&1
)
exit /b 0
