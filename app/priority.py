# -*- coding: utf-8 -*-
"""出题优先级：不依赖时间，只回答“下一题该先出哪一道”。

评分由五项加权构成（满分 1.0）：

    优先级 = 0.40·未掌握度 + 0.25·错误压力 + 0.15·难度适配 + 0.12·覆盖缺口 + 0.08·考点频次

再叠加“连续同类惩罚”，保证同一知识点、同一章不会连着出。
详见 docs/ranking.md。
"""
from __future__ import annotations

import random

from .models import Bank, Question

W_NEED = 0.40          # 未掌握度
W_WRONG = 0.25         # 错误压力（错误频率 + 最近一次是否答错）
W_FIT = 0.15           # 难度适配（提分性价比）
W_COVER = 0.12         # 知识点覆盖缺口
W_FREQ = 0.08          # 考点频次（以题库内该知识点题量作代理）

JITTER = 0.05          # 同分抖动，避免每次顺序完全一致
PENALTY_SAME_KNOWLEDGE = 0.22   # 与上一题同知识点
PENALTY_RECENT_KNOWLEDGE = 0.10  # 近三题内出现过同一知识点
PENALTY_SAME_CHAPTER = 0.08     # 与上一题同章节

MASTERY_GOAL = 0.55    # 掌握度低于此值视为“待巩固”
NEW_QUESTION_NEED = 0.75  # 新题价值：未知但值得查漏，略低于确定不会的题


# ------------------------------------------------------------------ 单项指标
def static_difficulty(question: Question) -> float:
    """题目难度先验：题型、选项数、题干长度、正确项个数。区间 0.2–0.9。"""
    value = 0.46 if question.is_multiple else 0.30
    if len(question.options) >= 5:
        value += 0.05
    value += min(len(question.stem) / 120, 1.0) * 0.04
    if question.is_multiple:
        value += 0.05 * max(0, len(question.answer) - 2)
    return max(0.2, min(0.9, value))


def difficulty_label(value: float) -> str:
    if value < 0.40:
        return "低"
    if value < 0.62:
        return "中"
    return "高"


def mastery(record: dict | None) -> float | None:
    """掌握度 0–1；没有作答记录时返回 None（未知，不是 0）。"""
    if not record or not int(record.get("attempts", 0)):
        return None
    attempts = max(int(record.get("attempts", 1)), 1)
    right = int(record.get("right", 0))
    recent = str(record.get("recent") or ("1" if record.get("correct") else "0"))
    acc_recent = recent.count("1") / max(len(recent), 1)
    acc_all = right / attempts
    streak = int(record.get("streak", 0))
    # 样本少时向 0.5 收缩：答对一次不等于掌握（1 次 60% / 2 次 70% / 4 次 90%）
    confidence = min(attempts / 4.0, 1.0)
    raw = 0.55 * acc_recent + 0.30 * acc_all + 0.10 * min(streak / 2.0, 1.0)
    return 0.5 * (1 - confidence) + raw * confidence


def wrong_pressure(record: dict | None) -> float:
    """错误压力 0–1：累计错误次数（边际递减）+ 错误率 + 最近一次是否错。"""
    if not record or not int(record.get("attempts", 0)):
        return 0.0
    attempts = max(int(record.get("attempts", 1)), 1)
    wrong = int(record.get("wrong", 0))
    rate = wrong / attempts
    value = 0.6 * min(wrong / 3.0, 1.0) + 0.4 * rate
    if record.get("correct") is False:
        value = min(1.0, value + 0.15)
    return value


def difficulty_fit(question: Question, record: dict | None) -> float:
    """难度适配：中等难度最容易在短期提分，过易无收益、过难性价比低。

    新题不参与性价比判断，给中间值，避免一上来全是难题或全是简单题。
    """
    if record is None:
        return 0.5
    difficulty = static_difficulty(question)
    return max(0.0, 1.0 - abs(difficulty - 0.60) / 0.60)


# ------------------------------------------------------------------ 综合评分
def base_score(question: Question, record: dict | None, kp_total: int,
               kp_count: int, kp_practiced: bool) -> float:
    m = mastery(record)
    need = NEW_QUESTION_NEED if m is None else 1.0 - m
    wrong = wrong_pressure(record)
    fit = difficulty_fit(question, record)
    if not kp_practiced:
        cover = 1.0          # 整个知识点一道没做过：优先查漏
    elif m is None:
        cover = 0.6          # 该知识点练过，但这道题没做过
    else:
        cover = 0.0
    freq = kp_count / max(kp_total, 1)
    return (W_NEED * need + W_WRONG * wrong + W_FIT * fit
            + W_COVER * cover + W_FREQ * freq)


def order(questions: list[Question], records: dict[str, dict], bank: Bank,
          rng: random.Random | None = None) -> list[Question]:
    """贪心排序：每轮取当前得分最高者，并对同类知识点做连续惩罚。

    纯函数，不读时间、不写状态，便于单元测试与复现。
    """
    rng = rng or random.Random()
    if len(questions) <= 1:
        return list(questions)

    kp_count: dict[str, int] = {}
    for q in bank.questions:
        kp_count[q.knowledge] = kp_count.get(q.knowledge, 0) + 1
    kp_total = max(kp_count.values(), default=1)

    practiced_kp = {bank.by_id[qid].knowledge for qid in records if qid in bank.by_id}
    scores = {q.id: base_score(q, records.get(q.id), kp_total,
                               kp_count.get(q.knowledge, 1), q.knowledge in practiced_kp)
              for q in questions}

    remaining = list(questions)
    picked: list[Question] = []
    recent_kp: list[str] = []
    while remaining:
        best: Question | None = None
        best_value = float("-inf")
        for q in remaining:
            value = scores[q.id] + rng.uniform(0.0, JITTER)
            if recent_kp and q.knowledge == recent_kp[-1]:
                value -= PENALTY_SAME_KNOWLEDGE
            elif q.knowledge in recent_kp[-3:]:
                value -= PENALTY_RECENT_KNOWLEDGE
            if picked and q.chapter_id == picked[-1].chapter_id:
                value -= PENALTY_SAME_CHAPTER
            if value > best_value:
                best_value, best = value, q
        picked.append(best)
        remaining.remove(best)
        recent_kp.append(best.knowledge)
    return picked


def weak_count(questions: list[Question], records: dict[str, dict]) -> int:
    """需要继续巩固的题：做过且掌握度低于目标值。"""
    count = 0
    for q in questions:
        m = mastery(records.get(q.id))
        if m is not None and m < MASTERY_GOAL:
            count += 1
    return count


def explain(question: Question, record: dict | None) -> str:
    """给界面用的一句话评估。"""
    m = mastery(record)
    if m is None:
        return "首次作答 · 难度" + difficulty_label(static_difficulty(question))
    wrong = int(record.get("wrong", 0))
    parts = [f"掌握度 {round(m * 100)}%"]
    if wrong:
        parts.append(f"累计错 {wrong} 次")
    parts.append("难度" + difficulty_label(static_difficulty(question)))
    return " · ".join(parts)
