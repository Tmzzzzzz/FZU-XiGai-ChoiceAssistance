# -*- coding: utf-8 -*-
"""答题进度的本地持久化（原子写入，避免中断损坏）。"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


RECENT_WINDOW = 5   # 记录最近若干次作答，用于计算“最近正确率”


class ProgressStore:
    """保存每题作答结果、复习计划与界面偏好。"""

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
            self.records = {k: _upgrade(v) for k, v in data["records"].items()
                            if isinstance(v, dict)}
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
    def record(self, question_id: str, chosen: list[str], correct: bool) -> dict[str, Any]:
        """记录一次作答：累计对错、连续答对与最近若干次结果（用于排序，不涉及时间）。"""
        old = _upgrade(self.records.get(question_id, {}))
        recent = str(old.get("recent") or "") + ("1" if correct else "0")
        rec = {
            "attempts": int(old.get("attempts", 0)) + 1,
            "correct": bool(correct),
            "chosen": list(chosen),
            "at": datetime.now().isoformat(timespec="seconds"),
            "wrong": int(old.get("wrong", 0)) + (0 if correct else 1),
            "right": int(old.get("right", 0)) + (1 if correct else 0),
            "streak": int(old.get("streak", 0)) + 1 if correct else 0,
            "recent": recent[-RECENT_WINDOW:],
        }
        self.records[question_id] = rec
        return rec

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


def _upgrade(rec: dict[str, Any]) -> dict[str, Any]:
    """兼容旧记录：补齐次数与最近结果；旧的 due 字段直接丢弃。"""
    out = dict(rec)
    out.pop("due", None)
    if not out:
        return out
    if "wrong" not in out:
        out["wrong"] = 0 if out.get("correct") else 1
    if "right" not in out:
        out["right"] = 1 if out.get("correct") else 0
    if "streak" not in out:
        out["streak"] = 1 if out.get("correct") else 0
    if "recent" not in out:
        out["recent"] = "1" if out.get("correct") else "0"
    return out
