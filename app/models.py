# -*- coding: utf-8 -*-
"""数据模型与题库加载。"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Option:
    key: str
    text: str


@dataclass(frozen=True)
class Question:
    id: str
    chapter_id: str
    chapter: str
    chapter_no: int
    type: str                 # single / multiple
    type_label: str           # 单选 / 多选
    knowledge: str
    no: int
    seq: int
    stem: str
    options: tuple[Option, ...]
    answer: frozenset[str]
    explanation: str
    note: str = ""
    order: int = 0

    @property
    def is_multiple(self) -> bool:
        return self.type == "multiple"

    @property
    def answer_text(self) -> str:
        return "".join(k for k in (o.key for o in self.options) if k in self.answer)

    def is_correct(self, chosen) -> bool:
        return set(chosen) == set(self.answer)


@dataclass(frozen=True)
class Chapter:
    id: str
    no: int
    name: str
    short: str
    knowledge: tuple[str, ...]


@dataclass(frozen=True)
class Bank:
    title: str
    version: str
    chapters: tuple[Chapter, ...]
    questions: tuple[Question, ...]
    by_id: dict[str, Question]
    glossary: dict[str, str]

    def chapter(self, chapter_id: str) -> Chapter:
        for c in self.chapters:
            if c.id == chapter_id:
                return c
        raise KeyError(chapter_id)

    def knowledge_of(self, chapter_id: str) -> tuple[str, ...]:
        return self.chapter(chapter_id).knowledge


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(f"题库格式错误：{msg}")


def load_bank(path: str | Path) -> Bank:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    _require("questions" in raw and "chapters" in raw, "缺少 questions 或 chapters")

    chapters = tuple(
        Chapter(
            id=c["id"],
            no=int(c["no"]),
            name=c["name"],
            short=c.get("short", c["name"]),
            knowledge=tuple(c.get("knowledge", ())),
        )
        for c in raw["chapters"]
    )
    _require(len({c.id for c in chapters}) == len(chapters), "章节 id 重复")

    questions = []
    for q in raw["questions"]:
        opts = tuple(Option(o["key"], o["text"]) for o in q["options"])
        _require(len(opts) >= 4, f"{q.get('id')} 选项少于 4 个")
        answer = frozenset(q["answer"])
        _require(answer <= {o.key for o in opts}, f"{q.get('id')} 答案不在选项中")
        questions.append(
            Question(
                id=q["id"],
                chapter_id=q["chapter_id"],
                chapter=q["chapter"],
                chapter_no=int(q["chapter_no"]),
                type=q["type"],
                type_label=q.get("type_label", "单选" if q["type"] == "single" else "多选"),
                knowledge=q["knowledge"],
                no=int(q["no"]),
                seq=int(q.get("seq", q["no"])),
                stem=q["stem"],
                options=opts,
                answer=answer,
                explanation=q.get("explanation", ""),
                note=q.get("note", ""),
                order=int(q.get("order", 0)),
            )
        )

    by_id = {q.id: q for q in questions}
    _require(len(by_id) == len(questions), "题目 id 重复")

    meta = raw.get("meta", {})
    glossary = meta.get("glossary") or {}
    _require(isinstance(glossary, dict), "glossary 必须是对象")
    return Bank(
        title=meta.get("title", "选择题题库"),
        version=meta.get("version", "1.0.0"),
        chapters=chapters,
        questions=tuple(questions),
        by_id=by_id,
        glossary={str(k): str(v) for k, v in glossary.items() if str(k).strip()},
    )
