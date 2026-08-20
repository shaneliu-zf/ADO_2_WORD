---
name: export-drawio-png
description: >-
  Exports docs/pipeline.drawio page 1 to docs/pipeline-overview.png via draw.io Desktop CLI.
  Use when the user asks to export PNG, update the pipeline diagram, regenerate pipeline-overview.png,
  or convert draw.io to PNG.
---

# 匯出 pipeline PNG

不要在 repo 裡新增或保留匯出腳本。需要時直接跑 CLI。README 用 PNG（Cursor 預覽對 draw.io 的 SVG `foreignObject` 顯示不佳）。

## 步驟

1. 確認來源：`docs/pipeline.drawio`
2. 確認 draw.io Desktop 可執行：

```bash
DRAWIO="${DRAWIO:-/Applications/draw.io.app/Contents/MacOS/draw.io}"
test -x "$DRAWIO"
```

找不到就停：請安裝 [draw.io Desktop](https://github.com/jgraph/drawio-desktop)，或設 `DRAWIO` 指向可執行檔。

3. 匯出第 1 頁為 2x PNG：

```bash
DRAWIO="${DRAWIO:-/Applications/draw.io.app/Contents/MacOS/draw.io}"
"$DRAWIO" -x -f png -s 2 -o docs/pipeline-overview.png -p 1 docs/pipeline.drawio
```

4. 確認寫入 `docs/pipeline-overview.png`。README 用相對路徑 `![Pipeline 總覽](docs/pipeline-overview.png)`（不要寫成 `/docs/...`）。
