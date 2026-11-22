# -*- coding: utf-8 -*-
"""程序入口。

pythonw 启动时没有控制台，因此这里做统一兜底：任何启动异常都会写入
`logs/error.log` 并弹出提示框，避免“双击没反应”的情况无法排查。
"""
from __future__ import annotations

import shutil
import sys
import traceback
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QStandardPaths, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QMessageBox

from .main_window import MainWindow
from .models import load_bank
from .store import ProgressStore
from .ui import theme

APP_NAME = "XigaiReview"


def _app_root() -> Path:
    """源码运行时是项目根目录；打包成 exe 后是 exe 所在目录。

    这样 data/、userdata/、logs/ 始终跟着程序走，整个文件夹可任意移动。
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


ROOT = _app_root()
BANK_PATH = ROOT / "data" / "questions.json"
LOG_PATH = ROOT / "logs" / "error.log"
DATA_DIR = ROOT / "userdata"


def _legacy_state_path() -> Path:
    """旧版本把记录放在用户目录，这里仅用于一次性迁移。"""
    base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    if not base:
        base = str(Path.home() / ".xigai_review")
    return Path(base) / "progress.json"


def _state_path() -> Path:
    """记录保存在程序目录的 userdata/ 下，整个文件夹拷走即可换机。

    只有在程序目录不可写（例如放在 Program Files）时才退回用户目录。
    """
    target = DATA_DIR / "progress.json"
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        probe = DATA_DIR / ".write-check"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return target
    except OSError:
        fallback = _legacy_state_path()
        fallback.parent.mkdir(parents=True, exist_ok=True)
        _write_crash(f"程序目录不可写，记录改存到：{fallback}")
        return fallback


def _migrate_legacy(target: Path) -> None:
    """把旧版用户目录里的记录搬到程序目录（仅首次，不覆盖已有文件）。"""
    if target.exists():
        return
    legacy = _legacy_state_path()
    if legacy.exists():
        try:
            shutil.copy2(legacy, target)
        except OSError:
            pass


def _write_crash(text: str) -> Path:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}]\n{text}\n")
    except OSError:
        pass
    return LOG_PATH


def _resolve_theme(store: ProgressStore) -> str:
    """优先用上次选择，其次跟随系统深浅色。"""
    saved = store.get_pref("theme")
    if saved in ("light", "dark"):
        return saved
    try:
        scheme = QGuiApplication.styleHints().colorScheme()
        if scheme == Qt.ColorScheme.Dark:
            return "dark"
    except Exception:  # noqa: BLE001
        pass
    return "light"


def _run() -> int:
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName("习概选择题")
    app.setOrganizationName("Xigai")
    app.setStyle("Fusion")
    app.setFont(theme.base_font(10))

    state_path = _state_path()
    _migrate_legacy(state_path)
    store = ProgressStore(state_path)
    theme.set_mode(_resolve_theme(store))
    app.setPalette(theme.app_palette())
    app.setStyleSheet(theme.qss())

    try:
        bank = load_bank(BANK_PATH)
    except Exception as exc:  # noqa: BLE001
        box = QMessageBox()
        box.setIcon(QMessageBox.Critical)
        box.setWindowTitle("题库加载失败")
        box.setText("无法读取题库数据。")
        box.setInformativeText(f"{exc}\n\n路径：{BANK_PATH}")
        box.exec()
        return 1

    win = MainWindow(bank, store)
    win.show()
    return app.exec()


def main() -> int:
    try:
        return _run()
    except Exception:  # noqa: BLE001
        detail = traceback.format_exc()
        path = _write_crash(detail)
        try:
            QMessageBox.critical(
                None, "启动失败",
                "程序启动时发生错误，详细信息已写入：\n"
                f"{path}\n\n{detail[-900:]}")
        except Exception:  # noqa: BLE001
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
