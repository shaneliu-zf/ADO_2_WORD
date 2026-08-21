#!/usr/bin/env bash
# 在 Finder 雙擊即可啟動（會開 Terminal）。檢查／安裝後一次開前後端；Ctrl+C 一起停。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

PY=""
PY_MIN="3.9"
NODE_MIN_MAJOR=18

say() { printf '%s\n' "$*"; }
die() { printf '錯誤：%s\n' "$*" >&2; exit 1; }

brew_shellenv() {
  if [[ -x /opt/homebrew/bin/brew ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [[ -x /usr/local/bin/brew ]]; then
    eval "$(/usr/local/bin/brew shellenv)"
  fi
}

ensure_brew() {
  brew_shellenv
  if command -v brew >/dev/null 2>&1; then
    say "Homebrew：已安裝（$(brew --prefix)）"
    return 0
  fi
  say "找不到 Homebrew，開始安裝…"
  NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  brew_shellenv
  export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
  command -v brew >/dev/null 2>&1 || die "Homebrew 安裝失敗。若跳出權限視窗請允許後再執行一次。"
  say "Homebrew：安裝完成（$(brew --prefix)）"
}

python_ok() {
  local bin="${1:-}"
  [[ -x "$bin" ]] || return 1
  "$bin" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)" 2>/dev/null
}

node_ok() {
  command -v node >/dev/null 2>&1 || return 1
  node -e "process.exit(Number(process.versions.node.split('.')[0]) >= $NODE_MIN_MAJOR ? 0 : 1)" 2>/dev/null
}

ensure_python() {
  if python_ok "$(command -v python3.12 || true)"; then
    PY="$(command -v python3.12)"
  elif python_ok "$(command -v python3 || true)"; then
    PY="$(command -v python3)"
  elif python_ok "$(command -v python || true)"; then
    PY="$(command -v python)"
  fi

  if [[ -z "$PY" ]]; then
    say "找不到 Python ${PY_MIN}+，用 Homebrew 安裝…"
    brew install python@3.12
    PY="$(brew --prefix python@3.12)/bin/python3.12"
    python_ok "$PY" || PY="$(command -v python3 || true)"
  fi

  python_ok "$PY" || die "無法使用 Python ${PY_MIN}+"
  py_ver="$("$PY" -c 'import sys; print(sys.version.split()[0])')"
  say "Python：${py_ver} (${PY})"
}

ensure_python_packages() {
  say "檢查 Python 套件…"
  if "$PY" -c "import flask, docx, lxml, markdown" 2>/dev/null; then
    say "Python 套件：已就緒"
    return 0
  fi
  say "安裝 Python 套件（requirements.txt）…"
  if ! "$PY" -m pip install -r "$ROOT/requirements.txt"; then
    say "改用 --break-system-packages 安裝…"
    "$PY" -m pip install --break-system-packages -r "$ROOT/requirements.txt"
  fi
  "$PY" -c "import flask, docx, lxml, markdown" \
    || die "Python 套件安裝失敗"
}

ensure_node() {
  if node_ok; then
    say "Node：$(node -v)"
    return 0
  fi
  say "找不到 Node.js ${NODE_MIN_MAJOR}+，用 Homebrew 安裝…"
  brew install node
  node_ok || die "Node.js 安裝失敗"
  say "Node：$(node -v)"
}

ensure_frontend() {
  command -v npm >/dev/null 2>&1 || die "找不到 npm"
  if [[ -d "$ROOT/frontend/node_modules/vite" ]]; then
    say "前端套件：已就緒"
    return 0
  fi
  say "安裝前端套件（npm install）…"
  (cd "$ROOT/frontend" && npm install)
  [[ -d "$ROOT/frontend/node_modules/vite" ]] || die "npm install 失敗"
}

if [[ ! -f "$ROOT/backend/app.py" ]]; then
  die "請把腳本放在專案根目錄再執行"
fi

say "=== 檢查環境 ==="
ensure_brew
ensure_python
ensure_python_packages
ensure_node
ensure_frontend
say "=== 啟動前後端 ==="
say "5173 就緒後會自動打開：http://127.0.0.1:5173/"
say "按 Ctrl+C 會同時停止 Flask 與 Vite"
say ""

wait_for_port() {
  local port="$1"
  local retries=120
  while (( retries > 0 )); do
    if python3 - <<PY >/dev/null 2>&1
import socket
sock = socket.socket()
sock.settimeout(0.2)
try:
    sock.connect(("127.0.0.1", ${port}))
except OSError:
    raise SystemExit(1)
finally:
    sock.close()
raise SystemExit(0)
PY
    then
      return 0
    fi
    sleep 0.5
    ((retries--))
  done
  return 1
}

PIDS=()
cleanup_and_maybe_pause() {
  local ec=$?
  trap - EXIT INT TERM
  for pid in "${PIDS[@]+"${PIDS[@]}"}"; do
    kill "$pid" 2>/dev/null || true
    pkill -P "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
  if [[ $ec -ne 0 && $ec -ne 130 && $ec -ne 143 ]]; then
    echo
    echo "啟動失敗（結束碼 ${ec}）。按 Enter 關閉視窗。"
    read -r || true
  fi
}
trap cleanup_and_maybe_pause EXIT INT TERM

"$PY" -m backend.app &
PIDS+=("$!")
cd "$ROOT/frontend"
npm run dev &
PIDS+=("$!")
if wait_for_port 5173; then
  open "http://127.0.0.1:5173/"
else
  say "警告：等待 http://127.0.0.1:5173/ 啟動逾時，請手動打開瀏覽器。"
fi
wait
