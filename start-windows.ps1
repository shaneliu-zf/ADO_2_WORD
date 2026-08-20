# 檢查／安裝 Python、Node 與套件，然後一次啟動前後端。Ctrl+C 會一起停。
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$Python = $null
$NodeMinMajor = 18

function Say([string]$Message) { Write-Host $Message }
function Die([string]$Message) { Write-Host "錯誤：$Message" -ForegroundColor Red; exit 1 }

function Refresh-Path {
    $machine = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $user = [System.Environment]::GetEnvironmentVariable("Path", "User")
    $local = Join-Path $env:USERPROFILE ".local\bin"
    $env:Path = "$local;$user;$machine"
    $pyRoot = Join-Path $env:LOCALAPPDATA "Programs\Python"
    if (Test-Path $pyRoot) {
        Get-ChildItem $pyRoot -Directory | ForEach-Object {
            $env:Path = "$($_.FullName);$(Join-Path $_.FullName 'Scripts');$env:Path"
        }
    }
    $node = "C:\Program Files\nodejs"
    if (Test-Path $node) { $env:Path = "$node;$env:Path" }
}

function Test-PythonOk([string]$Bin) {
    if (-not (Test-Path $Bin)) { return $false }
    & $Bin -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)" 2>$null
    return ($LASTEXITCODE -eq 0)
}

function Test-NodeOk {
    $node = Get-Command node -ErrorAction SilentlyContinue
    if (-not $node) { return $false }
    node -e "process.exit(Number(process.versions.node.split('.')[0]) >= $NodeMinMajor ? 0 : 1)" 2>$null
    return ($LASTEXITCODE -eq 0)
}

function Ensure-Winget {
    if (Get-Command winget -ErrorAction SilentlyContinue) { return $true }
    return $false
}

function Find-Python {
    foreach ($name in @("python3", "python")) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd -and (Test-PythonOk $cmd.Source)) { return $cmd.Source }
    }
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        $out = & py -3 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $out -and (Test-PythonOk $out.Trim())) {
            return $out.Trim()
        }
    }
    return $null
}

function Ensure-Python {
    $script:Python = Find-Python
    if (-not $script:Python) {
        Say "找不到 Python 3.9+，開始安裝…"
        if (-not (Ensure-Winget)) {
            Die "找不到 winget，請先安裝 Python 3.9+：https://www.python.org/downloads/"
        }
        winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
        Refresh-Path
        $script:Python = Find-Python
    }
    if (-not $script:Python -or -not (Test-PythonOk $script:Python)) {
        Die "無法使用 Python 3.9+"
    }
    $ver = & $script:Python -c "import sys; print(sys.version.split()[0])"
    Say "Python：$ver（$script:Python）"
}

function Ensure-PythonPackages {
    Say "檢查 Python 套件…"
    & $script:Python -c "import flask, docx, lxml, markdown" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Say "Python 套件：已就緒"
        return
    }
    Say "安裝 Python 套件（requirements.txt）…"
    & $script:Python -m pip install -r (Join-Path $Root "requirements.txt")
    if ($LASTEXITCODE -ne 0) { Die "Python 套件安裝失敗" }
    & $script:Python -c "import flask, docx, lxml, markdown"
    if ($LASTEXITCODE -ne 0) { Die "Python 套件安裝失敗" }
}

function Ensure-Node {
    Refresh-Path
    if (Test-NodeOk) {
        Say "Node：$(node -v)"
        return
    }
    Say "找不到 Node.js $NodeMinMajor+，開始安裝…"
    if (-not (Ensure-Winget)) {
        Die "找不到 winget，請先安裝 Node.js 18+：https://nodejs.org/"
    }
    winget install -e --id OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
    Refresh-Path
    if (-not (Test-NodeOk)) {
        Die "Node.js 安裝失敗，請重開終端機後再執行一次"
    }
    Say "Node：$(node -v)"
}

function Ensure-Frontend {
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { Die "找不到 npm" }
    $vite = Join-Path $Root "frontend\node_modules\vite"
    if (Test-Path $vite) {
        Say "前端套件：已就緒"
        return
    }
    Say "安裝前端套件（npm install）…"
    Push-Location (Join-Path $Root "frontend")
    try { npm install } finally { Pop-Location }
    if (-not (Test-Path $vite)) { Die "npm install 失敗" }
}

if (-not (Test-Path (Join-Path $Root "backend\app.py"))) {
    Die "請把腳本放在專案根目錄再執行"
}

Refresh-Path
Say "=== 檢查環境 ==="
Ensure-Python
Ensure-PythonPackages
Ensure-Node
Ensure-Frontend
Say "=== 啟動前後端 ==="
Say "瀏覽器請開：http://127.0.0.1:5173/"
Say "按 Ctrl+C 會同時停止 Flask 與 Vite"
Say ""

$backend = Start-Process -FilePath $script:Python -ArgumentList "-m","backend.app" -WorkingDirectory $Root -PassThru -NoNewWindow
try {
    Set-Location (Join-Path $Root "frontend")
    npm run dev
} finally {
    if ($backend -and -not $backend.HasExited) {
        Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
        Get-CimInstance Win32_Process -Filter "ParentProcessId=$($backend.Id)" -ErrorAction SilentlyContinue |
            ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    }
    Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}
