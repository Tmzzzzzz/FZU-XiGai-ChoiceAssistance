# -*- coding: utf-8 -*-
"""练习会话：出题队列、判分、统计。不依赖 Qt，便于单独测试。"""
from __future__ import annotations

import random
from dataclasses import dataclass

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
        self.rebuild()

    # ---------------------------------------------------------------- 队列
    def candidates(self) -> list[Question]:
        qs = list(self.bank.questions)
        if self.mode == "wrong":
            wrong = set(self.wrong_ids())
            qs = [q for q in qs if q.id in wrong]
        elif self.mode == "filter":
            ch = self.filters.get("chapter")
            kp = self.filters.get("knowledge")
            tp = self.filters.get("type")
            if ch:
                qs = [q for q in qs if q.chapter_id == ch]
            if kp:
                qs = [q for q in qs if q.knowledge == kp]
            if tp:
                qs = [q for q in qs if q.type == tp]
            qs.sort(key=lambda q: q.order)
            return qs
        return qs

    def rebuild(self, keep_current: bool = True) -> None:
        current = self.current.id if self.queue else None
        qs = self.candidates()
        if self.mode == "random":
            fresh = [q for q in qs if q.id not in self.store.records]
            done = [q for q in qs if q.id in self.store.records]
            self.rng.shuffle(fresh)
            self.rng.shuffle(done)
            qs = fresh + done
        self.queue = [q.id for q in qs]
        if keep_current and current in self.queue:
            self.index = self.queue.index(current)
        else:
            self.index = 0

    def reshuffle(self) -> None:
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
        ids = [qid for qid, r in self.store.records.items() if not r.get("correct")]
        order = {q.id: q.order for q in self.bank.questions}
        return sorted((i for i in ids if i in order), key=lambda i: order[i])

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
