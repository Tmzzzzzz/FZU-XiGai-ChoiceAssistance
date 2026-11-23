# -*- coding: utf-8 -*-
"""左侧栏：练习模式与筛选条件。"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton,
                               QScrollArea, QVBoxLayout, QWidget)

from ..session import MODES, QuizSession
from .widgets import BrandMark, Chip, HLine, Segmented, Select


class Sidebar(QWidget):
    modeChanged = Signal(str)
    filtersChanged = Signal()
    restartRequested = Signal()

    def __init__(self, session: QuizSession, parent=None):
        super().__init__(parent)
        self.session = session
        self.setObjectName("sidebar")
        self.setFixedWidth(272)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.addWidget(scroll)

        host = QWidget()
        scroll.setWidget(host)
        lay = QVBoxLayout(host)
        lay.setContentsMargins(20, 22, 20, 18)
        lay.setSpacing(16)

        # ---- 品牌
        brand = QHBoxLayout()
        brand.setSpacing(10)
        brand.addWidget(BrandMark(40), 0, Qt.AlignTop)
        texts = QVBoxLayout()
        texts.setSpacing(1)
        t1 = QLabel("习概题库")
        t1.setObjectName("brandTitle")
        t2 = QLabel(f"{len(session.bank.questions)} 题 · {len(session.bank.chapters)} 章 · "
                    f"{sum(len(c.knowledge) for c in session.bank.chapters)} 知识点")
        t2.setObjectName("brandSub")
        texts.addWidget(t1)
        texts.addWidget(t2)
        brand.addLayout(texts, 1)
        lay.addLayout(brand)

        # ---- 模式
        mode_label = QLabel("练习模式")
        mode_label.setObjectName("sectionLabel")
        lay.addWidget(mode_label)

        self.segmented = Segmented(["随机", "筛选", "错题"])
        self.segmented.changed.connect(self._on_mode)
        lay.addWidget(self.segmented)

        self.mode_hint = QLabel("")
        self.mode_hint.setObjectName("hint")
        self.mode_hint.setWordWrap(True)
        lay.addWidget(self.mode_hint)

        lay.addWidget(HLine())

        # ---- 筛选
        filter_label = QLabel("筛选条件")
        filter_label.setObjectName("sectionLabel")
        lay.addWidget(filter_label)

        self.filter_note = QLabel("章节 / 知识点需切到「筛选」模式")
        self.filter_note.setObjectName("hint")
        self.filter_note.setWordWrap(True)
        lay.addWidget(self.filter_note)

        self.chapter_select = Select("全部章节")
        self.kp_select = Select("全部知识点")
        self.type_select = Select("全部题型")
        for title, widget in (("章节", self.chapter_select),
                              ("知识点", self.kp_select),
                              ("题型", self.type_select)):
            row = QVBoxLayout()
            row.setSpacing(5)
            cap = QLabel(title)
            cap.setObjectName("hint")
            row.addWidget(cap)
            row.addWidget(widget)
            lay.addLayout(row)

        self.queue_chip = Chip("0 题", "primary")
        chip_row = QHBoxLayout()
        chip_row.addWidget(self.queue_chip, 0)
        chip_row.addStretch(1)
        lay.addLayout(chip_row)

        lay.addWidget(HLine())

        # ---- 快捷键
        keys_label = QLabel("快捷键")
        keys_label.setObjectName("sectionLabel")
        lay.addWidget(keys_label)
        tips = QLabel("A–E / 1–5　选择选项\nEnter　　　提交 / 下一题\n← →　　　　上一题 / 下一题\nR　　　　　打乱本轮顺序")
        tips.setObjectName("hint")
        tips.setWordWrap(True)
        lay.addWidget(tips)

        lay.addStretch(1)

        self.restart_btn = QPushButton("↻　重新开始本轮")
        self.restart_btn.setObjectName("link")
        self.restart_btn.setCursor(Qt.PointingHandCursor)
        self.restart_btn.clicked.connect(self.restartRequested.emit)
        lay.addWidget(self.restart_btn, 0, Qt.AlignHCenter)

        self._fill_static_items()
        self.refresh()

    # ---------------------------------------------------------------- 数据
    def _fill_static_items(self) -> None:
        items = [(None, "全部章节")]
        for c in self.session.bank.chapters:
            n = sum(1 for q in self.session.bank.questions if q.chapter_id == c.id)
            name = c.name if c.no == 0 else f"{c.short} {c.name.split(' ', 1)[-1]}"
            items.append((c.id, f"{name}（{n}）"))
        self.chapter_select.set_items(items)
        self.type_select.set_items([(None, "全部题型"), ("single", "单选题"),
                                    ("multiple", "多选题")])
        self._rebuild_kp_items()
        self.chapter_select.changed.connect(self._on_chapter)
        self.kp_select.changed.connect(lambda _=None: self.filtersChanged.emit())
        self.type_select.changed.connect(lambda _=None: self.filtersChanged.emit())

    def _rebuild_kp_items(self, keep: bool = False) -> None:
        chapter = self.chapter_select.value
        current = self.kp_select.value if keep else None
        items = [(None, "全部知识点")]
        pool = [q for q in self.session.bank.questions
                if chapter is None or q.chapter_id == chapter]
        seen: dict[str, int] = {}
        for q in pool:
            seen[q.knowledge] = seen.get(q.knowledge, 0) + 1
        for kp, n in seen.items():
            items.append((kp, f"{kp}（{n}）"))
        self.kp_select.set_items(items, keep=False)
        if current in [v for v, _ in items]:
            self.kp_select.set_value(current)
        else:
            self.kp_select.set_value(None)

    def _on_chapter(self, _value) -> None:
        self._rebuild_kp_items(keep=True)
        self.filtersChanged.emit()

    def _on_mode(self, index: int) -> None:
        self.modeChanged.emit(MODES[index])
        self.refresh()

    # ---------------------------------------------------------------- 刷新
    def refresh(self) -> None:
        mode = self.session.mode
        self.segmented.set_index(MODES.index(mode))
        for sel in (self.chapter_select, self.kp_select):
            sel.set_disabled(mode != "filter")
        self.type_select.set_disabled(mode == "wrong")
        self.filter_note.setVisible(mode != "filter")

        if mode == "random":
            tp = self.session.filters.get("type")
            scope = {"single": "仅单选", "multiple": "仅多选"}.get(tp or "", "")
            if scope:
                self.mode_hint.setText(f"按掌握度与错误频率排序，范围：{scope}。")
            else:
                self.mode_hint.setText("按掌握度、错误频率与知识点覆盖排序，优先薄弱环节。")
        elif mode == "filter":
            self.mode_hint.setText("按章节 / 知识点 / 题型组合筛选，顺序练习。")
        else:
            self.mode_hint.setText(f"只抽错题本中的题（当前 {len(self.session.wrong_ids())} 题）。")

        stats = self.session.stats()
        total = self.session.total
        self.queue_chip.setText(f"本轮 {total} 题")
        self.queue_chip.set_kind("primary" if total else "danger")
        self.queue_chip.setToolTip(f"已作答 {stats.attempted} / {stats.total} 题")

        chapter = self.session.filters.get("chapter")
        if chapter != self.chapter_select.value:
            self.chapter_select.set_value(chapter)
            self._rebuild_kp_items()
        self.kp_select.set_value(self.session.filters.get("knowledge"))
        self.type_select.set_value(self.session.filters.get("type"))

    @property
    def filters(self) -> dict:
        return {
            "chapter": self.chapter_select.value,
            "knowledge": self.kp_select.value,
            "type": self.type_select.value,
        }
