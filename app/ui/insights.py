# -*- coding: utf-8 -*-
"""右侧统计面板：正确率环图、指标卡、错题本。"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton,
                               QScrollArea, QSizePolicy, QVBoxLayout, QWidget)

from ..session import QuizSession
from . import theme
from .widgets import Chip, HLine, RingIndicator, StatTile, WrongItem


class InsightsPanel(QWidget):
    jumpRequested = Signal(str)
    resetRequested = Signal()

    def __init__(self, session: QuizSession, parent=None):
        super().__init__(parent)
        self.session = session
        self._wrong_ids: list[str] = []
        self.setFixedWidth(316)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("card")
        theme.apply_shadow(card, blur=30, dy=8, alpha=20)
        outer.addWidget(card)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 20, 20, 16)
        lay.setSpacing(14)

        title = QLabel("学习统计")
        title.setObjectName("sectionLabel")
        lay.addWidget(title)

        self.ring = RingIndicator(136)
        lay.addWidget(self.ring, 0, Qt.AlignHCenter)

        tiles = QHBoxLayout()
        tiles.setSpacing(6)
        self.tile_done = StatTile("已做")
        self.tile_right = StatTile("正确")
        self.tile_wrong = StatTile("错误")
        for t in (self.tile_done, self.tile_right, self.tile_wrong):
            tiles.addWidget(t, 1)
        lay.addLayout(tiles)

        self.coverage = QLabel("覆盖 0 / 271 题")
        self.coverage.setObjectName("hint")
        self.coverage.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.coverage)

        self.due = QLabel("")
        self.due.setToolTip("做过且掌握度低于 55% 的题数")
        self.due.setObjectName("hint")
        self.due.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.due)

        lay.addWidget(HLine())

        head = QHBoxLayout()
        head.setSpacing(8)
        wrong_title = QLabel("错题本")
        wrong_title.setObjectName("sectionLabel")
        self.wrong_count = Chip("0 题", "danger")
        head.addWidget(wrong_title, 0)
        head.addStretch(1)
        head.addWidget(self.wrong_count, 0)
        lay.addLayout(head)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        host = QWidget()
        host_lay = QVBoxLayout(host)
        host_lay.setContentsMargins(0, 0, 4, 0)
        host_lay.setSpacing(2)

        self.empty = QLabel("还没有错题。\n答错的题目会自动收进这里，\n答对后自动移出。")
        self.empty.setObjectName("hint")
        self.empty.setAlignment(Qt.AlignCenter)
        self.empty.setWordWrap(True)
        host_lay.addWidget(self.empty)

        self.items_host = QWidget()
        self.items_lay = QVBoxLayout(self.items_host)
        self.items_lay.setContentsMargins(0, 0, 0, 0)
        self.items_lay.setSpacing(4)
        host_lay.addWidget(self.items_host)
        host_lay.addStretch(1)

        self.scroll.setWidget(host)
        lay.addWidget(self.scroll, 1)

        self.reset_btn = QPushButton("重置全部进度")
        self.reset_btn.setObjectName("link")
        self.reset_btn.setCursor(Qt.PointingHandCursor)
        self.reset_btn.clicked.connect(self.resetRequested.emit)
        lay.addWidget(self.reset_btn, 0, Qt.AlignHCenter)

        self.refresh()

    # ---------------------------------------------------------------- 刷新
    def refresh(self) -> None:
        st = self.session.stats()
        self.ring.set_value(st.accuracy, f"{st.accuracy * 100:.0f}%", "正确率")
        self.tile_done.set_value(st.attempted)
        self.tile_right.set_value(st.correct)
        self.tile_wrong.set_value(st.wrong)
        self.coverage.setText(f"覆盖 {st.attempted} / {st.total} 题")
        weak = self.session.weak_count()
        self.due.setText(f"待巩固 {weak} 题" if weak else "")
        self.wrong_count.setText(f"{st.wrong} 题")
        self.wrong_count.set_kind("danger" if st.wrong else "success")

        ids = self.session.wrong_ids()
        if ids != self._wrong_ids:
            self._wrong_ids = ids
            self._rebuild_list(ids)

        self.empty.setVisible(not ids)

    def _rebuild_list(self, ids: list[str]) -> None:
        while self.items_lay.count():
            item = self.items_lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        for qid in ids:
            q = self.session.bank.by_id.get(qid)
            if q is None:
                continue
            item = WrongItem(q)
            item.clicked.connect(self.jumpRequested.emit)
            self.items_lay.addWidget(item)
