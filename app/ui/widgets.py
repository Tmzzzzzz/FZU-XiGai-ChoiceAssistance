# -*- coding: utf-8 -*-
"""可复用界面组件。"""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPoint, QRectF, QVariantAnimation, Qt, Signal
from PySide6.QtGui import (QActionGroup, QColor, QLinearGradient, QPainter,
                           QPainterPath, QPalette, QPen)
from PySide6.QtWidgets import (QAbstractButton, QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QMenu, QPushButton,
                               QSizePolicy, QVBoxLayout, QWidget)

from . import theme


# ------------------------------------------------------------------ 基础块
class WrapLabel(QLabel):
    """自动换行标签：随宽度同步最小高度，避免在滚动容器中被裁切。"""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setWordWrap(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

    def setText(self, text: str) -> None:  # noqa: N802
        super().setText(text)
        self._sync_height()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_height()

    def _sync_height(self) -> None:
        width = self.width()
        if width <= 0:
            return
        need = self.heightForWidth(width)
        if need > 0 and abs(self.minimumHeight() - need) > 1:
            self.setMinimumHeight(need)


class HLine(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("hline")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)


class Chip(QLabel):
    def __init__(self, text: str, kind: str = "default", parent=None):
        super().__init__(text, parent)
        self.setObjectName("chip")
        self.setProperty("kind", kind)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(24)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

    def set_kind(self, kind: str) -> None:
        self.setProperty("kind", kind)
        self.style().unpolish(self)
        self.style().polish(self)


class BrandMark(QWidget):
    """左上角标识：渐变圆角方块 + 「习」字。"""

    def __init__(self, size: int = 40, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        grad = QLinearGradient(r.topLeft(), r.bottomRight())
        grad.setColorAt(0, QColor("#4A6BF0"))
        grad.setColorAt(1, QColor("#7A5BE0"))
        path = QPainterPath()
        path.addRoundedRect(r, 12, 12)
        p.fillPath(path, grad)
        p.setPen(QColor("#FFFFFF"))
        f = theme.base_font(15, 700)
        p.setFont(f)
        p.drawText(r, Qt.AlignCenter, "习")


class ResultIcon(QWidget):
    """作答结果图标：绿色对勾 / 红色叉号，均为绘制，避免字体差异。"""

    def __init__(self, ok: bool, size: int = 30, parent=None):
        super().__init__(parent)
        self.ok = ok
        self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        color = QColor(theme.SUCCESS if self.ok else theme.DANGER)
        p.setBrush(color)
        p.setPen(Qt.NoPen)
        p.drawEllipse(r)
        pen = QPen(QColor("#FFFFFF"), 2.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        w, h = r.width(), r.height()
        x, y = r.left(), r.top()
        if self.ok:
            p.drawPolyline([QPoint(int(x + w * 0.28), int(y + h * 0.53)),
                            QPoint(int(x + w * 0.44), int(y + h * 0.69)),
                            QPoint(int(x + w * 0.73), int(y + h * 0.34))])
        else:
            p.drawLine(QPoint(int(x + w * 0.33), int(y + h * 0.33)),
                       QPoint(int(x + w * 0.67), int(y + h * 0.67)))
            p.drawLine(QPoint(int(x + w * 0.67), int(y + h * 0.33)),
                       QPoint(int(x + w * 0.33), int(y + h * 0.67)))


class RingIndicator(QWidget):
    """正确率环形图。"""

    def __init__(self, diameter: int = 132, parent=None):
        super().__init__(parent)
        self._value = 0.0
        self._text = "0%"
        self._sub = "正确率"
        self.setFixedSize(diameter, diameter)

    def set_value(self, value: float, text: str | None = None, sub: str | None = None) -> None:
        self._value = max(0.0, min(1.0, value))
        self._text = text if text is not None else f"{self._value * 100:.0f}%"
        if sub is not None:
            self._sub = sub
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(9, 9, -9, -9)
        width = 9
        p.setPen(QPen(QColor(theme.RING_TRACK), width, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(rect, 0, 360 * 16)

        if self._value > 0:
            if self._value >= 0.85:
                color = QColor(theme.SUCCESS)
            elif self._value >= 0.6:
                color = QColor(theme.PRIMARY)
            else:
                color = QColor(theme.DANGER)
            p.setPen(QPen(color, width, Qt.SolidLine, Qt.RoundCap))
            p.drawArc(rect, 90 * 16, -int(360 * 16 * self._value))

        p.setPen(QColor(theme.TEXT))
        f = theme.base_font(17, 700)
        p.setFont(f)
        p.drawText(QRectF(rect.left(), rect.center().y() - 24, rect.width(), 30),
                   Qt.AlignHCenter | Qt.AlignVCenter, self._text)
        p.setPen(QColor(theme.MUTED))
        p.setFont(theme.base_font(8))
        p.drawText(QRectF(rect.left(), rect.center().y() + 6, rect.width(), 20),
                   Qt.AlignHCenter | Qt.AlignVCenter, self._sub)


class StatTile(QWidget):
    def __init__(self, name: str, value: str = "0", parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        self.value = QLabel(value)
        self.value.setObjectName("bigNum")
        self.value.setAlignment(Qt.AlignCenter)
        self.name = QLabel(name)
        self.name.setObjectName("tileName")
        self.name.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.value)
        lay.addWidget(self.name)

    def set_value(self, value) -> None:
        self.value.setText(str(value))


# ------------------------------------------------------------------ 分段控件
class Segmented(QFrame):
    changed = Signal(int)

    def __init__(self, labels: list[str], parent=None):
        super().__init__(parent)
        self.setObjectName("segment")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(4)
        self.buttons: list[QPushButton] = []
        for i, text in enumerate(labels):
            btn = QPushButton(text)
            btn.setObjectName("segBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.clicked.connect(lambda _=False, idx=i: self._select(idx))
            lay.addWidget(btn)
            self.buttons.append(btn)
        self.buttons[0].setChecked(True)
        self._index = 0

    def _select(self, index: int) -> None:
        if index == self._index:
            return
        self._index = index
        self.buttons[index].setChecked(True)
        for i, b in enumerate(self.buttons):
            if i != index:
                b.setChecked(False)
        self.changed.emit(index)

    def set_index(self, index: int) -> None:
        """仅同步显示状态，不发出 changed（避免与外部状态互相触发）。"""
        if 0 <= index < len(self.buttons) and index != self._index:
            self._index = index
            for i, b in enumerate(self.buttons):
                b.setChecked(i == index)

    @property
    def index(self) -> int:
        return self._index


# ------------------------------------------------------------------ 下拉选择
class Select(QFrame):
    """轻量下拉选择：白底圆角 + 弹出菜单，支持「全部」。"""

    changed = Signal(object)

    def __init__(self, placeholder: str = "全部", parent=None):
        super().__init__(parent)
        self.setObjectName("select")
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("disabled", "false")
        self._items: list[tuple[object, str]] = [(None, placeholder)]
        self._value: object = None
        self._open = False

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 10, 8)
        lay.setSpacing(8)
        self.value_label = QLabel(placeholder)
        self.value_label.setObjectName("selectValue")
        self.arrow = QLabel("▾")
        self.arrow.setObjectName("selectArrow")
        lay.addWidget(self.value_label, 1)
        lay.addWidget(self.arrow, 0)

    # ---- 数据
    def set_items(self, items: list[tuple[object, str]], keep: bool = True) -> None:
        self._items = items
        values = [v for v, _ in items]
        if not keep or self._value not in values:
            self._value = items[0][0] if items else None
        self._refresh_label()

    def set_value(self, value: object, emit: bool = False) -> None:
        values = [v for v, _ in self._items]
        if value not in values:
            value = values[0] if values else None
        if value == self._value:
            return
        self._value = value
        self._refresh_label()
        if emit:
            self.changed.emit(value)

    @property
    def value(self) -> object:
        return self._value

    def _label_for(self, value: object) -> str:
        for v, label in self._items:
            if v == value:
                return label
        return str(value)

    def _refresh_label(self) -> None:
        self.value_label.setText(self._label_for(self._value))

    # ---- 交互
    def set_disabled(self, disabled: bool) -> None:
        self.setProperty("disabled", "true" if disabled else "false")
        self.value_label.setProperty("disabled", "true" if disabled else "false")
        self.setCursor(Qt.ForbiddenCursor if disabled else Qt.PointingHandCursor)
        for w in (self, self.value_label):
            w.style().unpolish(w)
            w.style().polish(w)

    @property
    def is_disabled(self) -> bool:
        return self.property("disabled") == "true"

    def mousePressEvent(self, event) -> None:
        if self.is_disabled or event.button() != Qt.LeftButton:
            return
        self._popup()

    def _popup(self) -> None:
        if len(self._items) > 18:
            self._popup_search()
            return
        menu = self._build_menu()
        self.setProperty("open", "true")
        self.style().unpolish(self)
        self.style().polish(self)
        menu.exec(self.mapToGlobal(QPoint(0, self.height() + 6)))
        self.setProperty("open", "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def _build_menu(self) -> QMenu:
        """短列表用标准菜单；勾选标记跟随主题调色板。"""
        menu = QMenu(self)
        menu.setAttribute(Qt.WA_DeleteOnClose)
        group = QActionGroup(menu)
        group.setExclusive(True)
        for value, label in self._items:
            act = menu.addAction(label)
            act.setCheckable(True)
            act.setChecked(value == self._value)
            act.triggered.connect(lambda _=False, v=value: self._choose(v))
            group.addAction(act)
        menu.setMinimumWidth(max(self.width(), 200))
        return menu

    def _popup_search(self) -> None:
        popup = SearchPopup(self._items, self._value, self)
        popup.picked.connect(self._choose)
        popup.picked.connect(lambda _=None: popup.close())
        self._popup_ref = popup
        popup.show_at(self.mapToGlobal(QPoint(0, self.height() + 6)))

    def _choose(self, value: object) -> None:
        if value == self._value:
            return
        self._value = value
        self._refresh_label()
        self.changed.emit(value)


# ------------------------------------------------------------------ 选项行
class OptionRow(QFrame):
    clicked = Signal(str)

    def __init__(self, key: str, text: str, parent=None):
        super().__init__(parent)
        self.setObjectName("option")
        self.key = key
        self._base = "idle"
        self._dim = False
        self._hover = False
        self._interactive = True
        self.setCursor(Qt.PointingHandCursor)
        # 开启 heightForWidth，行高才能随选项文字换行而增长（否则会被裁切）
        policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 12, 16, 12)
        lay.setSpacing(12)

        self.badge = QLabel(key)
        self.badge.setObjectName("badge")
        self.badge.setFixedSize(26, 26)
        self.badge.setAlignment(Qt.AlignCenter)
        self.badge.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        self.text = WrapLabel(text)
        self.text.setObjectName("optionText")
        self.text.setTextInteractionFlags(Qt.NoTextInteraction)
        self.text.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        lay.addWidget(self.badge, 0, Qt.AlignTop | Qt.AlignHCenter)
        lay.addWidget(self.text, 1)
        self._apply()

    # ---- 状态
    def _set_qss_property(self, name: str, value: str) -> None:
        self.setProperty(name, value)
        self.badge.setProperty(name, value)
        for w in (self, self.badge):
            w.style().unpolish(w)
            w.style().polish(w)

    def _apply(self) -> None:
        display = "hover" if (self._hover and self._base == "idle") else self._base
        self._set_qss_property("state", display)
        self.text.setProperty("state", "dim" if self._dim else
                             ("readonly" if self._base == "readonly" else ""))
        self.text.style().unpolish(self.text)
        self.text.style().polish(self.text)

    def set_state(self, state: str, dim: bool = False) -> None:
        self._base = state
        self._dim = dim
        self._apply()

    def set_interactive(self, on: bool) -> None:
        self._interactive = on
        self.setCursor(Qt.PointingHandCursor if on else Qt.ArrowCursor)

    @property
    def state(self) -> str:
        return self._base

    # ---- 事件
    def enterEvent(self, event) -> None:
        if self._interactive and self._base == "idle":
            self._hover = True
            self._apply()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover = False
        self._apply()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._interactive and event.button() == Qt.LeftButton \
                and self.rect().contains(event.position().toPoint()):
            self.clicked.emit(self.key)
        super().mouseReleaseEvent(event)




class SearchPopup(QFrame):
    """带搜索框的下拉面板：适合知识点这类长列表。"""

    picked = Signal(object)

    def __init__(self, items: list[tuple[object, str]], current: object, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._items = list(items)
        self.setFixedWidth(max(320, (parent.width() if parent else 320)))

        shell = QVBoxLayout(self)
        shell.setContentsMargins(10, 10, 10, 10)

        card = QFrame()
        card.setObjectName("popupCard")
        card.setFrameShape(QFrame.NoFrame)
        theme.apply_shadow(card, blur=28, dy=8, alpha=45)
        shell.addWidget(card)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        self.search = QLineEdit()
        self.search.setObjectName("popupSearch")
        self.search.setPlaceholderText("输入关键字筛选…")
        self.search.setClearButtonEnabled(True)
        lay.addWidget(self.search)

        self.list = QListWidget()
        self.list.setObjectName("popupList")
        self.list.setUniformItemSizes(True)
        self.list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        lay.addWidget(self.list, 1)

        for value, label in self._items:
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, value)
            self.list.addItem(item)
            if value == current:
                self.list.setCurrentItem(item)

        rows = min(len(self._items), 11)
        self.setFixedHeight(58 + rows * 31 + 28)
        self.search.textChanged.connect(self._filter)
        self.search.returnPressed.connect(self._pick_current)
        self.list.itemClicked.connect(self._pick_item)

    def show_at(self, pos) -> None:
        screen = self.screen().availableGeometry() if self.screen() else None
        y = pos.y()
        if screen and y + self.height() > screen.bottom():
            y = max(screen.top() + 8, pos.y() - self.height() - 44)
        self.move(pos.x(), y)
        self.show()
        self.search.setFocus()

    def _filter(self, text: str) -> None:
        key = text.strip()
        for i in range(self.list.count()):
            item = self.list.item(i)
            item.setHidden(bool(key) and key not in item.text())
        visible = 0
        for i in range(self.list.count()):
            item = self.list.item(i)
            if not item.isHidden():
                if visible == 0:
                    self.list.setCurrentItem(item)
                visible += 1
        rows = min(max(visible, 1), 11)
        self.setFixedHeight(58 + rows * 31 + 28)

    def _pick_current(self) -> None:
        item = self.list.currentItem()
        if item is not None and not item.isHidden():
            self._pick_item(item)

    def _pick_item(self, item: QListWidgetItem) -> None:
        self.picked.emit(item.data(Qt.UserRole))
        self.close()

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key_Down, Qt.Key_Up):
            self.list.setFocus()
            self.list.keyPressEvent(event)
            return
        super().keyPressEvent(event)


# ------------------------------------------------------------------ 其他
class ElidedLabel(QLabel):
    """单行省略文本，随宽度自动截断。"""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self._full = text

    def setText(self, text: str) -> None:  # noqa: N802
        self._full = text
        self.setToolTip(text if len(text) > 26 else "")
        super().setText(text)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        metrics = self.fontMetrics()
        elided = metrics.elidedText(self._full, Qt.ElideRight, self.width())
        painter.setPen(self.palette().color(QPalette.WindowText))
        painter.drawText(self.rect(), int(self.alignment() | Qt.AlignVCenter), elided)


class WrongItem(QFrame):
    clicked = Signal(str)

    def __init__(self, question, parent=None):
        super().__init__(parent)
        self.setObjectName("wrongItem")
        self.question = question
        self.setCursor(Qt.PointingHandCursor)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 7, 10, 7)
        lay.setSpacing(2)
        meta = QLabel(f"{question.chapter.split(' ')[0]} · {question.type_label} · {question.knowledge}")
        meta.setObjectName("wrongMeta")
        stem = ElidedLabel(question.stem)
        stem.setObjectName("wrongStem")
        lay.addWidget(meta)
        lay.addWidget(stem)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.question.id)
        super().mouseReleaseEvent(event)


class ThemeToggle(QAbstractButton):
    """日 / 月图标切换按钮：浅色显示月亮，深色显示太阳，切换时旋转淡入。"""

    def __init__(self, dark: bool = False, parent=None):
        super().__init__(parent)
        self.setFixedSize(38, 38)
        self.setCursor(Qt.PointingHandCursor)
        self._dark = dark
        self._t = 1.0 if dark else 0.0      # 0 = 月亮, 1 = 太阳
        self._hover = False
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(240)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._on_anim)
        self._update_tip()

    # ---- 状态
    def is_dark(self) -> bool:
        return self._dark

    def set_dark(self, dark: bool, animate: bool = True) -> None:
        self._dark = dark
        target = 1.0 if dark else 0.0
        self._update_tip()
        if not animate:
            self._t = target
            self.update()
            return
        self._anim.stop()
        self._anim.setStartValue(self._t)
        self._anim.setEndValue(target)
        self._anim.start()

    def _on_anim(self, value) -> None:
        self._t = float(value)
        self.update()

    def _update_tip(self) -> None:
        self.setToolTip("切换到浅色" if self._dark else "切换到深色")

    # ---- 交互
    def enterEvent(self, event) -> None:
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover = False
        self.update()
        super().leaveEvent(event)

    # ---- 绘制
    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        p.setPen(QPen(QColor(theme.PRIMARY_LINE if self._hover else theme.BORDER), 1))
        p.setBrush(QColor(theme.PRIMARY_SOFT if self._hover else theme.SURFACE_SOFT))
        p.drawRoundedRect(rect, 11, 11)

        cx, cy = rect.center().x(), rect.center().y()
        p.translate(cx, cy)
        p.rotate(-90.0 * self._t)

        moon_alpha = max(0.0, 1.0 - self._t * 1.6)
        sun_alpha = max(0.0, min(1.0, (self._t - 0.35) * 1.6))

        if moon_alpha > 0.01:
            p.setOpacity(moon_alpha)
            disc = QPainterPath()
            disc.addEllipse(QRectF(-6.4, -6.4, 12.8, 12.8))
            bite = QPainterPath()
            bite.addEllipse(QRectF(-2.2, -9.2, 13.0, 13.0))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(theme.TEXT_SECOND))
            p.drawPath(disc.subtracted(bite))

        if sun_alpha > 0.01:
            p.setOpacity(sun_alpha)
            p.setPen(QPen(QColor(theme.SUN), 1.7, Qt.SolidLine, Qt.RoundCap))
            p.setBrush(QColor(theme.SUN))
            p.drawEllipse(QRectF(-3.9, -3.9, 7.8, 7.8))
            for i in range(8):
                p.save()
                p.rotate(i * 45)
                p.drawLine(QPoint(0, -7), QPoint(0, -9))
                p.restore()

        p.setOpacity(1.0)

class EmptyState(QWidget):
    def __init__(self, title: str, text: str = "", parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 40, 24, 40)
        lay.setSpacing(8)
        lay.setAlignment(Qt.AlignCenter)
        mark = QLabel("?")
        mark.setObjectName("emptyMark")
        mark.setAlignment(Qt.AlignCenter)
        mark.setFixedSize(46, 46)
        self.title = QLabel(title)
        self.title.setObjectName("emptyTitle")
        self.title.setAlignment(Qt.AlignCenter)
        self.text = QLabel(text)
        self.text.setObjectName("emptyText")
        self.text.setAlignment(Qt.AlignCenter)
        self.text.setWordWrap(True)
        lay.addWidget(mark, 0, Qt.AlignHCenter)
        lay.addWidget(self.title)
        lay.addWidget(self.text)
