# -*- coding: utf-8 -*-
"""练习会话：出题队列、判分、统计。不依赖 Qt，便于单独测试。"""
from __future__ import annotations

import random
from dataclasses import dataclass

from . import priority
from .models import Bank, Question
from .store import ProgressStore

MODES = ("random", "filter", "wrong")
MODE_LABELS = {"random": "随机练习", "filter": "筛选练习", "wrong": "只做错题"}


@dataclass(frozen=True)
class Stats:
    attempted: int
    correct: int
    wrong: int
    total: int

    @property
    def accuracy(self) -> float:
        return self.correct / self.attempted if self.attempted else 0.0

    @property
    def coverage(self) -> float:
        return self.attempted / self.total if self.total else 0.0


class QuizSession:
    def __init__(self, bank: Bank, store: ProgressStore, rng: random.Random | None = None):
        self.bank = bank
        self.store = store
        self.rng = rng or random.Random()
        self.mode = "random"
        self.filters: dict[str, str | None] = {"chapter": None, "knowledge": None, "type": None}
        self.queue: list[str] = []
        self.index = 0
        self.round_done: set[str] = set()   # 本轮已作答的题（切换轮次时清空）
        self.rebuild()

    # ---------------------------------------------------------------- 队列
    def candidates(self) -> list[Question]:
        qs = list(self.bank.questions)
        if self.mode == "wrong":
            wrong = set(self.wrong_ids())
            return [q for q in qs if q.id in wrong]

        # 题型范围在随机、筛选两种模式下都生效；章节/知识点只在筛选模式生效
        tp = self.filters.get("type")
        if tp:
            qs = [q for q in qs if q.type == tp]

        if self.mode == "filter":
            ch = self.filters.get("chapter")
            kp = self.filters.get("knowledge")
            if ch:
                qs = [q for q in qs if q.chapter_id == ch]
            if kp:
                qs = [q for q in qs if q.knowledge == kp]
            qs.sort(key=lambda q: q.order)
        return qs

    def rebuild(self, keep_current: bool = True, new_round: bool = False) -> None:
        current = self.current.id if self.queue else None
        qs = self.candidates()
        if self.mode in ("random", "wrong"):
            qs = priority.order(qs, self.store.records, self.bank, self.rng)
        if new_round:
            self.round_done.clear()
        self.queue = [q.id for q in qs]
        if keep_current and current in self.queue:
            self.index = self.queue.index(current)
        else:
            self.index = 0

    # ---------------------------------------------------------------- 掌握度
    def weak_count(self) -> int:
        """做过但掌握度低于目标值的题数（用于统计面板）。"""
        return priority.weak_count(list(self.bank.questions), self.store.records)

    def reshuffle(self) -> None:
        """打乱本轮顺序（R 键）：保留本轮已答状态，只改先后。"""
        self.rng.shuffle(self.queue)
        self.index = 0

    # ---------------------------------------------------------------- 导航
    @property
    def total(self) -> int:
        return len(self.queue)

    @property
    def at_end(self) -> bool:
        return self.index >= len(self.queue)

    @property
    def current(self) -> Question | None:
        if 0 <= self.index < len(self.queue):
            return self.bank.by_id[self.queue[self.index]]
        return None

    def go_next(self) -> bool:
        if self.index < len(self.queue):
            self.index += 1
            return self.index < len(self.queue)
        return False

    def go_prev(self) -> bool:
        if self.index > 0:
            self.index -= 1
            return True
        return False

    def jump_to(self, question_id: str) -> bool:
        if question_id in self.queue:
            self.index = self.queue.index(question_id)
            return True
        return False

    # ---------------------------------------------------------------- 判分
    def submit(self, chosen: list[str]) -> bool:
        q = self.current
        if q is None:
            return False
        ok = q.is_correct(chosen)
        self.store.record(q.id, sorted(chosen), ok)
        self.round_done.add(q.id)
        return ok

    def state_of(self, question_id: str) -> dict | None:
        return self.store.get(question_id)

    # ---------------------------------------------------------------- 统计
    def stats(self) -> Stats:
        attempted = len(self.store.records)
        correct = sum(1 for r in self.store.records.values() if r.get("correct"))
        return Stats(attempted=attempted, correct=correct,
                     wrong=attempted - correct, total=len(self.bank.questions))

    def wrong_ids(self) -> list[str]:
        """错题按「错得最多 → 最快到期 → 最早作答」排序，优先攻克顽固题。"""
        ids = [qid for qid, r in self.store.records.items() if not r.get("correct")]
        order = {q.id: q.order for q in self.bank.questions}

        def key(qid: str):
            rec = self.store.records.get(qid, {})
            return (-int(rec.get("wrong", 0)), -int(rec.get("attempts", 0)), order[qid])

        return sorted((i for i in ids if i in order), key=key)

    # ---------------------------------------------------------------- 筛选
    def set_mode(self, mode: str) -> None:
        if mode not in MODES or mode == self.mode:
            return
        self.mode = mode
        self.rebuild(keep_current=True if mode != "random" else False)

    def set_filters(self, chapter: str | None, knowledge: str | None, type_: str | None) -> None:
        self.filters = {"chapter": chapter, "knowledge": knowledge, "type": type_}
        self.rebuild(keep_current=True)

    def knowledge_options(self) -> list[str]:
        ch = self.filters.get("chapter")
        if ch:
            return list(self.bank.knowledge_of(ch))
        seen: list[str] = []
        for c in self.bank.chapters:
            for kp in c.knowledge:
                if kp not in seen:
                    seen.append(kp)
        return seen
