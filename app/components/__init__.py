"""Native, theme-aware presentation components for the approved desktop design."""
from math import ceil
import json

from PySide6.QtCore import QEasingCurve, QRectF, QSize, Qt, QUrl, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QSizePolicy, QSpinBox, QStyle, QStyleOptionSpinBox, QStyledItemDelegate, QTextBrowser, QToolTip, QVBoxLayout, QWidget,
)

from ..theme import DARK, LIGHT, themed_icon
from ..i18n import bind_text, tr
from ..gameplay import BINGO_LABELS, SIZE_LABELS

GROUP_LABELS = {"special": "Đặc biệt", "first": "Giải nhất", "second": "Giải nhì", "third": "Giải ba"}


def tokens_for(widget):
    return getattr(widget.window(), "tokens", LIGHT)


class TextLabel(QLabel):
    def __init__(self, text="", parent=None, *, reserve_wrapped_height=True):
        self._ui_source = text
        self._reserve_wrapped_height = reserve_wrapped_height
        super().__init__(tr(text), parent)

    def setText(self, text):
        self._ui_source = text
        super().setText(tr(text))

    def set_parts(self, *parts):
        self._ui_source = parts
        self.retranslate()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._reserve_wrapped_height and self.wordWrap() and self.width() > 0:
            # Nested bento layouts can otherwise compress wrapped copy below its text height.
            self.setMinimumHeight(self.heightForWidth(self.width()))

    def retranslate(self):
        texts = []
        for source in self._ui_source if isinstance(self._ui_source, tuple) else (self._ui_source,):
            text = tr(source)
            if text == source:
                text = "\n".join(tr(line) for line in source.split("\n"))
            texts.append(text)
        super().setText("".join(texts))


class LocalizedTextBrowser(QTextBrowser):
    """Only translate explicitly owned UI copy; streamed/provider text stays raw."""
    _ui_source = None

    def set_ui_text(self, text):
        self._ui_source = text
        self.retranslate()

    def retranslate(self):
        if self._ui_source is not None:
            position = self.verticalScrollBar().value()
            text = tr(self._ui_source)
            if text == self._ui_source:
                text = "\n".join(tr(line) for line in self._ui_source.split("\n"))
            super().setPlainText(text)
            self.verticalScrollBar().setValue(position)

    def setPlainText(self, text):
        self._ui_source = None
        super().setPlainText(text)

    def clear(self):
        self._ui_source = None
        super().clear()

    def insertPlainText(self, text):
        self._ui_source = None
        super().insertPlainText(text)

    def append(self, text):
        self._ui_source = None
        super().append(text)


def text_label(text, role=None):
    label = TextLabel(text)
    label.setWordWrap(True)
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setMinimumWidth(0)
    if role:
        label.setObjectName(role)
    return label


class BallLabel(QLabel):
    def __init__(self, number, size=42, variant="normal", parent=None):
        super().__init__(f"{number:02}" if isinstance(number, int) else str(number), parent)
        self.variant = variant
        self.setFixedSize(size, size)
        bind_text(self, "setAccessibleName", "Số " + self.text())

    @staticmethod
    def paint_ball(painter, rect, text, tokens, variant="normal"):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(rect).adjusted(1, 1, -1, -1)
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        dark = tokens["bg"] == DARK["bg"]
        if variant == "hit":
            top, middle, bottom = ("#FF7C8D", "#FF4D67", "#F23554") if dark else ("#DB3851", "#C01A36", "#A8122D")
            ink, ring = tokens["on_red"], tokens["red"]
        elif variant == "gold":
            top, middle, bottom, ink, ring = "#FBE8BF", "#EEC77C", "#D39B3F", "#3A2705", "#D39B3F"
        else:
            top, middle, bottom = tokens["ball_top"], tokens["ball_mid"], tokens["ball_end"]
            ink, ring = tokens["fg"], tokens["ball_ring"]
        gradient.setColorAt(0, QColor(top)); gradient.setColorAt(.5, QColor(middle)); gradient.setColorAt(1, QColor(bottom))
        path = QPainterPath(); path.addEllipse(rect)
        painter.fillPath(path, gradient)
        painter.setPen(QPen(QColor(ring), 1)); painter.drawPath(path)
        font = QFont(["Segoe UI Variable Text", "Segoe UI"])
        font.setPixelSize(round(rect.width() * (.37 if rect.width() > 30 else .43)))
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font); painter.setPen(QColor(ink))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(text))
        painter.restore()

    def paintEvent(self, event):
        self.paint_ball(QPainter(self), self.rect(), self.text(), tokens_for(self), self.variant)


class BallStrip(QWidget):
    """Wrap painted balls without adding a minimum width to a bento column."""
    def __init__(self, size=52, parent=None):
        super().__init__(parent)
        self.ball_size, self.values = size, []
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.set_data({})

    def set_data(self, selections):
        self.groups = selections.get("groups", {})
        self.values = [(f"{n:02}" if isinstance(n, int) else str(n), "normal") for n in selections.get("main", [])]
        if "special" in selections:
            self.values.append((f"{selections['special']:02}", "gold"))
        if "groups" in selections:
            self.values = [(str(n), "normal") for group in selections["groups"].values() for n in group]
        bind_text(self, "setAccessibleName", "Kết quả: " + " · ".join(value for value, _ in self.values))
        bind_text(self, "setToolTip", self.property("i18n_setAccessibleName"))
        self.updateGeometry(); self.update()

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        columns = max(1, (width + 7) // (self.ball_size + 7))
        if self.groups:
            return sum(18 + ceil(len(values) / columns) * (self.ball_size + 7) for values in self.groups.values())
        return max(1, ceil(len(self.values) / columns)) * (self.ball_size + 7)

    def sizeHint(self):
        return QSize(250, self.heightForWidth(max(250, self.width())))

    def paintEvent(self, event):
        painter = QPainter(self)
        columns = max(1, (self.width() + 7) // (self.ball_size + 7))
        if self.groups:
            y = 0
            for group, values in self.groups.items():
                painter.setPen(QColor(tokens_for(self)["fg_muted"])); painter.setFont(QFont("Segoe UI", 8))
                painter.drawText(QRectF(0, y, self.width(), 16), tr(GROUP_LABELS.get(group, group)))
                y += 18
                for i, value in enumerate(values):
                    rect = QRectF((i % columns) * (self.ball_size + 7), y + (i // columns) * (self.ball_size + 7), self.ball_size, self.ball_size)
                    BallLabel.paint_ball(painter, rect, value, tokens_for(self), "gold" if group == "special" else "normal")
                y += ceil(len(values) / columns) * (self.ball_size + 7)
            return
        for i, (text, variant) in enumerate(self.values):
            rect = QRectF((i % columns) * (self.ball_size + 7), (i // columns) * (self.ball_size + 7), self.ball_size, self.ball_size)
            BallLabel.paint_ball(painter, rect, text, tokens_for(self), variant)


class TableItemDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        # Selection highlights the row; native cell focus frames break the continuous row.
        option.state &= ~QStyle.StateFlag.State_HasFocus


class BallDelegate(TableItemDelegate):
    """Keep QTableWidgetItem text/API intact while rendering the number column."""
    def __init__(self, parent=None, variant="normal"):
        super().__init__(parent); self.variant = variant

    @staticmethod
    def groups(raw):
        if str(raw).startswith("{"):
            try:
                groups = json.loads(raw)
                if "play" in groups:
                    play = groups["play"]
                    if play == "size":
                        return [(tr(BINGO_LABELS[play]) + " · " + tr(SIZE_LABELS[groups["main"][0]]), [])]
                    if play == "triple":
                        return [(tr(BINGO_LABELS[play]), [(f"{groups['main'][0]:02}", "normal")] * 3)]
                    values = [(tr(SIZE_LABELS.get(n, str(n))), "normal") for n in groups["main"]]
                    return [(tr(BINGO_LABELS.get(play, play)), values)]
                return [(tr(GROUP_LABELS.get(key, key)), [(n, "gold" if key == "special" else "normal") for n in values]) for key, values in groups.items()]
            except (ValueError, AttributeError, TypeError):
                return []
        return []

    @staticmethod
    def row_height(raw, width):
        columns = max(1, (width - 15) // 31)
        groups = BallDelegate.groups(raw)
        if groups:
            return 14 + sum(18 + ceil(len(values) / columns) * 31 for _, values in groups)
        return max(44, ceil(len(raw.replace("| ĐB", "").split()) / columns) * 31 + 14)

    def paint(self, painter, option, index):
        raw = index.data() or ""
        main, _, special = str(raw).partition(" | ĐB ")
        numbers = main.split()
        groups = self.groups(raw)
        if not groups and (not numbers or not all(n.isdigit() for n in numbers)):
            return super().paint(painter, option, index)
        opt = type(option)(option)
        self.initStyleOption(opt, index); opt.text = ""
        widget = option.widget
        widget.style().drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, widget)
        numbers = [(n, self.variant) for n in numbers] + ([(special, "gold")] if special else [])
        size, gap = 26, 5
        columns = max(1, (option.rect.width() - 20 + gap) // (size + gap))
        if groups:
            y = option.rect.y() + 6
            for caption, values in groups:
                painter.save(); painter.setPen(QColor(tokens_for(widget)["fg_muted"])); painter.setFont(QFont("Segoe UI", 8))
                painter.drawText(QRectF(option.rect.x() + 10, y, option.rect.width() - 20, 16), caption); painter.restore()
                y += 18
                for i, (value, variant) in enumerate(values):
                    rect = QRectF(option.rect.x() + 10 + (i % columns) * (size + gap), y + (i // columns) * 31, size, size)
                    BallLabel.paint_ball(painter, rect, value, tokens_for(widget), variant)
                y += ceil(len(values) / columns) * 31
            return
        for i, (number, variant) in enumerate(numbers):
            rect = QRectF(option.rect.x() + 10 + (i % columns) * (size + gap), option.rect.y() + 8 + (i // columns) * (size + 5), size, size)
            BallLabel.paint_ball(painter, rect, number, tokens_for(widget), variant)


class Badge(TextLabel):
    def __init__(self, text, variant="neutral", parent=None):
        super().__init__(text, parent)
        self.setObjectName("badge"); self.setProperty("variant", variant)
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setFixedHeight(22)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

    def set_variant(self, variant):
        self.setProperty("variant", variant)
        self.style().unpolish(self); self.style().polish(self)


class SourceDelegate(TableItemDelegate):
    @staticmethod
    def source_text(value):
        if value == "manual:csv":
            return tr("Nhập CSV")
        url = QUrl(str(value))
        if url.scheme() == "https" and url.host() and not url.userName() and not url.password():
            return tr("Xem nguồn ↗")
        return str(value) or tr("Chưa có nguồn")

    def paint(self, painter, option, index):
        opt = type(option)(option)
        self.initStyleOption(opt, index); opt.text = self.source_text(index.data())
        opt.palette.setColor(opt.palette.ColorRole.Text, QColor(tokens_for(option.widget)["fg_muted"]))
        option.widget.style().drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, option.widget)


class IconLabel(QLabel):
    def __init__(self, name, size=24, tone="red_ink", parent=None):
        super().__init__(parent)
        self.name, self.icon_size, self.tone = name, size, tone
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        tokens = tokens_for(self)
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.icon_size >= 24:
            gradient = QLinearGradient(0, 0, self.width(), self.height())
            gradient.setColorAt(0, QColor(tokens["red_soft"])); gradient.setColorAt(1, QColor(tokens["bg_elevated"]))
            painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(gradient)
            painter.drawRoundedRect(self.rect(), 6, 6)
        themed_icon(self.name, tokens[self.tone], min(16, self.icon_size)).paint(painter, self.rect().adjusted(4, 4, -4, -4) if self.icon_size >= 24 else self.rect())


class SectionCard(QFrame):
    def __init__(self, title="", icon=None, hint="", parent=None):
        super().__init__(parent)
        self.setObjectName("card"); self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.body = QVBoxLayout(self); self.body.setContentsMargins(18, 18, 18, 18); self.body.setSpacing(12)
        self.header = QHBoxLayout(); self.header.setSpacing(10)
        if icon:
            self.header.addWidget(IconLabel(icon))
        self.title = text_label(title, "sectionTitle")
        self.title.setWordWrap(False)
        if title:
            self.header.addWidget(self.title)
        self.header.addStretch()
        self.hint = text_label(hint, "caption")
        if hint:
            self.header.addWidget(self.hint)
        if title or icon:
            self.body.addLayout(self.header)


class StatCard(SectionCard):
    def __init__(self, title, value="—", delta="", parent=None):
        super().__init__(parent=parent)
        self.body.setSpacing(6)
        self.title = text_label(title, "caption"); self.body.addWidget(self.title)
        self.value = text_label(value, "statValue"); self.body.addWidget(self.value)
        self.delta = text_label(delta, "caption"); self.body.addWidget(self.delta)


class Callout(QFrame):
    def __init__(self, text, variant="warn", parent=None):
        super().__init__(parent)
        self.setObjectName("callout"); self.setProperty("variant", variant)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        layout = QHBoxLayout(self); layout.setContentsMargins(12, 10, 12, 10); layout.setSpacing(8)
        layout.addWidget(IconLabel("info" if variant == "info" else "check" if variant == "success" else "warn", 14, "fg_subtle" if variant == "info" else "green" if variant == "success" else "amber"), 0, Qt.AlignmentFlag.AlignTop)
        self.text = text_label(text); layout.addWidget(self.text, 1)


class EmptyState(QWidget):
    def __init__(self, title, description, action, icon="database", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self); layout.setContentsMargins(20, 36, 20, 36); layout.setSpacing(10)
        layout.addWidget(IconLabel(icon, 46, "fg_subtle"), 0, Qt.AlignmentFlag.AlignHCenter)
        heading = text_label(title, "sectionTitle"); heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detail = text_label(description, "subtle"); detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detail.setMaximumWidth(360)
        self.detail = detail
        layout.addWidget(heading); layout.addWidget(detail, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(action, 0, Qt.AlignmentFlag.AlignHCenter)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.detail.setMinimumHeight(self.detail.heightForWidth(self.detail.width()))


class MiniBar(QWidget):
    def __init__(self, value=0, maximum=1, parent=None):
        super().__init__(parent)
        self.value, self.maximum = value, maximum
        self.setFixedHeight(4); self.setMinimumWidth(30)

    def paintEvent(self, event):
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tokens = tokens_for(self)
        painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QColor(tokens["bg_sunken"]))
        painter.drawRoundedRect(self.rect(), 2, 2)
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0, QColor(tokens["cta_top"])); gradient.setColorAt(1, QColor(tokens["cta_end"]))
        painter.setBrush(gradient)
        painter.drawRoundedRect(QRectF(0, 0, self.width() * min(1, max(0, self.value / max(1, self.maximum))), 4), 2, 2)


class NumberHeatmap(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.frequencies = {}
        self.setMinimumWidth(0); self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def set_data(self, frequencies):
        self.frequencies = frequencies
        bind_text(self, "setAccessibleName", "Tần suất: " + ", ".join(f"{n}: {v}" for n, v in frequencies.items()))
        self.updateGeometry(); self.update()

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return int(ceil(len(self.frequencies) / 9) * ((width - 40) / 9 + 5) + 18)

    def sizeHint(self):
        return QSize(360, int(self.heightForWidth(max(200, self.width()))))

    def paintEvent(self, event):
        if not self.frequencies:
            return
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tokens = tokens_for(self); dark = tokens["bg"] == DARK["bg"]
        colors = ("#14141A", "#1F1519", "#3A1820", "#5C1A26", "#8A1B2C", "#C01F35", "#FF3B4E") if dark else ("#FAFAFA", "#F9E8EB", "#F5D2D8", "#EDB0BA", "#E08291", "#D34A61", "#C81E33")
        values = list(self.frequencies.values()); low, high = min(values), max(values)
        mean = sum(values) / len(values); cell = (self.width() - 40) / 9
        for i, (number, count) in enumerate(self.frequencies.items()):
            level = round((count - low) / (high - low) * 6) if high > low else 0
            rect = QRectF((i % 9) * (cell + 5), (i // 9) * (cell + 5), cell, cell)
            painter.setBrush(QColor(colors[level])); painter.setPen(QPen(QColor(tokens["red"]), 1.5) if count >= mean + 2 else QPen(Qt.PenStyle.NoPen))
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 7, 7)
            ink = tokens["on_red"] if level == 6 else "#FFFFFF" if dark and level >= 4 else "#18050B" if level >= 4 else tokens["fg"]
            painter.setPen(QColor(ink)); font = QFont(["Segoe UI Variable Text", "Segoe UI"]); font.setPixelSize(11); font.setWeight(QFont.Weight.DemiBold); painter.setFont(font)
            painter.drawText(rect.adjusted(0, -4, 0, -4), Qt.AlignmentFlag.AlignCenter, f"{number:02}" if isinstance(number, int) else number)
            font.setPixelSize(9); font.setWeight(QFont.Weight.Normal); painter.setFont(font)
            painter.drawText(rect.adjusted(0, 11, 0, 11), Qt.AlignmentFlag.AlignCenter, str(count))
        painter.setPen(QColor(tokens["fg_subtle"]))
        painter.drawText(QRectF(0, ceil(len(values) / 9) * (cell + 5), self.width(), 16), tr("Ít   ░ ▒ ▓ ▰   Nhiều     ·     Viền đỏ: ≥ trung bình + 2 lần"))

    def mouseMoveEvent(self, event):
        cell = (self.width() - 40) / 9 + 5
        i = int(event.position().y() // cell) * 9 + int(event.position().x() // cell)
        entries = list(self.frequencies.items())
        bind_text(self, "setToolTip", f"Số {entries[i][0]} · {entries[i][1]} lần" if 0 <= i < len(entries) else "")


class Histogram(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self.values = []; self.setMinimumHeight(115)

    def set_data(self, values):
        self.values = list(values); self.update()

    def paintEvent(self, event):
        if not self.values:
            return
        low, high = min(self.values), max(self.values); bins = [0] * 10
        for count in self.values:
            bins[min(9, int((count - low) / (high - low + 1) * 10))] += 1
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tokens = tokens_for(self); painter.setPen(Qt.PenStyle.NoPen)
        width = self.width() / 10; height = self.height() - 22
        for i, value in enumerate(bins):
            bar = height * value / max(bins)
            gradient = QLinearGradient(0, height, 0, height - max(1, bar))
            for stop, token in ((0, "red"), (1, "red_bright")):
                color = QColor(tokens[token]); color.setAlpha(180); gradient.setColorAt(stop, color)
            painter.setBrush(gradient)
            painter.drawRoundedRect(QRectF(i * width, height - bar, max(1, width - 4), bar), 3, 3)
        painter.setPen(QColor(tokens["fg_subtle"])); painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(QRectF(0, height + 5, self.width(), 16), Qt.AlignmentFlag.AlignLeft, tr(f"{low} lần"))
        painter.drawText(QRectF(0, height + 5, self.width(), 16), Qt.AlignmentFlag.AlignRight, tr(f"{high} lần"))


class NavigationDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        return QSize(44 if self.parent().collapsed else 210, 38)

    def paint(self, painter, option, index):
        painter.save(); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tokens = tokens_for(option.widget)
        active = bool(option.state & QStyle.StateFlag.State_Selected)
        hover = bool(option.state & QStyle.StateFlag.State_MouseOver)
        rect = QRectF(option.rect).adjusted(0, 1, 0, -1)
        painter.setPen(Qt.PenStyle.NoPen)
        if active or hover:
            if active:
                gradient = QLinearGradient(rect.topLeft(), rect.topRight())
                for stop, token in ((0, "active_top"), (.7, "active_mid"), (1, "active_end")):
                    gradient.setColorAt(stop, QColor(tokens[token]))
                painter.setBrush(gradient)
            else:
                painter.setBrush(QColor(tokens["bg_sunken"]))
            painter.drawRoundedRect(rect, 8, 8)
        if active:
            painter.setBrush(QColor(tokens["red"])); painter.drawRoundedRect(QRectF(rect.x(), rect.y() + 9, 3, 18), 1.5, 1.5)
        color = tokens["red_ink"] if active else tokens["fg_muted"]
        if self.parent().collapsed:
            themed_icon(index.data(Qt.ItemDataRole.UserRole), color, 18).paint(painter, int(rect.center().x() - 9), int(rect.center().y() - 9), 18, 18)
            painter.restore()
            return
        themed_icon(index.data(Qt.ItemDataRole.UserRole), color, 17).paint(painter, int(rect.x()) + 12, int(rect.y()) + 10, 17, 17)
        font = QFont(["Segoe UI Variable Text", "Segoe UI"]); font.setPixelSize(13); font.setWeight(QFont.Weight.DemiBold if active else QFont.Weight.Medium)
        painter.setFont(font); painter.setPen(QColor(color))
        painter.drawText(rect.adjusted(39, 0, -35, 0), Qt.AlignmentFlag.AlignVCenter, index.data())
        badge = index.data(Qt.ItemDataRole.UserRole + 1)
        if badge is not None:
            badge_rect = QRectF(rect.right() - 38, rect.y() + 10, 31, 18)
            painter.setBrush(QColor(tokens["bg_sunken"])); painter.setPen(QPen(QColor(tokens["border"])))
            painter.drawRoundedRect(badge_rect, 8, 8); painter.setFont(QFont("Cascadia Mono", 7))
            painter.setPen(QColor(tokens["fg_subtle"])); painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, str(badge))
        painter.restore()


class SidebarNav(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.collapsed = False
        self.setObjectName("navigation"); self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.setItemDelegate(NavigationDelegate(self))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        for title, icon in (("Tổng quan", "overview"), ("Lịch sử", "history"), ("Thống kê", "stats"), ("Xác suất", "odds"), ("Bộ số tham khảo", "suggest"), ("Kiểm chứng", "verify"), ("AI & cấu hình", "ai"), ("Cài đặt", "settings")):
            item = QListWidgetItem(tr(title)); item.setData(Qt.ItemDataRole.UserRole, icon)
            item.setData(Qt.ItemDataRole.UserRole + 2, title); self.addItem(item)

    def set_count(self, count):
        self.item(1).setData(Qt.ItemDataRole.UserRole + 1, count)
        self.update_tooltips()

    def set_collapsed(self, collapsed):
        self.collapsed = collapsed
        self.update_tooltips()
        self.doItemsLayout(); self.viewport().update()
        QToolTip.hideText()

    def update_tooltips(self):
        for row in range(self.count()):
            item = self.item(row)
            count = item.data(Qt.ItemDataRole.UserRole + 1)
            text = item.text() + (tr(f" · {count} kỳ") if count is not None else "")
            item.setToolTip(text if self.collapsed else "")
            item.setData(Qt.ItemDataRole.AccessibleDescriptionRole, text)

    def show_current_tooltip(self):
        item = self.currentItem()
        if self.collapsed and item:
            rect = self.visualItemRect(item)
            QToolTip.showText(self.viewport().mapToGlobal(rect.topRight()), item.toolTip(), self)

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        self.show_current_tooltip()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.show_current_tooltip()

    def focusOutEvent(self, event):
        QToolTip.hideText()
        super().focusOutEvent(event)


class SegmentedControl(QFrame):
    changed = Signal(int)

    def __init__(self, choices, parent=None):
        super().__init__(parent); self.setObjectName("segmented")
        layout = QHBoxLayout(self); layout.setContentsMargins(3, 3, 3, 3); layout.setSpacing(2)
        self.group = QButtonGroup(self)
        for index, text in enumerate(choices):
            button = QPushButton(tr(text)); button.setObjectName("segment"); button.setCheckable(True)
            button.setProperty("i18n_setText", text)
            self.group.addButton(button, index); layout.addWidget(button)
        self.group.button(0).setChecked(True); self.group.idClicked.connect(self.changed)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

    def setCurrentIndex(self, index):
        self.group.button(index).setChecked(True)


class ThemedComboBox(QComboBox):
    def addItem(self, text, userData=None):
        super().addItem(tr(text), userData)
        self.setItemData(self.count() - 1, text, Qt.ItemDataRole.UserRole + 2)

    def retranslate(self):
        for index in range(self.count()):
            self.setItemText(index, tr(self.itemData(index, Qt.ItemDataRole.UserRole + 2)))

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        themed_icon("chevron-down", tokens_for(self)["fg_subtle"], 13).paint(painter, self.width() - 23, (self.height() - 13) // 2, 13, 13)


class StepperSpinBox(QSpinBox):
    def paintEvent(self, event):
        super().paintEvent(event)
        option = QStyleOptionSpinBox(); self.initStyleOption(option)
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(tokens_for(self)["fg_muted"]), 1.2))
        for control, plus in ((QStyle.SubControl.SC_SpinBoxUp, True), (QStyle.SubControl.SC_SpinBoxDown, False)):
            rect = self.style().subControlRect(QStyle.ComplexControl.CC_SpinBox, option, control, self)
            center = rect.center(); painter.drawLine(center.x() - 3, center.y(), center.x() + 3, center.y())
            if plus:
                painter.drawLine(center.x(), center.y() - 3, center.x(), center.y() + 3)


class NoticeLabel(TextLabel):
    def __init__(self, text, parent=None):
        super().__init__(parent=parent)
        self.setTextFormat(Qt.TextFormat.PlainText); self.setText(text)

    def setText(self, text):
        super().setText(text); self.setToolTip(self.text()); self.setAccessibleName(self.text())

    def retranslate(self):
        super().retranslate(); self.setToolTip(self.text()); self.setAccessibleName(self.text())

    def paintEvent(self, event):
        painter = QPainter(self); painter.setPen(QColor(tokens_for(self)["fg_muted"]))
        painter.setFont(self.font())
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignVCenter, self.fontMetrics().elidedText(self.text(), Qt.TextElideMode.ElideRight, self.width()))


class ThemeToggle(QPushButton):
    def __init__(self, parent=None):
        super().__init__(tr("Sáng / Tối"), parent)
        self.setObjectName("themeToggle"); self.setCheckable(True)
        self.setProperty("i18n_setText", "Sáng / Tối")

    def setText(self, text):
        self.setProperty("i18n_setText", text)
        super().setText(tr(text))

    def retranslate(self):
        super().setText(tr(self.property("i18n_setText")))

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tokens = tokens_for(self)
        track = QRectF(self.width() - 38, (self.height() - 17) / 2, 30, 17)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(tokens["red"] if self.isChecked() else tokens["border_strong"]))
        painter.drawRoundedRect(track, 8.5, 8.5)
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(QRectF(track.x() + (15 if self.isChecked() else 2), track.y() + 2, 13, 13))


class DayNightToggle(ThemeToggle):
    """Native adaptation of the Uiverse.io day/night switch by JkHuger."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dayNightToggle")
        self.setText("")
        self.setFixedSize(44, 34)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._position = 0.0
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.animation.valueChanged.connect(self._move_thumb)
        self.toggled.connect(self._animate)

    def sizeHint(self):
        return QSize(44, 34)

    def minimumSizeHint(self):
        return QSize(44, 34)

    def _move_thumb(self, position):
        self._position = float(position)
        self.update()

    def _animate(self, checked):
        self.animation.stop()
        target = 1.0 if checked else 0.0
        if not self.isVisible():
            self._move_thumb(target)
            return
        self.animation.setStartValue(self._position)
        self.animation.setEndValue(target)
        self.animation.start()

    def paintEvent(self, event):
        QPushButton.paintEvent(self, event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        width, height = 30.0, 17.0
        painter.translate((self.width() - width) / 2, (self.height() - height) / 2)
        painter.scale(width / 100, height / 50)
        if not self.isEnabled():
            painter.setOpacity(0.5)
        position = self._position

        def blend(day, night):
            return QColor.fromRgbF(
                day.redF() + (night.redF() - day.redF()) * position,
                day.greenF() + (night.greenF() - day.greenF()) * position,
                day.blueF() + (night.blueF() - day.blueF()) * position,
            )

        track = blend(QColor.fromHslF(48/360, .9, .85), QColor.fromHslF(198/360, .9, .15))
        thumb = blend(QColor.fromHslF(48/360, .9, .55), QColor.fromHslF(198/360, .9, .55))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track)
        painter.drawRoundedRect(QRectF(0, 0, 100, 50), 25, 25)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(thumb)
        painter.translate(25 + 50 * position, 25)
        painter.drawEllipse(QRectF(-21, -21, 42, 42))
        painter.save()
        painter.setOpacity((1 - position) * (1 if self.isEnabled() else .5))
        painter.rotate(90 * position)
        painter.setBrush(QColor("#FFFFFF"))
        for _ in range(8):
            painter.drawRoundedRect(QRectF(-1, -17 - 4 * position, 2, 5), 1, 1)
            painter.rotate(45)
        painter.restore()
        icon = QPainterPath()
        radius = 6 + 5 * position
        icon.addEllipse(QRectF(-radius, -radius, 2 * radius, 2 * radius))
        cutout = QPainterPath()
        cutout.addEllipse(QRectF(15 - 20 * position, -30 + 11 * position, 23, 23))
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawPath(icon.subtracted(cutout))


class SidebarToggle(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebarToggle"); self.setCheckable(True); self.setFixedSize(32, 32)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)

    def mousePressEvent(self, event):
        # Keep keyboard focus visible without retaining it after a mouse click.
        self.clearFocus()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(tokens_for(self)["fg_muted"]), 1.5))
        box = QRectF((self.width() - 16) / 2, (self.height() - 14) / 2, 16, 14)
        painter.drawRoundedRect(box, 2.5, 2.5)
        painter.drawLine(int(box.x() + 6), int(box.y()), int(box.x() + 6), int(box.bottom()))
