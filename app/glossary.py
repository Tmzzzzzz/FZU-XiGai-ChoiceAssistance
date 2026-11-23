# -*- coding: utf-8 -*-
"""专有名词匹配：从题干、选项、解析中找出需要解释的术语。"""
from __future__ import annotations

from .models import Question


def match_terms(question: Question, glossary: dict[str, str], limit: int = 3) -> list[tuple[str, str]]:
    """返回命中的 (术语, 解释)，长词优先，已被长词包含的短词不再重复展示。"""
    if not glossary:
        return []
    text = " ".join(
        [question.stem, *[o.text for o in question.options], question.explanation]
    )
    hits = [(term, explain) for term, explain in glossary.items() if term in text]
    hits.sort(key=lambda item: -len(item[0]))

    chosen: list[tuple[str, str]] = []
    for term, explain in hits:
        if any(term in picked for picked, _ in chosen):
            continue
        chosen.append((term, explain))
        if len(chosen) >= limit:
            break
    return chosen
