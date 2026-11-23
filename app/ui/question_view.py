# -*- coding: utf-8 -*-
"""题目主视图：题干、选项、作答反馈。"""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton,
                               QScrollArea, QSizePolicy, QVBoxLayout, QWidget)

from .. import priority
from ..glossary import match_terms
from ..models import Question
from . import theme
from .widgets import Chip, HLine, OptionRow, ResultIcon, WrapLabel


class ProgressLine(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0.0
        self.setFixedHeight(4)

    def set_value(self, value: float) -> None:
        self._value = max(0.0, min(1.0, value))
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect())
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(theme.TRACK))
        p.drawRoundedRect(r, 2, 2)
        if self._value > 0:
            grad = QLinearGradient(r.topLeft(), r.topRight())
            grad.setColorAt(0, QColor(theme.GRAD_A))
            grad.setColorAt(1, QColor(theme.GRAD_B))
            p.setBrush(grad)
            p.drawRoundedRect(QRectF(r.left(), r.top(), r.width() * self._value, r.height()), 2, 2)


class QuestionView(QWidget):
    """一次展示一道题；作答、翻页由外部控制。"""

    submitted = Signal(list)
    nextRequested = Signal()
    prevRequested = Signal()
    redoRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.question: Question | None = None
        self._glossary: dict[str, str] = {}
        self._bank = None
        self._rows: dict[str, OptionRow] = {}
        self._chosen: set[str] = set()
        self._locked = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.card = QFrame()
        self.card.setObjectName("card")
        theme.apply_shadow(self.card, blur=30, dy=8, alpha=22)
        root.addWidget(self.card)

        card = QVBoxLayout(self.card)
        card.setContentsMargins(30, 22, 30, 18)
        card.setSpacing(14)

        # ---- 顶部信息
        top = QHBoxLayout()
        top.setSpacing(8)
        self.chapter_chip = Chip("导论", "primary")
        self.type_chip = Chip("单选")
        self.kp_chip = Chip("知识点", "default")
        self.counter = QLabel("1 / 1")
        self.counter.setObjectName("qmeta")
        top.addWidget(self.chapter_chip, 0)
        top.addWidget(self.type_chip, 0)
        top.addWidget(self.kp_chip, 0)
        top.addStretch(1)
        top.addWidget(self.counter, 0)
        card.addLayout(top)

        self.progress = ProgressLine()
        card.addWidget(self.progress)

        # ---- 可滚动内容
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.viewport().setAutoFillBackground(False)
        inner = QWidget()
        inner.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.body = QVBoxLayout(inner)
        self.body.setContentsMargins(0, 2, 6, 4)
        self.body.setSpacing(16)

        self.stem = WrapLabel("")
        self.stem.setObjectName("stem")
        self.stem.setTextFormat(Qt.PlainText)
        self.stem.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        # 题干高度随换行增长；剩余空白由布局末尾的 stretch 吸收
        stem_policy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        stem_policy.setHeightForWidth(True)
        self.stem.setSizePolicy(stem_policy)
        self.body.addWidget(self.stem)

        self.options_box = QVBoxLayout()
        self.options_box.setSpacing(10)
        self.body.addLayout(self.options_box)

        self.feedback = QFrame()
        self.feedback.setObjectName("feedback")
        self.feedback.setVisible(False)
        fb = QVBoxLayout(self.feedback)
        fb.setContentsMargins(16, 14, 16, 14)
        fb.setSpacing(10)
        head = QHBoxLayout()
        head.setSpacing(10)
        self.fb_icon_holder = QHBoxLayout()
        self.fb_title = QLabel("回答正确")
        self.fb_title.setObjectName("feedbackTitle")
        head.addLayout(self.fb_icon_holder, 0)
        head.addWidget(self.fb_title, 1)
        fb.addLayout(head)

        self.fb_line = WrapLabel("")
        self.fb_line.setObjectName("feedbackLine")
        self.fb_line.setTextFormat(Qt.PlainText)
        fb.addWidget(self.fb_line)

        self.fb_schedule = QLabel("")
        self.fb_schedule.setObjectName("scheduleText")
        self.fb_schedule.setVisible(False)
        fb.addWidget(self.fb_schedule)

        self.explain_box = QVBoxLayout()
        self.explain_box.setSpacing(4)
        tag = QLabel("解析")
        tag.setObjectName("explainTitle")
        self.fb_explain = WrapLabel("")
        self.fb_explain.setObjectName("explainText")
        self.fb_explain.setTextFormat(Qt.PlainText)
        self.explain_box.addWidget(tag)
        self.explain_box.addWidget(self.fb_explain)
        fb.addLayout(self.explain_box)

        # ---- 名词解释（命中术语时才显示）
        self.glossary_box = QWidget()
        gb = QVBoxLayout(self.glossary_box)
        gb.setContentsMargins(0, 2, 0, 0)
        gb.setSpacing(8)
        self.glossary_tag = QLabel("名词解释")
        self.glossary_tag.setObjectName("explainTitle")
        self.glossary_body = QVBoxLayout()
        self.glossary_body.setSpacing(8)
        gb.addWidget(self.glossary_tag)
        gb.addLayout(self.glossary_body)
        self.glossary_box.setVisible(False)
        fb.addWidget(self.glossary_box)

        self.fb_note = WrapLabel("")
        self.fb_note.setObjectName("explainText")
        self.fb_note.setObjectName("fbNote")
        self.fb_note.setVisible(False)
        fb.addWidget(self.fb_note)

        self.placeholder = QFrame()
        self.placeholder.setObjectName("placeholder")
        self.placeholder.setFixedHeight(132)
        self.placeholder.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        ph = QVBoxLayout(self.placeholder)
        ph.setContentsMargins(24, 24, 24, 24)
        ph.setSpacing(6)
        ph.setAlignment(Qt.AlignCenter)
        self.placeholder_title = QLabel("作答后显示正确答案与解析")
        self.placeholder_title.setObjectName("placeholderTitle")
        self.placeholder_title.setAlignment(Qt.AlignCenter)
        self.placeholder_text = QLabel("选择选项后点击「提交答案」，或按 Enter")
        self.placeholder_text.setObjectName("placeholderText")
        self.placeholder_text.setAlignment(Qt.AlignCenter)
        self.placeholder_text.setWordWrap(False)
        ph.addWidget(self.placeholder_title)
        ph.addWidget(self.placeholder_text)

        self.feedback.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.body.addWidget(self.placeholder, 0)
        self.body.addWidget(self.feedback)
        self.body.addStretch(1)
        self.scroll.setWidget(inner)
        card.addWidget(self.scroll, 1)

        # ---- 底部操作
        card.addWidget(HLine())
        foot = QHBoxLayout()
        foot.setSpacing(10)
        self.hint = QLabel("A–D / 1–5 选择　Enter 提交")
        self.hint.setObjectName("hint")
        self.prev_btn = QPushButton("上一题")
        self.prev_btn.setObjectName("ghost")
        self.prev_btn.setCursor(Qt.PointingHandCursor)
        self.prev_btn.clicked.connect(self.prevRequested.emit)
        self.submit_btn = QPushButton("提交答案")
        self.submit_btn.setObjectName("primary")
        self.submit_btn.setCursor(Qt.PointingHandCursor)
        self.submit_btn.clicked.connect(self.submit)
        self.next_btn = QPushButton("下一题")
        self.next_btn.setObjectName("primary")
        self.next_btn.setCursor(Qt.PointingHandCursor)
        self.next_btn.clicked.connect(self.nextRequested.emit)
        self.next_btn.setVisible(False)
        self.redo_btn = QPushButton("重做本题")
        self.redo_btn.setObjectName("ghost")
        self.redo_btn.setCursor(Qt.PointingHandCursor)
        self.redo_btn.setVisible(False)
        self.redo_btn.clicked.connect(self.redoRequested.emit)
        foot.addWidget(self.hint, 0)
        foot.addStretch(1)
        foot.addWidget(self.prev_btn, 0)
        foot.addWidget(self.redo_btn, 0)
        foot.addWidget(self.submit_btn, 0)
        foot.addWidget(self.next_btn, 0)
        card.addLayout(foot)

    def set_assessment(self, question: Question | None, record: dict | None) -> None:
        """展示本题的掌握度与错误情况（纯计数，不含时间概念）。"""
        if question is None or not record:
            self.fb_schedule.setVisible(False)
            return
        self.fb_schedule.setText("本题评估：" + priority.explain(question, record))
        self.fb_schedule.setVisible(True)

    def set_glossary(self, glossary: dict[str, str]) -> None:
        self._glossary = dict(glossary or {})

    def set_bank(self, bank) -> None:
        self._bank = bank

    def _render_glossary(self, question: Question) -> None:
        while self.glossary_body.count():
            item = self.glossary_body.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        terms = match_terms(question, self._glossary)
        for term, explain in terms:
            holder = QWidget()
            box = QVBoxLayout(holder)
            box.setContentsMargins(0, 0, 0, 0)
            box.setSpacing(2)
            name = QLabel(f"「{term}」")
            name.setObjectName("glossaryTerm")
            desc = WrapLabel(explain)
            desc.setObjectName("glossaryText")
            desc.setTextFormat(Qt.PlainText)
            box.addWidget(name)
            box.addWidget(desc)
            self.glossary_body.addWidget(holder)
        self.glossary_box.setVisible(bool(terms))

    # ---------------------------------------------------------------- 渲染
    def _clear_options(self) -> None:
        while self.options_box.count():
            item = self.options_box.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._rows.clear()

    def load(self, question: Question, index: int, total: int,
             record: dict | None = None, review: bool = True) -> None:
        self.question = question
        self._chosen = set()
        self._locked = False
        self.scroll.verticalScrollBar().setValue(0)

        self.chapter_chip.setText(question.chapter.split(" ")[0])
        self.type_chip.setText(question.type_label)
        self.type_chip.set_kind("amber" if question.is_multiple else "default")
        kp = question.knowledge
        self.kp_chip.setText(kp if len(kp) <= 16 else kp[:15] + "…")
        self.kp_chip.setToolTip(kp)
        self.counter.setText(f"{index + 1} / {total}")
        self.progress.set_value((index + 1) / max(1, total))

        self.stem.setText(question.stem)
        self._clear_options()
        for opt in question.options:
            row = OptionRow(opt.key, opt.text)
            row.clicked.connect(self._toggle)
            self.options_box.addWidget(row)
            self._rows[opt.key] = row

        self.feedback.setVisible(False)
        self.glossary_box.setVisible(False)
        self.fb_schedule.setVisible(False)
        self.placeholder.setVisible(True)
        self.submit_btn.setVisible(True)
        self.next_btn.setVisible(False)
        self.redo_btn.setVisible(False)
        self.prev_btn.setEnabled(index > 0)
        self.hint.setText("A–D / 1–5 选择　Enter 提交" if not question.is_multiple
                          else "可多选　Enter 提交")
        self._update_submit_state()

        if record and review:
            chosen = record.get("chosen") or []
            self._locked = True
            self._chosen = set(chosen)
            self._paint_result(bool(record.get("correct")), chosen, record.get("attempts", 1))
            self.set_assessment(question, record)

    def _update_submit_state(self) -> None:
        self.submit_btn.setEnabled(bool(self._chosen) and not self._locked)

    # ---------------------------------------------------------------- 交互
    def _toggle(self, key: str) -> None:
        if self._locked or self.question is None:
            return
        if self.question.is_multiple:
            if key in self._chosen:
                self._chosen.discard(key)
            else:
                self._chosen.add(key)
        else:
            self._chosen = {key}
        for k, row in self._rows.items():
            if k in self._chosen:
                row.set_state("selected")
            else:
                row.set_state("idle")
        self._update_submit_state()

    def toggle_key(self, key: str) -> None:
        if key in self._rows:
            self._toggle(key)

    @property
    def is_locked(self) -> bool:
        """当前题是否已经提交并展示反馈。"""
        return self._locked

    @property
    def has_selection(self) -> bool:
        return bool(self._chosen)

    def submit(self) -> None:
        """提交当前选择（供快捷键或外部调用）。"""
        if self._locked or not self._chosen or self.question is None:
            return
        self.submitted.emit(sorted(self._chosen))

    def mark_submitted(self, chosen: list[str], correct: bool, attempts: int = 1) -> None:
        self._chosen = set(chosen)
        self._locked = True
        self._paint_result(correct, chosen, attempts)
        # 布局完成后再滚动，保证解析可见（回看已答题时不打扰）
        QTimer.singleShot(0, lambda: self.scroll.ensureWidgetVisible(self.feedback, 0, 16))

    def _paint_result(self, correct: bool, chosen: list[str], attempts: int) -> None:
        q = self.question
        assert q is not None
        answers = set(q.answer)
        for key, row in self._rows.items():
            if key in answers and key in chosen:
                row.set_state("correct")
            elif key in answers:
                row.set_state("missed")
            elif key in chosen:
                row.set_state("wrong")
            else:
                row.set_state("readonly", dim=True)
            row.set_interactive(False)

        # 反馈面板
        while self.fb_icon_holder.count():
            item = self.fb_icon_holder.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.fb_icon_holder.addWidget(ResultIcon(correct))
        self.fb_title.setText("回答正确" if correct else "回答错误")
        self.fb_title.setProperty("result", "ok" if correct else "bad")
        self.fb_title.style().unpolish(self.fb_title)
        self.fb_title.style().polish(self.fb_title)
        self.feedback.setProperty("result", "ok" if correct else "bad")
        self.feedback.style().unpolish(self.feedback)
        self.feedback.style().polish(self.feedback)

        chosen_text = "、".join(sorted(chosen)) or "未作答"
        ans_text = "、".join(sorted(answers))
        extra = f"（本题已作答 {attempts} 次）" if attempts > 1 else ""
        self.fb_line.setText(f"你的答案：{chosen_text}　·　正确答案：{ans_text}{extra}")
        self.fb_explain.setText(q.explanation or "暂无解析")
        self.fb_note.setVisible(bool(q.note))
        if q.note:
            self.fb_note.setText(f"提示：{q.note}")
        self._render_glossary(q)
        self.feedback.setVisible(True)
        self.placeholder.setVisible(False)

        self.submit_btn.setVisible(False)
        self.next_btn.setVisible(True)
        self.redo_btn.setVisible(True)
        self.hint.setText("Enter 继续下一题　← → 翻页")

    def unlock(self) -> None:
        """重做本题：清空选择与反馈，恢复可作答状态。"""
        if self.question is None:
            return
        self._locked = False
        self._chosen = set()
        for row in self._rows.values():
            row.set_state("idle")
            row.set_interactive(True)
        self.feedback.setVisible(False)
        self.glossary_box.setVisible(False)
        self.fb_schedule.setVisible(False)
        self.placeholder.setVisible(True)
        self.submit_btn.setVisible(True)
        self.next_btn.setVisible(False)
        self.redo_btn.setVisible(False)
        self.hint.setText("A–D / 1–5 选择　Enter 提交" if not self.question.is_multiple
                          else "可多选　Enter 提交")
        self._update_submit_state()

    # ---------------------------------------------------------------- 状态
    def set_nav(self, can_prev: bool, has_next: bool) -> None:
        self.prev_btn.setEnabled(can_prev)
        if self._locked:
            self.next_btn.setText("下一题" if has_next else "完成本轮")
