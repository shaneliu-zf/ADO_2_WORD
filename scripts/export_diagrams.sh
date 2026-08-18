#!/usr/bin/env bash
# 從 docs/pipeline.drawio 匯出 SVG（需已安裝 draw.io Desktop）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DRAWIO="${DRAWIO:-/Applications/draw.io.app/Contents/MacOS/draw.io}"
SRC="$ROOT/docs/pipeline.drawio"

if [[ ! -x "$DRAWIO" ]]; then
  echo "找不到 draw.io：$DRAWIO" >&2
  echo "請安裝 https://github.com/jgraph/drawio-desktop 或設定 DRAWIO=…" >&2
  exit 1
fi

"$DRAWIO" -x -f svg -o "$ROOT/docs/pipeline-overview.svg" -p 1 "$SRC"

echo "已寫入：docs/pipeline-overview.svg"
