"""버클 브랜드 .ico 생성 — exe 아이콘(PyInstaller --icon)용. 실행: python packaging/gen_icon.py

드로잉 단일 소스(harness_app.qt_shell.widgets.brand_pixmap)를 크기별로 렌더해
멀티 해상도 ICO(16~256)로 묶는다(Pillow). 산출: packaging/buckle.ico (커밋 대상 —
빌드 머신에 Pillow 없어도 빌드 가능하도록 생성물을 리포에 둔다).
"""

import io
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # 리포 루트(편집설치 불요)

from PIL import Image
from PySide6.QtCore import QBuffer
from PySide6.QtWidgets import QApplication

from harness_app.qt_shell.widgets import brand_pixmap

SIZES = [16, 24, 32, 48, 64, 128, 256]
OUT = Path(__file__).resolve().parent / "buckle.ico"


def _to_pil(size: int) -> Image.Image:
    pm = brand_pixmap(size)
    buf = QBuffer()
    buf.open(QBuffer.OpenModeFlag.WriteOnly)
    pm.save(buf, "PNG")
    return Image.open(io.BytesIO(bytes(buf.data()))).convert("RGBA")


def main() -> None:
    _app = QApplication.instance() or QApplication([])
    imgs = [_to_pil(s) for s in SIZES]
    # 각 크기를 Qt 로 직접 렌더(선명) — Pillow 축소 대신 append_images 로 원본 삽입.
    imgs[-1].save(
        OUT,
        format="ICO",
        append_images=imgs[:-1],
        sizes=[(s, s) for s in SIZES],
    )
    print("생성:", OUT, OUT.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
