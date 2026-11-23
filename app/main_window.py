# -*- coding: utf-8 -*-
"""主窗口：组装侧栏、题目区、统计面板，并串联答题流程。"""
from __future__ import annotations

import random

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import (QActionGroup, QColor, QIcon, QKeySequence, QLinearGradient,
                           QPainter, QPainterPath, QPixmap, QShortcut)
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QMainWindow,
                               QMenu, QMessageBox, QPushButton, QStackedWidget,
                               QVBoxLayout, QWidget)

from .models import Bank
from .session import MODE_LABELS, QuizSession
from .store import ProgressStore
from .ui import theme
from .ui.insights import InsightsPanel
from .ui.question_view import QuestionView
from .ui.sidebar import Sidebar
from .ui.widgets import EmptyState, RingIndicator, ThemeToggle


def _app_icon() -> QIcon:
    pm = QPixmap(128, 128)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    grad = QLinearGradient(0, 0, 128, 128)
    grad.setColorAt(0, QColor("#4A6BF0"))
    grad.setColorAt(1, QColor("#7A5BE0"))
    path = QPainterPath()
    path.addRoundedRect(4, 4, 120, 120, 30, 30)
    p.fillPath(path, grad)
    p.setPen(QColor("#FFFFFF"))
    f = theme.base_font(52, 700)
    p.setFont(f)
    p.drawText(pm.rect(), Qt.AlignCenter, "习")
    p.end()
    return QIcon(pm)


class MainWindow(QMainWindow):
    def __init__(self, bank: Bank, store: ProgressStore):
        super().__init__()
        self.bank = bank
        self.store = store
        self.session = QuizSession(bank, store, random.Random())
        self._insights_manual: bool | None = None
        self._last_width = 0

        self.setWindowTitle("习概选择题 · 复习训练")
        self.setWindowIcon(_app_icon())
        self.setMinimumSize(980, 620)

        self._restore_prefs()
        self._build_ui()
        self._bind_shortcuts()
        self._refresh_all()
        self._initial_size()

    # ---------------------------------------------------------------- 初始化
    def _restore_prefs(self) -> None:
        mode = self.store.get_pref("mode", "random")
        if mode in MODE_LABELS:
            self.session.mode = mode
            self.session.filters = {
                "chapter": self.store.get_pref("filter_chapter"),
                "knowledge": self.store.get_pref("filter_knowledge"),
                "type": self.store.get_pref("filter_type"),
            }
            self.session.rebuild(keep_current=False)

    def _initial_size(self) -> None:
        screen = self.screen().availableGeometry()
        w = min(1360, int(screen.width() * 0.86))
        h = min(880, int(screen.height() * 0.86))
        self.resize(max(980, w), max(620, h))
        self.move(screen.center() - self.rect().center())

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        row = QHBoxLayout(root)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        self.sidebar = Sidebar(self.session)
        row.addWidget(self.sidebar)

        content = QWidget()
        row.addWidget(content, 1)
        col = QVBoxLayout(content)
        col.setContentsMargins(24, 20, 24, 22)
        col.setSpacing(14)
        self.content_col = col

        # ---- 顶栏
        top = QHBoxLayout()
        top.setSpacing(10)
        titles = QVBoxLayout()
        titles.setSpacing(2)
        self.page_title = QLabel("随机练习")
        self.page_title.setStyleSheet("font-size:17pt; font-weight:700;")
        self.page_sub = QLabel("")
        self.page_sub.setObjectName("hint")
        titles.addWidget(self.page_title)
        titles.addWidget(self.page_sub)
        top.addLayout(titles, 1)

        self.restart_btn = QPushButton("重新开始")
        self.restart_btn.setObjectName("ghost")
        self.restart_btn.setCursor(Qt.PointingHandCursor)
        self.restart_btn.setToolTip("打乱并重新开始本轮练习，统计不会清零")
        self.restart_btn.clicked.connect(self._restart_round)
        top.addWidget(self.restart_btn, 0)

        self.toggle_btn = QPushButton("统计面板")
        self.toggle_btn.setObjectName("ghost")
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(True)
        self.toggle_btn.clicked.connect(self._toggle_insights)
        top.addWidget(self.toggle_btn, 0)

        self.theme_btn = ThemeToggle(theme.is_dark())
        self.theme_btn.clicked.connect(self._toggle_theme)
        top.addWidget(self.theme_btn, 0)

        self.font_btn = QPushButton("Aa")
        self.font_btn.setObjectName("chipBtn")
        self.font_btn.setFixedSize(38, 38)
        self.font_btn.setCursor(Qt.PointingHandCursor)
        self.font_btn.setToolTip("字体大小")
        self.font_btn.clicked.connect(self._show_font_menu)
        top.addWidget(self.font_btn, 0)
        col.addLayout(top)

        # ---- 主体
        body = QHBoxLayout()
        body.setSpacing(18)
        col.addLayout(body, 1)

        self.stack = QStackedWidget()
        body.addWidget(self.stack, 1)

        self.view = QuestionView()
        self.view.set_glossary(self.bank.glossary)
        self.view.set_bank(self.bank)
        self.stack.addWidget(self.view)

        # 空状态页
        self.empty_page = QFrame()
        self.empty_page.setObjectName("card")
        theme.apply_shadow(self.empty_page, blur=30, dy=8, alpha=22)
        e_lay = QVBoxLayout(self.empty_page)
        e_lay.setContentsMargins(30, 30, 30, 30)
        e_lay.setSpacing(6)
        e_lay.addStretch(1)
        self.empty_state = EmptyState("没有符合条件的题目", "试试放宽筛选条件，或换个练习模式。")
        e_lay.addWidget(self.empty_state, 0)
        self.empty_action = QPushButton("去随机练习")
        self.empty_action.setObjectName("primary")
        self.empty_action.setCursor(Qt.PointingHandCursor)
        self.empty_action.clicked.connect(self._empty_action)
        e_lay.addWidget(self.empty_action, 0, Qt.AlignHCenter)
        e_lay.addStretch(1)
        self.stack.addWidget(self.empty_page)

        # 完成页
        self.done_page = QFrame()
        self.done_page.setObjectName("card")
        theme.apply_shadow(self.done_page, blur=30, dy=8, alpha=22)
        d_lay = QVBoxLayout(self.done_page)
        d_lay.setContentsMargins(36, 34, 36, 34)
        d_lay.setSpacing(12)
        d_lay.addStretch(1)
        self.done_ring = RingIndicator(150)
        d_lay.addWidget(self.done_ring, 0, Qt.AlignHCenter)
        self.done_title = QLabel("本轮练习完成")
        self.done_title.setStyleSheet("font-size:17pt; font-weight:700;")
        self.done_title.setAlignment(Qt.AlignCenter)
        d_lay.addWidget(self.done_title)
        self.done_text = QLabel("")
        self.done_text.setObjectName("hint")
        self.done_text.setAlignment(Qt.AlignCenter)
        self.done_text.setWordWrap(True)
        d_lay.addWidget(self.done_text)
        btns = QHBoxLayout()
        btns.setSpacing(10)
        again = QPushButton("再来一轮")
        again.setObjectName("primary")
        again.setCursor(Qt.PointingHandCursor)
        again.clicked.connect(self._restart_round)
        only_wrong = QPushButton("只看错题")
        only_wrong.setObjectName("ghost")
        only_wrong.setCursor(Qt.PointingHandCursor)
        only_wrong.clicked.connect(lambda: self._switch_mode("wrong"))
        btns.addStretch(1)
        btns.addWidget(again)
        btns.addWidget(only_wrong)
        btns.addStretch(1)
        d_lay.addLayout(btns)
        d_lay.addStretch(1)
        self.stack.addWidget(self.done_page)

        self.insights = InsightsPanel(self.session)
        body.addWidget(self.insights, 0)

        # ---- 信号
        self.sidebar.modeChanged.connect(self._on_mode)
        self.sidebar.filtersChanged.connect(self._on_filters)
        self.sidebar.restartRequested.connect(self._restart_round)
        self.view.submitted.connect(self._on_submit)
        self.view.nextRequested.connect(self._on_next)
        self.view.prevRequested.connect(self._on_prev)
        self.view.redoRequested.connect(self.view.unlock)
        self.insights.jumpRequested.connect(self._jump_to)
        self.insights.resetRequested.connect(self._reset_progress)

    def _bind_shortcuts(self) -> None:
        for key in ["A", "B", "C", "D", "E"]:
            QShortcut(QKeySequence(key), self, activated=lambda k=key: self.view.toggle_key(k))
            QShortcut(QKeySequence(key.lower()), self, activated=lambda k=key: self.view.toggle_key(k))
        for i, key in enumerate(["A", "B", "C", "D", "E"], start=1):
            QShortcut(QKeySequence(str(i)), self, activated=lambda k=key: self.view.toggle_key(k))
        QShortcut(QKeySequence(Qt.Key_Return), self, activated=self._enter)
        QShortcut(QKeySequence(Qt.Key_Enter), self, activated=self._enter)
        QShortcut(QKeySequence(Qt.Key_Left), self, activated=self._on_prev)
        QShortcut(QKeySequence(Qt.Key_Right), self, activated=self._on_next)
        QShortcut(QKeySequence("R"), self, activated=self._shuffle)
        QShortcut(QKeySequence("r"), self, activated=self._shuffle)

    # ---------------------------------------------------------------- 流程
    def _enter(self) -> None:
        q = self.session.current
        if q is None:
            return
        record = self.session.state_of(q.id)
        if record is not None:
            self._on_next()
        elif self.view.has_selection:
            self.view.submit()

    def _on_submit(self, chosen: list[str]) -> None:
        q = self.session.current
        if q is None:
            return
        correct = self.session.submit(chosen)
        record = self.session.state_of(q.id) or {}
        self.view.mark_submitted(chosen, correct, record.get("attempts", 1))
        self.view.set_assessment(q, record)
        self.view.set_nav(self.session.index > 0, self.session.index + 1 < self.session.total)
        self.insights.refresh()
        self.sidebar.refresh()
        self._save()

    def _on_next(self) -> None:
        if self.stack.currentIndex() == 2:
            return
        if self.session.current is None:
            return
        self.session.go_next()
        self._render()

    def _on_prev(self) -> None:
        if self.stack.currentIndex() == 2:
            self.session.index = max(0, self.session.total - 1)
            self._render()
            return
        if self.session.go_prev():
            self._render()

    def _on_mode(self, mode: str) -> None:
        self.session.set_mode(mode)
        self.store.set_pref("mode", mode)
        self._refresh_all()
        self._save()

    def _switch_mode(self, mode: str) -> None:
        if mode == self.session.mode:
            self.session.rebuild(keep_current=False)
        else:
            self.session.set_mode(mode)
        self.store.set_pref("mode", mode)
        self._refresh_all()
        self._save()

    def _on_filters(self) -> None:
        f = self.sidebar.filters
        self.session.set_filters(f["chapter"], f["knowledge"], f["type"])
        self.store.set_pref("filter_chapter", f["chapter"])
        self.store.set_pref("filter_knowledge", f["knowledge"])
        self.store.set_pref("filter_type", f["type"])
        self._refresh_all()
        self._save()

    def _restart_round(self) -> None:
        self.session.rebuild(keep_current=False)
        if self.session.mode == "random":
            self.session.reshuffle()
        self._render()
        self.insights.refresh()
        self.sidebar.refresh()

    def _shuffle(self) -> None:
        if self.stack.currentIndex() != 0:
            return
        self.session.reshuffle()
        self.session.index = 0
        self._render()

    def _empty_action(self) -> None:
        if self.session.mode == "filter":
            self.sidebar.chapter_select.set_value(None)
            self.sidebar.kp_select.set_value(None)
            self.sidebar.type_select.set_value(None)
            self._on_filters()
        else:
            self._switch_mode("random")

    def _jump_to(self, question_id: str) -> None:
        if self.session.jump_to(question_id):
            self._render()
            return
        self.session.set_mode("wrong")
        self.store.set_pref("mode", "wrong")
        self.session.jump_to(question_id)
        self._refresh_all()

    def _reset_progress(self) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("重置进度")
        box.setText("确定清空全部作答记录与错题本吗？")
        box.setInformativeText("此操作不可撤销，统计将重新开始。")
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.setDefaultButton(QMessageBox.No)
        box.button(QMessageBox.Yes).setText("清空")
        box.button(QMessageBox.No).setText("取消")
        if box.exec() != QMessageBox.Yes:
            return
        self.store.reset()
        self.session.rebuild(keep_current=False)
        self.store.set_pref("mode", self.session.mode)
        self._refresh_all()
        self._save()

    # ---------------------------------------------------------------- 渲染
    def _refresh_all(self) -> None:
        self.sidebar.refresh()
        self.insights.refresh()
        self._render()

    def _render(self) -> None:
        self._update_title()
        q = self.session.current
        if q is None:
            if self.session.total == 0:
                self._show_empty()
            else:
                self._show_done()
            return
        self.stack.setCurrentIndex(0)
        record = self.session.state_of(q.id)
        review = self.session.mode != "wrong"   # 错题模式默认重新作答
        self.view.load(q, self.session.index, self.session.total, record, review=review)
        self.view.set_nav(self.session.index > 0,
                          self.session.index + 1 < self.session.total)

    def _update_title(self) -> None:
        mode = self.session.mode
        self.page_title.setText(MODE_LABELS[mode])
        parts = [f"本轮 {self.session.total} 题"]
        if mode == "filter":
            chips = []
            if self.session.filters.get("chapter"):
                chips.append(self.bank.chapter(self.session.filters["chapter"]).short)
            if self.session.filters.get("knowledge"):
                chips.append(self.session.filters["knowledge"])
            if self.session.filters.get("type"):
                chips.append("单选题" if self.session.filters["type"] == "single" else "多选题")
            parts.append("筛选：" + " / ".join(chips) if chips else "未设置筛选（全部题目）")
        elif mode == "wrong":
            parts.append(f"错题本 {len(self.session.wrong_ids())} 题")
        else:
            tp = self.session.filters.get("type")
            if tp:
                parts.append("范围：" + ("单选题" if tp == "single" else "多选题"))
            parts.append("按掌握度与错误频率排序")
        st = self.session.stats()
        parts.append(f"已做 {st.attempted}/{st.total}")
        self.page_sub.setText("　·　".join(parts))

    def _show_empty(self) -> None:
        if self.session.mode == "wrong":
            self.empty_state.title.setText("错题本还是空的")
            self.empty_state.text.setText("先做几道题，答错的题目会自动收集到这里，\n答对后会自动移出。")
            self.empty_action.setText("去随机练习")
        else:
            self.empty_state.title.setText("没有符合条件的题目")
            self.empty_state.text.setText("当前筛选组合下没有题目，\n试试放宽条件或清除筛选。")
            self.empty_action.setText("清除筛选")
        self.stack.setCurrentIndex(1)

    def _show_done(self) -> None:
        self.stack.setCurrentIndex(2)
        ids = self.session.queue
        done = [i for i in ids if self.session.state_of(i)]
        right = [i for i in done if (self.session.state_of(i) or {}).get("correct")]
        wrong = len(done) - len(right)
        acc = len(right) / len(done) if done else 0.0
        self.done_ring.set_value(acc, f"{acc * 100:.0f}%", "本轮正确率")
        if not done:
            self.done_title.setText("本轮还没有作答")
            self.done_text.setText("从第一题开始吧，作答记录会自动保存。")
            return
        self.done_title.setText("本轮练习完成")
        self.done_text.setText(
            f"本轮共 {len(ids)} 题，已作答 {len(done)} 题　·　"
            f"正确 {len(right)}　·　错误 {wrong}")

    # ---------------------------------------------------------------- 其他
    def _toggle_theme(self) -> None:
        target = "light" if theme.is_dark() else "dark"
        theme.set_mode(target)
        self._apply_theme()
        self.theme_btn.set_dark(target == "dark")
        self.store.set_pref("theme", target)
        self._save()

    def _show_font_menu(self) -> None:
        menu = QMenu(self)
        group = QActionGroup(menu)
        group.setExclusive(True)
        for level in ("small", "medium", "large"):
            act = menu.addAction(f"{theme.FONT_LABELS[level]}号字")
            act.setCheckable(True)
            act.setChecked(theme.font_level() == level)
            act.triggered.connect(lambda _=False, lv=level: self._set_font_level(lv))
            group.addAction(act)
        menu.setMinimumWidth(self.font_btn.width() + 60)
        menu.exec(self.font_btn.mapToGlobal(QPoint(0, self.font_btn.height() + 6)))

    def _set_font_level(self, level: str) -> None:
        theme.set_font_scale(level)
        self._apply_theme()
        self.store.set_pref("font_scale", level)
        self._save()

    def _apply_theme(self) -> None:
        app = QApplication.instance()
        if app is None:
            return
        app.setFont(theme.base_font(10))
        app.setPalette(theme.app_palette())
        app.setStyleSheet(theme.qss())
        for widget in app.allWidgets():
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()
        theme.refresh_shadows()

    def _toggle_insights(self) -> None:
        self._insights_manual = self.toggle_btn.isChecked()
        self._apply_insights_visibility()

    def _apply_insights_visibility(self) -> None:
        if self._insights_manual is None:
            visible = self.width() >= 1180
        else:
            visible = self._insights_manual
        self.insights.setVisible(visible)
        self.toggle_btn.setChecked(visible)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if abs(self.width() - self._last_width) > 4:
            self._last_width = self.width()
            self._apply_insights_visibility()
            self._apply_content_width()

    def _apply_content_width(self) -> None:
        """超宽屏时把内容区限制在舒适阅读宽度内并居中，避免行过长。"""
        inner = self.width() - self.sidebar.width()
        side = max(24, (inner - 1400) // 2)
        self.content_col.setContentsMargins(side, 20, side, 22)

    def _save(self) -> None:
        QTimer.singleShot(120, self._flush)

    def _flush(self) -> None:
        self.store.set_pref("mode", self.session.mode)
        self.store.save()

    def closeEvent(self, event) -> None:
        self._flush()
        super().closeEvent(event)
