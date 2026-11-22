# -*- coding: utf-8 -*-
"""生成应用图标 assets/app.ico（与界面左上角标识一致）。"""
import sys
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import (QColor, QFont, QGuiApplication, QImage, QLinearGradient,
                           QPainter, QPainterPath)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "app.ico"


def render(size: int) -> QImage:
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    r = QRectF(1, 1, size - 2, size - 2)
    grad = QLinearGradient(r.topLeft(), r.bottomRight())
    grad.setColorAt(0, QColor("#4A6BF0"))
    grad.setColorAt(1, QColor("#7A5BE0"))
    path = QPainterPath()
    path.addRoundedRect(r, size * 0.24, size * 0.24)
    p.fillPath(path, grad)
    p.setPen(QColor("#FFFFFF"))
    f = QFont("Microsoft YaHei UI")
    f.setPixelSize(int(size * 0.52))
    f.setWeight(QFont.Weight.Bold)
    p.setFont(f)
    p.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, "习")
    p.end()
    return img


def main() -> None:
    # QFont / QPainter 需要 GUI 应用实例，否则在无窗口环境下会直接崩溃
    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sizes = [256, 128, 64, 48, 32, 24, 16]
    frames = []
    for s in sizes:
        tmp = ROOT / "assets" / f"_tmp_{s}.png"
        render(s).save(str(tmp))
        frames.append(Image.open(tmp).convert("RGBA"))
    frames[0].save(OUT, format="ICO", sizes=[(s, s) for s in sizes])
    for s in sizes:
        (ROOT / "assets" / f"_tmp_{s}.png").unlink()
    print("icon written:", OUT, OUT.stat().st_size, "bytes")
    del app


if __name__ == "__main__":
    main()
