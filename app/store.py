# -*- coding: utf-8 -*-
"""答题进度的本地持久化（原子写入，避免中断损坏）。"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


# 连续答对后的复习间隔（天）与答错后的重练间隔（小时）
REVIEW_INTERVALS = (1, 3, 7, 16, 35)
RELEARN_HOURS = 6


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
        """记录一次作答，并按「连续答对次数」推算下次复习时间。"""
        old = _upgrade(self.records.get(question_id, {}))
        now = datetime.now()
        streak = int(old.get("streak", 0)) + 1 if correct else 0
        if correct:
            days = REVIEW_INTERVALS[min(max(streak, 1) - 1, len(REVIEW_INTERVALS) - 1)]
            due = now + timedelta(days=days)
        else:
            due = now + timedelta(hours=RELEARN_HOURS)
        rec = {
            "attempts": int(old.get("attempts", 0)) + 1,
            "correct": bool(correct),
            "chosen": list(chosen),
            "at": now.isoformat(timespec="seconds"),
            "wrong": int(old.get("wrong", 0)) + (0 if correct else 1),
            "right": int(old.get("right", 0)) + (1 if correct else 0),
            "streak": streak,
            "due": due.isoformat(timespec="seconds"),
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
    """兼容 v1 记录：补齐错误次数、连续答对与到期时间。"""
    out = dict(rec)
    if not out:
        return out
    if "wrong" not in out:
        out["wrong"] = 0 if out.get("correct") else 1
    if "right" not in out:
        out["right"] = 1 if out.get("correct") else 0
    if "streak" not in out:
        out["streak"] = 1 if out.get("correct") else 0
    if "due" not in out:
        try:
            base = datetime.fromisoformat(str(out.get("at")))
        except (TypeError, ValueError):
            base = datetime.now()
        days = REVIEW_INTERVALS[min(max(out["streak"], 1) - 1, len(REVIEW_INTERVALS) - 1)]
        out["due"] = (base + (timedelta(days=days) if out.get("correct")
                               else timedelta(hours=RELEARN_HOURS))).isoformat(timespec="seconds")
    return out
