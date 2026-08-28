#!/usr/bin/env python3
"""展示用佔位 PNG（純色色塊，不含客戶畫面）。"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

from backend.utils.paths import DEMO_FILES_DIR

# 檔名 → (寬, 高, RGB)
DEMO_IMAGE_SPECS: dict[str, tuple[int, int, tuple[int, int, int]]] = {
    "print_error.png": (640, 280, (198, 40, 40)),
    "label_preview.png": (640, 280, (245, 166, 35)),
    "inventory_count.png": (640, 280, (25, 118, 210)),
    "excel_columns.png": (640, 280, (56, 142, 60)),
    "scan_fail.png": (480, 320, (123, 31, 162)),
    "permission_dialog.png": (520, 260, (2, 119, 189)),
}


def write_png(path: Path, width: int, height: int, rgb: tuple[int, int, int]) -> None:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    row = b"\x00" + bytes(rgb) * width
    raw = row * height
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def write_demo_images() -> None:
    DEMO_FILES_DIR.mkdir(parents=True, exist_ok=True)
    for name, (width, height, rgb) in DEMO_IMAGE_SPECS.items():
        write_png(DEMO_FILES_DIR / name, width, height, rgb)
