# -*- coding: utf-8 -*-
"""答题进度的本地持久化（原子写入，避免中断损坏）。"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


class ProgressStore:
    """保存每题最近一次作答结果与界面偏好。"""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.records: dict[str, dict[str, Any]] = {}
        self.prefs: dict[str, Any] = {}
        self._load()

    # ---------------------------------------------------------------- 读写
    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return  # 损坏则忽略，从空白进度开始
        if isinstance(data.get("records"), dict):
            self.records = data["records"]
        if isinstance(data.get("prefs"), dict):
            self.prefs = data["prefs"]

    def save(self) -> bool:
        """写盘成功返回 True；磁盘只读等情况下静默失败，不影响答题。"""
        payload = {"version": 1, "records": self.records, "prefs": self.prefs}
        tmp = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=1)
            os.replace(tmp, self.path)
            return True
        except OSError:
            return False
        finally:
            if tmp and os.path.exists(tmp):
                try:
                    os.unlink(tmp)
                except OSError:
                    pass

    # ---------------------------------------------------------------- 记录
    def record(self, question_id: str, chosen: list[str], correct: bool) -> None:
        old = self.records.get(question_id, {})
        self.records[question_id] = {
            "attempts": int(old.get("attempts", 0)) + 1,
            "correct": bool(correct),
            "chosen": list(chosen),
            "at": datetime.now().isoformat(timespec="seconds"),
        }

    def get(self, question_id: str) -> dict[str, Any] | None:
        return self.records.get(question_id)

    def reset(self) -> None:
        self.records.clear()
        self.save()

    # ---------------------------------------------------------------- 偏好
    def set_pref(self, key: str, value: Any) -> None:
        self.prefs[key] = value

    def get_pref(self, key: str, default: Any = None) -> Any:
        return self.prefs.get(key, default)
