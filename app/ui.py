"""Desktop UI; foreground fetches are manual, optional daily jobs run separately."""
from html import escape
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from random import SystemRandom
import sqlite3
import sys

from PySide6.QtCore import QEasingCurve, QIODevice, QRegularExpression, QSaveFile, QSignalBlocker, Qt, QTime, QTimer, QUrl, QVariantAnimation
from PySide6.QtGui import QDesktopServices, QFont, QIcon, QRegularExpressionValidator, QTextCursor
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFrame, QHBoxLayout, QListWidget,
    QGridLayout, QHeaderView, QLineEdit, QMainWindow, QProgressBar, QPushButton,
    QScrollArea, QStackedWidget, QTableWidget, QTableWidgetItem, QTimeEdit,
    QSizePolicy, QVBoxLayout, QWidget,
)

from . import ai, __version__
from .ai_generation import AI_METHOD, AI_LABEL, build_generation_request, generate_with_ai
from .backtest import run_backtest
from .domain import Ticket
from .generation import METHOD_LABELS, generate, explain_ticket
from .game_guide import show_game_guide
from .model_catalog import fetch_models
from .onboarding import show_onboarding
from .gameplay import BINGO_LABELS, SIZE_LABELS, bingo_choices, sample_selections, ticket_capacity
from .policy import show_policy
from .probability import probabilities
from .rules import BASE, RULES, get_rule
from .settings import CONFIG_PATH, load_settings, save_settings
from .simulation import simulate
from .sources import CancelledError, OfficialSource, import_csv
from .statistics import describe
from .storage import Store, data_directory
from .widgets import label, table
from .theme import ASSETS, LIGHT, apply_theme, themed_icon
from .preferences import default_preferences, load_preferences, save_preferences
from .scheduling import configure_schedules
from .i18n import bind_text, set_language, tr
from .components import (Badge, BallDelegate, BallLabel, BallStrip, Callout, EmptyState, Histogram,
                         IconLabel, LocalizedTextBrowser, MiniBar, NoticeLabel, NumberHeatmap, SectionCard, SegmentedControl,
                         SidebarNav, SidebarToggle, SourceDelegate, StatCard, StepperSpinBox,
                         TextLabel, ThemedComboBox, ThemeToggle)
from .workers import Worker

APP_NAME = "LottoLens"
APP_TITLE = f"{APP_NAME} — V{__version__}"
APP_GITHUB_URL = "https://github.com/TKNguyenn/LottoLens"


def number_text(selections):
    if "play" in selections:
        return json.dumps(selections, ensure_ascii=False)
    main = selections.get("main")
    text = "  ".join(f"{x:02}" if isinstance(x, int) else x for x in main) if main else json.dumps(selections.get("groups", {}), ensure_ascii=False)
    if "special" in selections:
        text += f"  | ĐB {selections['special']:02}"
    return text


def fill(widget, rows):
    widget.setRowCount(len(rows))
    for i, row in enumerate(rows):
        widget.setRowHeight(i, 46)
        for j, value in enumerate(row):
            item = QTableWidgetItem(tr(str(value)))
            item.setToolTip(tr(str(value)))
            item.setData(Qt.ItemDataRole.UserRole + 2, str(value)); widget.setItem(i, j, item)
    widget.resize_ball_rows()


def draw_date(draw):
    return datetime.fromisoformat(draw.draw_at_utc).astimezone(timezone(timedelta(hours=7))).strftime("%d/%m/%Y")


class Desktop(QMainWindow):
    def __init__(self, db_path=None, config_path=CONFIG_PATH):
        super().__init__()
        self.store = Store(db_path)
        self.config_path = Path(config_path)
        self.preferences_path = self.config_path.with_name("ui_preferences.json")
        preferences_error = None
        try:
            self.preferences = load_preferences(self.preferences_path)
        except (ValueError, OSError) as error:
            self.preferences = default_preferences(); preferences_error = str(error)
        set_language(self.preferences["language"])
        self.language = self.preferences["language"]
        self.analysis_window = self.preferences["analysis_window"]
        self.worker = None
        self.closing = False
        self.generated = None
        self.actions = []
        self.ticket_controls = []
        self._play_context = "single"
        self._bingo_sample = bingo_choices()[0]
        self._max_sample = ["007", "123"]
        self.tokens = LIGHT
        self.theme_name = "light"
        self.setWindowTitle(APP_TITLE)
        self.setWindowIcon(QIcon(str(ASSETS / "generated" / "07-ticket-gold.ico")))
        self.resize(1440, 960)
        self.setMinimumSize(1000, 700)
        central = QWidget(); self.setCentralWidget(central)
        root = QHBoxLayout(central); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
        self.sidebar_collapsed = False
        self.sidebar = sidebar = QFrame(); sidebar.setObjectName("sidebar"); sidebar.setFixedWidth(236)
        self.sidebar_animation = QVariantAnimation(self)
        self.sidebar_animation.setDuration(220); self.sidebar_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.sidebar_animation.valueChanged.connect(sidebar.setFixedWidth)
        left = QVBoxLayout(sidebar); left.setContentsMargins(12, 18, 12, 14); left.setSpacing(4)
        self.brand_header = QWidget()
        self.brand_header.setFixedHeight(50)
        brand = QHBoxLayout(self.brand_header); brand.setContentsMargins(6, 0, 6, 18); brand.setSpacing(8)
        self.brand_logo = label(""); self.brand_logo.setPixmap(self.windowIcon().pixmap(32, 32)); self.brand_logo.setFixedSize(32, 32)
        brand.addWidget(self.brand_logo)
        self.brand_text = QWidget()
        brand_text = QVBoxLayout(self.brand_text); brand_text.setContentsMargins(0, 0, 0, 0); brand_text.setSpacing(0)
        # Qt can reflow these labels without retaining a minimum height from the sidebar animation.
        brand_text.addWidget(label(APP_NAME, "brand", reserve_wrapped_height=False))
        brand_text.addWidget(label("Lịch sử & xác suất", "caption", reserve_wrapped_height=False))
        brand.addWidget(self.brand_text, 1)
        self.sidebar_toggle = SidebarToggle()
        bind_text(self.sidebar_toggle, 'setToolTip', 'Thu gọn thanh điều hướng')
        bind_text(self.sidebar_toggle, 'setAccessibleName', 'Thu gọn thanh điều hướng')
        self.sidebar_toggle.clicked.connect(lambda: self.set_sidebar_collapsed(not self.sidebar_collapsed))
        brand.addWidget(self.sidebar_toggle, 0, Qt.AlignmentFlag.AlignHCenter)
        left.addWidget(self.brand_header)
        self.nav = SidebarNav()
        bind_text(self.nav, 'setAccessibleName', 'Điều hướng chính')
        left.addWidget(self.nav, 1)
        self.sidebar_footer = footer = QFrame(); footer.setObjectName("footer")
        foot = QVBoxLayout(footer); foot.setContentsMargins(10, 12, 10, 0); foot.setSpacing(10)
        self.sidebar_notes = [
            label("Dữ liệu lưu tại máy", "subtle", reserve_wrapped_height=False),
            label("SQLite tại máy. Chỉ gửi lịch sử tới nhà cung cấp khi bạn bấm gọi AI.", "caption", reserve_wrapped_height=False),
        ]
        for note in self.sidebar_notes:
            foot.addWidget(note)
        self.theme_button = ThemeToggle()
        self.theme_button.setObjectName("themeToggle"); bind_text(self.theme_button, 'setAccessibleName', 'Đổi giao diện sáng tối')
        self.theme_button.clicked.connect(lambda: self.set_theme("light" if self.theme_name == "dark" else "dark", persist=True))
        foot.addWidget(self.theme_button); left.addWidget(footer)
        root.addWidget(sidebar)
        workspace = QWidget(); workspace.setObjectName("workspace")
        right = QVBoxLayout(workspace); right.setContentsMargins(0, 0, 0, 0); right.setSpacing(0)
        topline = QFrame(); topline.setObjectName("topline"); topline.setFixedHeight(56)
        header = QHBoxLayout(topline); header.setContentsMargins(22, 0, 22, 0); header.setSpacing(8)
        dot = QFrame(); dot.setObjectName("contextDot"); dot.setFixedSize(6, 6); header.addWidget(dot)
        self.context = label("", "sectionTitle"); header.addWidget(self.context)
        self.count_label = label("", "caption"); header.addWidget(self.count_label); header.addStretch()
        self.game = ThemedComboBox()
        for game_id, rule in RULES.items():
            self.game.addItem(rule.name, game_id)
        header.addWidget(self.game)
        self.mode = ThemedComboBox()
        for n in range(1, 11):
            self.mode.addItem(f"Keno chọn {n} số", f"pick{n}")
        self.mode.setCurrentIndex(5)
        header.addWidget(self.mode)
        header.addWidget(self.icon_button("Hướng dẫn trò chơi", "info", lambda: show_game_guide(self, self.rule)))
        self.help_button = self.icon_button("Trợ giúp", "info", lambda: show_onboarding(self))
        header.addWidget(self.help_button)
        right.addWidget(topline)
        self.source_links = label("")
        self.source_links.setOpenExternalLinks(True)
        self.pages = QStackedWidget()
        for builder in (self.overview, self.history, self.statistics, self.odds, self.suggestions, self.verification, self.ai_page, self.settings_page):
            page = QWidget(); page.setObjectName("canvas")
            layout = QVBoxLayout(page); layout.setContentsMargins(22, 20, 22, 26); layout.setSpacing(14)
            layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            builder(layout)
            scroll = QScrollArea(); scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.setFrameShape(QFrame.Shape.NoFrame); scroll.setWidget(page)
            self.pages.addWidget(scroll)
        right.addWidget(self.pages, 1)
        status = QFrame(); status.setObjectName("statusbar"); status.setFixedHeight(34)
        bottom = QHBoxLayout(status); bottom.setContentsMargins(14, 0, 14, 0); bottom.setSpacing(10)
        self.status_text = label("●  Sẵn sàng", "caption"); bottom.addWidget(self.status_text)
        self.progress = QProgressBar(); self.progress.setTextVisible(False); self.progress.setFixedWidth(90)
        self.progress.hide(); bottom.addWidget(self.progress)
        self.cancel_button = QPushButton(tr("Hủy")); self.cancel_button.setFixedHeight(26); self.cancel_button.hide()
        self.cancel_button.setProperty("i18n_setText", "Hủy")
        self.cancel_button.clicked.connect(self.cancel_task); bottom.addWidget(self.cancel_button)
        self.notice = NoticeLabel("Thống kê quá khứ không tự làm tăng xác suất trúng kỳ tiếp theo.")
        self.notice.setTextFormat(Qt.TextFormat.PlainText)
        self.notice.setWordWrap(False); self.notice.setMinimumWidth(0)
        self.notice.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        bottom.addWidget(self.notice, 1); right.addWidget(status); root.addWidget(workspace, 1)
        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex); self.nav.setCurrentRow(0)
        self.game.currentIndexChanged.connect(self.refresh)
        self.mode.currentIndexChanged.connect(self.refresh)
        try:
            config = load_settings(self.config_path)
        except (ValueError, OSError) as error:
            config = ai.AIConfig(); self.notice.setText(f"Chưa đọc được cấu hình: {error}")
        self.base.setText(config.base_url); self.model.setCurrentText(config.model); self.key.setText(config.api_key)
        try:
            theme = json.loads(self.config_path.with_name("theme.json").read_text(encoding="utf-8")).get("theme", "light")
        except (OSError, ValueError, AttributeError):
            theme = "light"
        self.set_theme(theme)
        self.refresh()
        self.history_limit.valueChanged.connect(lambda value: self.draw_limit_inputs[self.rule.game_id].setValue(value))
        self.language_choice.currentIndexChanged.connect(lambda: self.apply_language(self.language_choice.currentData()))
        self.analysis_window_input.valueChanged.connect(self.set_analysis_window)
        self._auto_results = {}
        self.history_poll = QTimer(self); self.history_poll.setInterval(30_000)
        self.history_poll.timeout.connect(self.poll_background_updates); self.history_poll.start()
        if preferences_error:
            self.notice.setText(f"Chưa đọc được cài đặt giao diện: {preferences_error}")
        try:
            with self.config_path.with_name("window_geometry.bin").open("rb") as file:
                self.restoreGeometry(file.read(4096))
        except OSError:
            pass

    def set_sidebar_collapsed(self, collapsed, animate=True):
        self.sidebar_animation.stop()
        self.sidebar_collapsed = bool(collapsed)
        self.nav.set_collapsed(self.sidebar_collapsed)
        self.brand_logo.setVisible(not self.sidebar_collapsed)
        self.brand_text.setVisible(not self.sidebar_collapsed)
        self.brand_header.layout().setContentsMargins(0 if collapsed else 6, 0, 0 if collapsed else 6, 18)
        for note in self.sidebar_notes:
            note.setVisible(not self.sidebar_collapsed)
        self.sidebar_footer.layout().setContentsMargins(0 if collapsed else 10, 12, 0 if collapsed else 10, 0)
        self.theme_button.setText("" if collapsed else "Sáng / Tối")
        bind_text(self.theme_button, 'setToolTip', 'Đổi giao diện sáng / tối' if collapsed else '')
        self.sidebar_toggle.setChecked(self.sidebar_collapsed)
        text = "Mở rộng thanh điều hướng" if collapsed else "Thu gọn thanh điều hướng"
        bind_text(self.sidebar_toggle, 'setToolTip', text); bind_text(self.sidebar_toggle, 'setAccessibleName', text)
        width = 68 if collapsed else 236
        if animate and self.isVisible():
            self.sidebar_animation.setStartValue(self.sidebar.width()); self.sidebar_animation.setEndValue(width)
            self.sidebar_animation.start()
        else:
            self.sidebar.setFixedWidth(width)

    def set_theme(self, name, persist=False):
        self.theme_name = "dark" if name == "dark" else "light"
        self.tokens = apply_theme(self, self.theme_name)
        self.theme_button.setChecked(self.theme_name == "dark")
        for button in self.findChildren(QPushButton):
            icon = button.property("iconName")
            if icon:
                button.setIcon(themed_icon(icon, self.tokens["on_red"] if button.objectName() == "primary" else self.tokens["fg_muted"], 15))
        self.nav.viewport().update()
        self.refresh_source_links()
        if sys.platform == "win32" and QApplication.platformName() == "windows":
            import ctypes
            dark = ctypes.c_int(self.theme_name == "dark")
            ctypes.windll.dwmapi.DwmSetWindowAttribute(int(self.winId()), 20, ctypes.byref(dark), ctypes.sizeof(dark))
        self.update()
        if persist:
            try:
                path = self.config_path.with_name("theme.json")
                path.parent.mkdir(parents=True, exist_ok=True)
                temporary = path.with_suffix(".json.tmp")
                temporary.write_text(json.dumps({"theme": self.theme_name}), encoding="utf-8")
                temporary.replace(path)
            except OSError as error:
                self.notice.setText(f"Đã đổi giao diện; chưa lưu được theme: {error}")

    @property
    def rule(self):
        return get_rule(self.game.currentData(), self.mode.currentData() if self.game.currentData() == "keno" else None)

    def button(self, text, callback, primary=False):
        button = QPushButton(tr(text))
        button.setProperty("i18n_setText", text)
        if primary:
            button.setObjectName("primary")
        button.clicked.connect(lambda: self.guard(callback))
        self.actions.append(button)
        return button

    def icon_button(self, text, icon, callback, primary=False):
        button = self.button(text, callback, primary)
        button.setProperty("iconName", icon)
        button.setIcon(themed_icon(icon, self.tokens["on_red"] if primary else self.tokens["fg_muted"], 15))
        return button

    def guard(self, callback):
        try:
            callback()
        except (ValueError, OSError, sqlite3.Error, CancelledError) as error:
            self.notice.setText(str(error))

    def heading(self, layout, title, subtitle):
        row = QHBoxLayout(); row.setSpacing(14)
        text = QVBoxLayout(); text.setSpacing(3)
        text.addWidget(label(title, "title")); row.description = label(subtitle, "subtle"); text.addWidget(row.description)
        row.addLayout(text, 1); layout.addLayout(row)
        return row

    def grid(self, *stretches):
        widget = QWidget(); grid = QGridLayout(widget); grid.setContentsMargins(0, 0, 0, 0); grid.setSpacing(12)
        for i, stretch in enumerate(stretches):
            grid.setColumnStretch(i, stretch)
        return widget, grid

    def separator(self):
        separator = QFrame(); separator.setObjectName("separator"); separator.setFixedHeight(1)
        return separator

    def empty(self, title, description):
        return EmptyState(title, description, self.icon_button("Cập nhật lịch sử", "refresh", self.sync, True))

    def overview(self, layout):
        head = self.heading(layout, "Tổng quan", "Kiểm tra lịch sử đã lưu trước khi phân tích hoặc tạo bộ số.")
        head.addWidget(self.icon_button("Nhập CSV", "file", self.import_file))
        head.addWidget(self.icon_button("Cập nhật lịch sử", "refresh", self.sync, True))
        self.overview_empty = SectionCard(); self.overview_empty.body.addWidget(self.empty("Chưa có lịch sử", "Tải các kỳ gần nhất từ nguồn Vietlott hoặc nhập CSV có sẵn."))
        layout.addWidget(self.overview_empty)
        self.overview_data, grid = self.grid(165, 100)
        recent = SectionCard("Kỳ quay gần nhất", "spark")
        recent.setProperty("hero", True)
        self.latest = Badge("—", "red"); recent.header.insertWidget(2, self.latest)
        self.latest_date = label("", "caption"); recent.header.addWidget(self.latest_date)
        self.latest_balls = BallStrip(); recent.body.addWidget(self.latest_balls)
        recent.body.addWidget(self.separator())
        metrics, cols = self.grid(1, 1, 2)
        self.overview_metrics = []
        for i, title in enumerate(("Kỳ đã lưu", "Kỳ vọng / số", "Xác suất giải cao nhất")):
            block = QWidget(); box = QVBoxLayout(block); box.setContentsMargins(0, 0, 0, 0); box.setSpacing(6)
            caption = label(title, "caption"); box.addWidget(caption)
            if i == 2:
                self.overview_probability_title = caption
            value = label("—", "statValue" if i < 2 else "metric")
            box.addWidget(value); self.overview_metrics.append(value); cols.addWidget(block, 0, i)
        recent.body.addWidget(metrics); recent.body.addWidget(self.separator())
        line = QHBoxLayout(); line.addWidget(label("Ba kỳ gần nhất", "caption")); line.addStretch()
        more = self.button("Xem tất cả  ›", lambda: self.nav.setCurrentRow(1)); more.setObjectName("quiet")
        line.addWidget(more); recent.body.addLayout(line)
        self.recent_rows = QVBoxLayout(); self.recent_rows.setSpacing(6); recent.body.addLayout(self.recent_rows)
        grid.addWidget(recent, 0, 0)
        self.hot_card = hot = SectionCard("Số xuất hiện nhiều", "stats", "90 kỳ gần nhất")
        self.hot_rows = QVBoxLayout(); self.hot_rows.setSpacing(12); hot.body.addLayout(self.hot_rows)
        hot.body.addStretch()
        hot.body.addWidget(Callout("Tần suất quá khứ không dự báo kỳ tiếp theo. Mọi bộ hợp lệ cùng loại có cùng xác suất.", "info"))
        grid.addWidget(hot, 0, 1); layout.addWidget(self.overview_data)
        metadata, meta_grid = self.grid(1, 1, 1)
        db = SectionCard("Database", "database"); db.body.setContentsMargins(14, 14, 14, 14)
        self.summary = label("", "mono"); db.body.addWidget(self.summary)
        db.body.addWidget(label("Dữ liệu local · không đồng bộ cloud", "caption")); meta_grid.addWidget(db, 0, 0)
        source = SectionCard("Nguồn kết quả", "globe"); source.body.addWidget(label("vietlott.vn", "sectionTitle")); source.body.addWidget(self.source_links); meta_grid.addWidget(source, 0, 1)
        rules = SectionCard("Trạng thái luật", "shield")
        self.rule_version = label("", "mono"); rules.body.addWidget(self.rule_version)
        rules.body.addWidget(Badge("Kỳ cũ chưa xác minh", "amber")); meta_grid.addWidget(rules, 0, 2)
        layout.addWidget(metadata); layout.addStretch()

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())

    def refresh_overview(self):
        self.hot_card.hint.setText(f"{min(self.analysis_window, len(self.draws))} / {self.analysis_window} kỳ gần nhất")
        self.context.setText(self.rule.name)
        self.count_label.setText(f"· {len(self.draws)} kỳ đã lưu")
        self.nav.set_count(len(self.draws))
        self.overview_probability_title.setText("Xác suất vé đang xem" if self.rule.kind != "set" else f"Xác suất trùng {self.rule.selected} số" if self.rule.game_id == "keno" else "Xác suất giải cao nhất")
        self.overview_empty.setVisible(not self.draws); self.overview_data.setVisible(bool(self.draws))
        self.rule_version.setText(self.rule.rule_version)
        self.summary.setText(self.store.path.name); bind_text(self.summary, 'setToolTip', str(self.store.path))
        self.clear_layout(self.recent_rows); self.clear_layout(self.hot_rows)
        if not self.draws:
            return
        last = self.draws[-1]
        self.latest.setText("#" + last.draw_id)
        self.latest_date.setText(draw_date(last))
        self.latest_balls.set_data(last.payload)
        info = describe(self.rule, self.draws[-self.analysis_window:])
        self.overview_metrics[0].setText(str(len(self.draws)))
        self.overview_metrics[1].setText(f"{info['expected_per_number']:.2f}" if "expected_per_number" in info else "—")
        self.overview_metrics[2].setText("—")
        if self.rule.math_ready:
            _, first = self.top_probability()
            self.overview_metrics[2].setText(f"{float(first):.6%}" if self.rule.kind != "set" else f"{first.numerator} / {first.denominator:,}")
        for draw in reversed(self.draws[-4:-1]):
            row = QHBoxLayout(); row.setSpacing(8)
            row.addWidget(label("#" + draw.draw_id, "mono")); row.addWidget(label(draw_date(draw), "caption"))
            row.addStretch(); strip = BallStrip(size=22); strip.set_data(draw.payload); row.addWidget(strip, 1)
            self.recent_rows.addLayout(row)
        maximum = max(info["frequencies"].values(), default=1)
        for number, count in sorted(info["frequencies"].items(), key=lambda item: (-item[1], str(item[0])))[:6]:
            row = QHBoxLayout(); row.setSpacing(9); row.addWidget(BallLabel(number, 26, "hit"))
            row.addWidget(MiniBar(count, maximum), 1); row.addWidget(label(str(count), "caption")); self.hot_rows.addLayout(row)

    def top_probability(self):
        odds = probabilities(self.rule, self.sample_ticket())
        if self.rule.kind != "set":
            return "Trúng ít nhất một giải", 1-odds["Không trúng"]
        tier = {"mega": "Jackpot", "power": "Jackpot 1", "lotto": "Độc Đắc"}.get(self.rule.game_id, f"Trùng {self.rule.selected} số")
        return tier, odds[tier]

    def refresh_source_links(self):
        rule = self.rule
        color = self.tokens["fg_muted"]
        result, rules = tr("Kết quả"), tr("Thể lệ chính thức")
        text = f'<a style="color:{color}" href="{BASE+rule.result_path}">{result} {escape(rule.name)} ↗</a> · <a style="color:{color}" href="{rule.rules_url}">{rules} ↗</a>'
        self.source_links.setText(text); self.ai_sources.setText(text)

    def history(self, layout):
        head = self.heading(layout, "Lịch sử kết quả", "Kết quả chính, số đặc biệt và nguồn được giữ riêng cho từng kỳ.")
        head.addWidget(self.icon_button("Nhập CSV", "file", self.import_file))
        head.addWidget(self.icon_button("Cập nhật lịch sử", "refresh", self.sync, True))
        controls = SectionCard(); controls.body.setContentsMargins(14, 12, 14, 12)
        tools = QHBoxLayout(); tools.setSpacing(10)
        self.history_search = QLineEdit(); bind_text(self.history_search, 'setPlaceholderText', 'Tìm theo mã kỳ hoặc số…')
        bind_text(self.history_search, 'setAccessibleName', 'Tìm lịch sử theo mã kỳ hoặc số')
        tools.addWidget(self.history_search, 1)
        self.history_limit = StepperSpinBox(); self.history_limit.setRange(1, 2000); self.history_limit.setValue(100)
        self.history_limit.setFixedWidth(82); tools.addWidget(label("Số kỳ giữ lại", "caption")); tools.addWidget(self.history_limit)
        self.history_filter = ThemedComboBox()
        for text, value in (("Tất cả", "all"), ("Có số đặc biệt", "special"), ("30 ngày", "recent")):
            self.history_filter.addItem(text, value)
        tools.addWidget(self.history_filter)
        controls.body.addLayout(tools); layout.addWidget(controls)
        self.history_empty = SectionCard(); self.history_empty.body.addWidget(self.empty("Chưa có kỳ nào", "Tải lịch sử hoặc nhập CSV để bắt đầu.")); layout.addWidget(self.history_empty)
        frame = SectionCard(); frame.body.setContentsMargins(0, 0, 0, 0); frame.body.setSpacing(0)
        self.history_table = table(["KỲ", "NGÀY QUAY", "KẾT QUẢ", "NGUỒN"], [], ball_column=2)
        self.history_table.horizontalHeaderItem(1).setToolTip(tr("Ngày tại Việt Nam · UTC+7"))
        self.history_table.horizontalHeaderItem(1).setData(Qt.ItemDataRole.UserRole + 3, "Ngày tại Việt Nam · UTC+7")
        self.history_table.setMinimumHeight(390)
        header = self.history_table.horizontalHeader()
        for column, width in ((0, 88), (1, 132), (3, 120)):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed); self.history_table.setColumnWidth(column, width)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.history_table.setItemDelegateForColumn(3, SourceDelegate(self.history_table))
        self.history_table.cellDoubleClicked.connect(self.open_history_source)
        self.history_table.cellClicked.connect(lambda row, column: self.open_history_source(row, column) if column == 3 else None)
        bind_text(self.history_table, 'setToolTip', 'Bấm Xem nguồn hoặc bấm đúp một kỳ để mở nguồn gốc.')
        frame.body.addWidget(self.history_table)
        self.history_footer = label("", "caption"); self.history_footer.setContentsMargins(14, 10, 14, 10)
        frame.body.addWidget(self.history_footer); self.history_frame = frame; layout.addWidget(frame)
        layout.addWidget(Callout("Bấm Xem nguồn hoặc bấm đúp một kỳ để mở nguồn gốc. Kết quả sửa được lưu thành phiên bản mới, không ghi đè bản cũ.", "info"))
        self.history_search.textChanged.connect(self.filter_history)
        self.history_filter.currentIndexChanged.connect(self.filter_history)
        layout.addStretch()

    def filter_history(self):
        query = self.history_search.text().strip().casefold()
        mode = self.history_filter.currentData(); visible = 0
        for row, draw in enumerate(reversed(self.draws)):
            match = query in (draw.draw_id + " " + number_text(draw.payload)).casefold()
            if mode == "special":
                match = match and "special" in draw.payload
            elif mode == "recent":
                match = match and datetime.fromisoformat(draw.draw_at_utc) >= datetime.now(timezone.utc) - timedelta(days=30)
            self.history_table.setRowHidden(row, not match); visible += bool(match)
        self.history_footer.setText(f"Hiển thị {visible} / {len(self.draws)} kỳ · mới nhất trước")
        self.history_empty.setVisible(not self.draws); self.history_frame.setVisible(bool(self.draws))

    def statistics(self, layout):
        head = self.heading(layout, "Thống kê xuất hiện", "Tần suất, kỳ vọng và khoảng tin cậy 95% (Wilson) từ dữ liệu đã lưu.")
        self.window_size = ThemedComboBox()
        for text, value in (("90 kỳ gần nhất", 90), ("30 kỳ gần nhất", 30), ("Toàn bộ dữ liệu đã lưu", 0)):
            self.window_size.addItem(text, value)
        self.window_size.currentIndexChanged.connect(lambda: self.guard(self.refresh_statistics))
        self.window_size.hide()
        self.stats_segments = SegmentedControl(["90 kỳ", "30 kỳ", "Toàn bộ"])
        self.stats_segments.changed.connect(self.window_size.setCurrentIndex)
        head.addWidget(self.stats_segments)
        self.stats_empty = SectionCard(); self.stats_empty.body.addWidget(self.empty("Chưa có dữ liệu thống kê", "Cần ít nhất một kỳ đã lưu để tính tần suất.")); layout.addWidget(self.stats_empty)
        self.stats_content = QWidget(); content = QVBoxLayout(self.stats_content); content.setContentsMargins(0, 0, 0, 0); content.setSpacing(14)
        metrics, metrics_grid = self.grid(1, 1, 1)
        self.stats_metrics = [StatCard("Kỳ trong mẫu"), StatCard("Kỳ vọng mỗi số"), StatCard("Số nóng (≥ x̄ + 2 lần)")]
        for i, card in enumerate(self.stats_metrics):
            metrics_grid.addWidget(card, 0, i)
        content.addWidget(metrics)
        charts, charts_grid = self.grid(165, 100)
        self.heat_card = SectionCard("Bản đồ nhiệt", "grid")
        self.heatmap = NumberHeatmap(); self.heat_card.body.addWidget(self.heatmap)
        charts_grid.addWidget(self.heat_card, 0, 0)
        distribution = SectionCard("Phân bố tần suất", "stats")
        self.histogram = Histogram(); distribution.body.addWidget(self.histogram)
        distribution.body.addWidget(self.separator())
        self.distribution_detail = label("", "subtle"); distribution.body.addWidget(self.distribution_detail)
        note = Callout("Khoảng cách hiện tại còn bị cắt tại cuối mẫu.")
        self.stats_note = note.text; distribution.body.addWidget(note); distribution.body.addStretch()
        charts_grid.addWidget(distribution, 0, 1); content.addWidget(charts)
        frame = SectionCard(); frame.body.setContentsMargins(0, 0, 0, 0)
        self.stats_table = table(["Số", "Số lần", "Tỷ lệ quan sát", "Kỳ vọng", "Khoảng tin cậy 95%"], [])
        self.stats_table.setItemDelegateForColumn(0, BallDelegate(self.stats_table, "hit"))
        self.stats_table.setMinimumHeight(330); frame.body.addWidget(self.stats_table)
        content.addWidget(frame); layout.addWidget(self.stats_content); layout.addStretch()

    def odds(self, layout):
        self.heading(layout, "Xác suất lý thuyết", "Tính bằng tổ hợp theo luật; không thay đổi theo tần suất lịch sử.")
        self.build_ticket_controls(layout)
        self.odds_content, grid = self.grid(165, 100)
        tiers = SectionCard("Bảng xác suất theo hạng giải", "odds")
        self.odds_table = table(["HẠNG GIẢI", "PHÂN SỐ CHÍNH XÁC", "XÁC SUẤT"], [])
        self.odds_table.setMinimumHeight(300); tiers.body.addWidget(self.odds_table)
        self.ticket_note = label("", "caption"); tiers.body.addWidget(self.ticket_note)
        grid.addWidget(tiers, 0, 0, 2, 1)
        self.jackpot_card = StatCard("Giải cao nhất")
        self.jackpot_card.value.setObjectName("metric"); grid.addWidget(self.jackpot_card, 0, 1)
        assumptions = SectionCard("Giả định", "shield")
        self.odds_note = label("", "subtle"); assumptions.body.addWidget(self.odds_note)
        assumptions.body.addWidget(Callout("Với cùng một vé và cùng luật, xác suất lý thuyết không phụ thuộc phương pháp chọn số."))
        grid.addWidget(assumptions, 1, 1)
        layout.addWidget(self.odds_content)
        self.odds_empty = SectionCard("Chưa bật xác suất", "shield")
        self.odds_empty.body.addWidget(Callout("Cần xác minh đầy đủ bảng trả thưởng và luật trước khi tính. Không dùng công thức trò khác thay thế.", "info"))
        layout.addWidget(self.odds_empty); layout.addStretch()

    def suggestions(self, layout):
        head = self.heading(layout, "Bộ số tham khảo", "Áp dụng tần suất 90 kỳ và xác suất nền để tạo trọng số chọn số.")
        self.suggestion_description = head.description
        self.history_badge = Badge("Cần ≥ 90 kỳ", "amber"); head.addWidget(self.history_badge)
        split, grid = self.grid(1, 0); grid.setColumnMinimumWidth(1, 352)
        frame = SectionCard("Thiết lập sinh số", "suggest")
        body = frame.body
        self.build_ticket_controls(body)
        self.method = ThemedComboBox()
        for method, text in METHOD_LABELS.items():
            self.method.addItem(text, method)
        self.method.addItem(AI_LABEL, AI_METHOD)
        self.method.setMinimumWidth(0); self.method.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.method.setMinimumContentsLength(10)
        self.count = StepperSpinBox(); self.count.setRange(1, 100); self.count.setValue(5)
        self.target = QLineEdit(); bind_text(self.target, 'setPlaceholderText', 'Ví dụ: 01587; để trống nếu chỉ tạo để xem')
        bind_text(self.target, 'setToolTip', 'Mã kỳ quay bạn dự định dùng bộ số, để lưu và đối chiếu sau khi có kết quả.')
        self.method_requirements = self.add_field(body, "Phương pháp", self.method, "Bayes và tần suất cần ít nhất 90 kỳ. Đồng đều dùng được khi chưa có lịch sử.")
        row, fields = self.grid(1, 2)
        count_box = QVBoxLayout(); target_box = QVBoxLayout()
        self.count_hint = self.add_field(count_box, "Số bộ", self.count, "Tối đa 100")
        self.add_field(target_box, "Kỳ dự định chơi", self.target, "Chỉ cần khi bấm Lưu, dùng để đối chiếu sau.")
        fields.addLayout(count_box, 0, 0); fields.addLayout(target_box, 0, 1); body.addWidget(row)
        self.method_note = label("", "subtle"); body.addWidget(self.method_note)
        self.method.currentIndexChanged.connect(self.update_method_note)
        self.update_method_note()
        body.addWidget(self.separator())
        actions = QHBoxLayout(); actions.setSpacing(8)
        actions.addWidget(self.icon_button("Tạo bộ số tham khảo", "spark", self.make_suggestions, True))
        self.save_button = self.icon_button("Lưu bộ số", "save", self.save_generated); actions.addWidget(self.save_button); actions.addStretch(); body.addLayout(actions)
        clear = self.button("Xóa kết quả", self.clear_generated); clear.setObjectName("quiet"); body.addWidget(clear, 0, Qt.AlignmentFlag.AlignLeft)
        body.addStretch()
        self.ai_history_callout = Callout("Chọn AI phân tích sẽ gửi 90 kỳ tới nhà cung cấp và có thể tính phí. Không tự retry khi lỗi.")
        body.addWidget(self.ai_history_callout)
        grid.addWidget(frame, 0, 0)
        results = SectionCard("Bộ số vừa tạo", "layers")
        self.generation_badge = Badge("Chưa tạo"); results.header.addWidget(self.generation_badge)
        self.suggestion_table = table(["BỘ", "SỐ ĐƯỢC CHỌN"], [], ball_column=1)
        self.suggestion_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.suggestion_table.setColumnWidth(0, 40); self.suggestion_table.setMinimumHeight(230)
        results.body.addWidget(self.suggestion_table)
        self.suggestion_placeholder = label("Chọn phương pháp và bấm Tạo để xem bộ số tham khảo.", "subtle")
        results.body.addWidget(self.suggestion_placeholder)
        self.saved_label = label("", "caption"); results.body.addWidget(self.saved_label)
        grid.addWidget(results, 0, 1); layout.addWidget(split)
        lower, lower_grid = self.grid(1, 0); lower_grid.setColumnMinimumWidth(1, 352)
        detail = SectionCard("Giải thích bộ đầu tiên", "info")
        self.explanation = LocalizedTextBrowser(); self.explanation.setMinimumHeight(220); detail.body.addWidget(self.explanation)
        self.explanation.textChanged.connect(self.refresh_generation_view)
        lower_grid.addWidget(detail, 0, 0)
        limits = SectionCard("Giới hạn", "warn")
        limits.body.addWidget(label("Trọng số mô hình không phải xác suất trúng. Xác suất lý thuyết vẫn do app tính độc lập.", "subtle"))
        self.suggestion_odds = label("—", "metric"); limits.body.addWidget(self.suggestion_odds)
        self.suggestion_odds_hint = label("Theo vé đang xem ở phía trên; không phải toàn bộ batch.", "caption")
        limits.body.addWidget(self.suggestion_odds_hint)
        limits.body.addWidget(Callout("Chưa có bằng chứng phương pháp chọn số làm tăng xác suất trúng.", "info")); limits.body.addStretch()
        lower_grid.addWidget(limits, 0, 1); layout.addWidget(lower); layout.addStretch()

    def add_field(self, layout, text, widget, description=""):
        caption = label(text, "subtle"); caption.setBuddy(widget); layout.addWidget(caption)
        bind_text(widget, 'setAccessibleName', text); layout.addWidget(widget)
        if description:
            note = label(description, "caption"); layout.addWidget(note)
            return note

    def clear_generated(self):
        self.generated = None; fill(self.suggestion_table, [])
        self.explanation.set_ui_text("Chọn phương pháp rồi bấm Tạo bộ số tham khảo.")

    def refresh_generation_view(self):
        ready = bool(self.generated and self.suggestion_table.rowCount())
        self.generation_badge.setText(f"{self.suggestion_table.rowCount()} bộ · hợp lệ" if ready else "Chưa tạo")
        self.generation_badge.set_variant("green" if ready else "neutral")
        self.suggestion_table.setVisible(ready); self.suggestion_placeholder.setVisible(not ready)
        self.save_button.setEnabled(ready and self.worker is None)

    def verification(self, layout):
        self.heading(layout, "Kiểm chứng phương pháp", "Mỗi kỳ chỉ dùng lịch sử trước đó, so với 200 lượt chọn ngẫu nhiên.")
        split, grid = self.grid(1, 0); grid.setColumnMinimumWidth(1, 352)
        self.verify_setup = setup = SectionCard("Thiết lập kiểm chứng", "verify", "seed 42 · 5 vé/kỳ")
        self.verify_adjustment = Badge("", "amber"); self.verify_adjustment.hide()
        setup.header.insertWidget(2, self.verify_adjustment)
        self.verify_method = ThemedComboBox()
        for index in range(self.method.count()):
            self.verify_method.addItem(self.method.itemData(index, Qt.ItemDataRole.UserRole + 2), self.method.itemData(index))
        self.verify_method.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.verify_method.setMinimumContentsLength(10)
        self.verify_method.currentIndexChanged.connect(self.method.setCurrentIndex)
        self.method.currentIndexChanged.connect(self.verify_method.setCurrentIndex)
        self.verify_requirements = self.add_field(setup.body, "Phương pháp đưa vào kiểm chứng", self.verify_method, "Cần ít nhất 91 kỳ. Chạy một phương pháp đang chọn; AI chưa hỗ trợ kiểm chứng hàng loạt.")
        setup.body.addWidget(self.separator())
        setup.body.addWidget(label("Mô phỏng bổ sung · 10.000 kỳ", "sectionTitle"))
        setup.body.addWidget(label("Dùng bộ đầu tiên vừa tạo, hoặc vé 1..s nếu chưa tạo. Dữ liệu mô phỏng không lưu vào lịch sử.", "subtle"))
        actions = QHBoxLayout(); actions.setSpacing(8)
        actions.addWidget(self.icon_button("Chạy kiểm chứng", "play", self.backtest, True))
        actions.addWidget(self.icon_button("Chạy mô phỏng", "layers", self.run_simulation))
        actions.addStretch()
        setup.body.addLayout(actions); grid.addWidget(setup, 0, 0)
        latest = SectionCard("Báo cáo hiện tại", "clock")
        self.report_badge = Badge("Chưa chạy"); latest.body.addWidget(self.report_badge)
        self.report_detail = label("Bấm Chạy kiểm chứng hoặc Chạy mô phỏng để bắt đầu.", "subtle")
        latest.body.addWidget(self.report_detail); latest.body.addStretch(); grid.addWidget(latest, 0, 1)
        layout.addWidget(split)
        detail = SectionCard("Chi tiết báo cáo", "file", "JSON · kết quả thực tế")
        self.report = LocalizedTextBrowser(); self.report.setObjectName("report"); self.report.setMinimumHeight(230)
        self.report.textChanged.connect(self.refresh_report_view)
        detail.body.addWidget(self.report)
        detail.body.addWidget(Callout("Báo cáo chưa hoàn tất chỉ chứa phần đã chạy; trạng thái được lấy từ kết quả thực tế.", "info"))
        layout.addWidget(detail); layout.addStretch()

    def refresh_report_view(self):
        try:
            body = json.loads(self.report.toPlainText())
        except (ValueError, TypeError):
            body = {}
        status = body.get("status")
        self.report_badge.setText("Hoàn tất" if status == "completed" else "Chưa hoàn tất" if status == "incomplete" else str(status) if status else "Chưa chạy")
        self.report_badge.set_variant("green" if status == "completed" else "amber" if status else "neutral")
        if body:
            lines = [tr(f"Trạng thái: {status or '—'}")]
            for key, title in (("completed_trials", "Kỳ đã chạy"), ("tested_draws", "Kỳ kiểm chứng"), ("method", "Phương pháp"), ("conclusion", "Kết luận"), ("note", "Ghi chú")):
                if key in body:
                    lines.append(f"{tr(title)}: {tr(str(body[key]))}")
            self.report_detail.setText("\n\n".join(lines))
        else:
            self.report_detail.setText("Bấm Chạy kiểm chứng hoặc Chạy mô phỏng để bắt đầu.")

    def ai_page(self, layout):
        head = self.heading(layout, "AI & cấu hình", "Tìm nguồn trên web và giải thích; dữ liệu kỳ quay được xác minh riêng.")
        head.addWidget(Badge("Thao tác AI có thể tính phí", "amber"))
        split, grid = self.grid(165, 100)
        frame = SectionCard("Nhà cung cấp model", "ai")
        body = frame.body
        body.addWidget(label("Cấu hình lưu rõ trong config.json tại máy.", "caption"))
        body.addWidget(Callout("Hỗ trợ endpoint HTTPS OpenAI-compatible. App tự chọn Responses → Chat Completions → Completions; chỉ chuyển khi endpoint không được hỗ trợ (404/405). Dùng model và API key của nhà cung cấp.", "info"))
        self.base = QLineEdit(); self.model = ThemedComboBox(); self.key = QLineEdit()
        self.model.setEditable(True)
        self.model.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.model.setMaxVisibleItems(12)
        self.model.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.model.setMinimumContentsLength(10)
        self.base.setPlaceholderText(ai.AIConfig().base_url)
        self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.add_field(body, "Base URL", self.base)
        model_header = QHBoxLayout()
        model_label = label("Model", "subtle"); model_label.setBuddy(self.model)
        model_header.addWidget(model_label); model_header.addStretch()
        self.fetch_models_button = self.icon_button("Tải danh sách model", "download", self.load_models)
        model_header.addWidget(self.fetch_models_button); body.addLayout(model_header)
        bind_text(self.model, "setAccessibleName", "Model")
        body.addWidget(self.model)
        body.addWidget(label("Tải danh sách rồi chọn model, hoặc nhập tên thủ công. Danh sách không bảo đảm model hỗ trợ Responses hoặc web search.", "caption"))
        self.base.textChanged.connect(self.clear_model_catalog)
        self.key.textChanged.connect(self.clear_model_catalog)
        key_label = label("API key", "subtle"); key_label.setBuddy(self.key); body.addWidget(key_label)
        key_row = QHBoxLayout(); key_row.setSpacing(6); key_row.addWidget(self.key, 1)
        bind_text(self.key, 'setAccessibleName', 'API key')
        self.reveal_button = self.icon_button("", "eye", self.toggle_key)
        self.reveal_button.setFixedWidth(34); bind_text(self.reveal_button, 'setToolTip', 'Hiện / ẩn API key')
        bind_text(self.reveal_button, 'setAccessibleName', 'Hiện API key'); self.reveal_button.setCheckable(True)
        key_row.addWidget(self.reveal_button); body.addLayout(key_row)
        body.addWidget(label("Lưu rõ, không mã hóa — không đưa config.json vào Git.", "caption"))
        body.addWidget(self.separator())
        actions = QHBoxLayout()
        actions.addWidget(self.icon_button("Lưu cấu hình", "save", self.save_config))
        self.test_button = self.icon_button("Test model", "play", lambda: self.run_ai(test=True), True)
        actions.addWidget(self.test_button); actions.addStretch(); body.addLayout(actions)
        body.addWidget(label("Test model bật streaming và tự chọn endpoint; lần dò có thể thử tối đa 3 endpoint. Không thử lại lỗi key/model/mạng, không kiểm tra web search.", "caption"))
        body.addStretch(); grid.addWidget(frame, 0, 0)
        web = SectionCard("Tìm nguồn trên web", "globe")
        web.setMinimumWidth(310)
        web.body.addWidget(Badge("Web search"))
        self.query = QLineEdit(); bind_text(self.query, 'setPlaceholderText', 'Tìm lịch sử kết quả và thể lệ; bỏ trống để dùng nguồn đang chọn')
        self.add_field(web.body, "Truy vấn", self.query)
        web_actions = QHBoxLayout(); web_actions.setSpacing(6)
        web_actions.addWidget(self.icon_button("Tìm trên web", "search", self.run_ai, True))
        default = self.button("Nguồn mặc định", self.query.clear); default.setObjectName("quiet")
        web_actions.addWidget(default); web_actions.addStretch(); web.body.addLayout(web_actions)
        self.answer = LocalizedTextBrowser(); self.answer.setOpenExternalLinks(True); self.answer.setMinimumHeight(210)
        self.answer.set_ui_text("Phản hồi streaming sẽ xuất hiện ở đây khi bạn bấm Test model hoặc Tìm trên web.")
        web.body.addWidget(self.answer)
        self.ai_sources = label(""); self.ai_sources.setOpenExternalLinks(True); web.body.addWidget(self.ai_sources)
        web.body.addWidget(Callout("Mỗi lần bấm gửi yêu cầu thật và có thể tính phí. Chỉ đổi endpoint khi không được hỗ trợ; không tự thử lại lỗi AI hoặc mạng."))
        grid.addWidget(web, 0, 1); layout.addWidget(split)
        commitments = SectionCard("Cam kết dữ liệu", "shield")
        items, item_grid = self.grid(1, 1, 1)
        for i, (title, text) in enumerate((("Không tự gọi mạng", "App chỉ gửi request khi bạn bấm. Mở app không gọi API."), ("Không ghi số AI vào lịch sử", "Bộ AI chỉ sẵn sàng lưu sau khi phản hồi hoàn tất và được kiểm tra hợp lệ."), ("Key không vào record", "Bộ số đã lưu giữ snapshot và thông tin phương pháp, không giữ API key."))):
            box = QVBoxLayout(); box.setSpacing(6); box.addWidget(label(title, "caption")); box.addWidget(label(text, "subtle")); item_grid.addLayout(box, 0, i)
        commitments.body.addWidget(items); layout.addWidget(commitments); layout.addStretch()

    def toggle_key(self):
        visible = self.key.echoMode() == QLineEdit.EchoMode.Password
        self.key.setEchoMode(QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password)
        icon = "eye-off" if visible else "eye"
        self.reveal_button.setProperty("iconName", icon)
        self.reveal_button.setIcon(themed_icon(icon, self.tokens["fg_muted"], 15))
        bind_text(self.reveal_button, 'setAccessibleName', 'Ẩn API key' if visible else 'Hiện API key')

    def settings_page(self, layout):
        self.heading(layout, "Cài đặt", "Tùy chỉnh ngôn ngữ và số kỳ tải cho từng trò chơi.")
        content, grid = self.grid(1, 1)
        language = SectionCard("Ngôn ngữ & phân tích", "globe")
        self.language_choice = ThemedComboBox()
        self.language_choice.addItem("Tiếng Việt", "vi"); self.language_choice.addItem("English", "en")
        self.language_choice.setCurrentIndex(self.language_choice.findData(self.preferences["language"]))
        self.add_field(language.body, "Ngôn ngữ hiển thị", self.language_choice)
        language.body.addWidget(label("Thay đổi ngôn ngữ có hiệu lực ngay. Bấm Lưu cài đặt để dùng cho lần mở app sau.", "subtle"))
        language.body.addWidget(self.separator())
        self.analysis_window_input = StepperSpinBox(); self.analysis_window_input.setRange(1, 2000)
        self.analysis_window_input.setValue(self.analysis_window)
        self.add_field(language.body, "Số kỳ gần nhất để phân tích", self.analysis_window_input)
        language.body.addWidget(label("Mặc định 90. Dùng cho tổng quan, Bayes, tần suất, AI và warm-up kiểm chứng; không đổi số kỳ tải hoặc xóa dữ liệu.", "subtle"))
        language.body.addWidget(label("Bayes giữ prior tương đương 90 kỳ. AI có giới hạn đầu vào; số kỳ lớn có thể bị từ chối trước khi gửi.", "caption"))
        language.body.addStretch()
        limits = SectionCard("Lịch sử & tự cập nhật", "history")
        limits.body.setAlignment(Qt.AlignmentFlag.AlignTop)
        limits.body.addWidget(label("Giữ tối đa số kỳ mới nhất đã chọn. Cập nhật lấy phần còn thiếu và xóa kỳ cũ ngoài phạm vi sau khi tải hợp lệ; snapshot bộ số/báo cáo được giữ.", "subtle"))
        limits.body.addWidget(label("Lịch hằng ngày dùng giờ Việt Nam (UTC+7), chạy cả khi đóng app; máy cần bật và tài khoản Windows đang đăng nhập. Bật rồi Lưu cài đặt để đăng ký lịch.", "caption"))
        self.draw_limit_inputs = {}
        self.auto_update_inputs = {}; self.auto_time_inputs = {}; self.auto_status_labels = {}
        for game_id, rule in RULES.items():
            row = QHBoxLayout(); row.setSpacing(12)
            name = label(rule.name, "sectionTitle"); row.addWidget(name, 1)
            spin = StepperSpinBox(); spin.setRange(1, 2000); spin.setValue(self.preferences["history_limits"][game_id]); spin.setFixedWidth(100)
            bind_text(spin, 'setAccessibleName', 'Số kỳ giữ lại · {0}'.format(rule.name)); name.setBuddy(spin)
            spin.valueChanged.connect(lambda value, game=game_id: self.history_limit.setValue(value) if self.rule.game_id == game else None)
            row.addWidget(spin); limits.body.addLayout(row); self.draw_limit_inputs[game_id] = spin
            schedule = QHBoxLayout(); schedule.setSpacing(8)
            toggle = ThemeToggle(); toggle.setText("Tự động"); toggle.setFixedWidth(120)
            toggle.setChecked(self.preferences["auto_updates"][game_id]["enabled"])
            bind_text(toggle, "setAccessibleName", f"Tự cập nhật hằng ngày · {rule.name}")
            clock = QTimeEdit(); clock.setDisplayFormat("HH:mm"); clock.setFixedWidth(88)
            clock.setButtonSymbols(QTimeEdit.ButtonSymbols.NoButtons)
            clock.setTime(QTime.fromString(self.preferences["auto_updates"][game_id]["time"], "HH:mm"))
            clock.setEnabled(toggle.isChecked()); bind_text(clock, "setAccessibleName", f"Giờ cập nhật · {rule.name}")
            toggle.toggled.connect(lambda enabled, target=clock: target.setEnabled(enabled and self.worker is None))
            schedule.addWidget(toggle); schedule.addStretch(); caption = label("Giờ", "caption"); caption.setBuddy(clock)
            schedule.addWidget(caption); schedule.addWidget(clock); limits.body.addLayout(schedule)
            self.auto_update_inputs[game_id] = toggle; self.auto_time_inputs[game_id] = clock
            status = label("Chưa có lần tự cập nhật nào.", "caption")
            limits.body.addWidget(status); self.auto_status_labels[game_id] = status
            if game_id != next(reversed(RULES)):
                limits.body.addWidget(self.separator())
        grid.addWidget(limits, 0, 1)
        about = SectionCard("Giới thiệu", "info")
        brand = QHBoxLayout(); brand.setSpacing(12)
        logo = label(""); logo.setPixmap(self.windowIcon().pixmap(42, 42)); logo.setFixedSize(42, 42)
        brand.addWidget(logo); brand.addWidget(label(APP_NAME, "title"), 1); about.body.addLayout(brand)
        about.body.addWidget(label("Xem lịch sử Vietlott, thống kê dữ liệu đã lưu và tạo bộ số tham khảo.", "subtle"))
        about.body.addWidget(label("Dữ liệu lưu tại máy. Lịch sử chỉ cập nhật khi bạn bấm nút hoặc bật lịch hằng ngày. AI chỉ gọi khi bạn bấm và có thể tính phí; thống kê quá khứ không dự báo kỳ tiếp theo.", "subtle"))
        about.body.addWidget(self.separator())
        self.github_button = QPushButton("GitHub")
        self.github_button.setEnabled(bool(APP_GITHUB_URL))
        bind_text(self.github_button, 'setToolTip', 'Chưa có liên kết GitHub. Sẽ bổ sung sau.' if not APP_GITHUB_URL else 'GitHub')
        self.github_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(APP_GITHUB_URL)))
        links = QHBoxLayout()
        links.addWidget(self.icon_button("Chính sách sử dụng", "shield", lambda: show_policy(self)))
        links.addWidget(self.github_button); links.addStretch()
        about.body.addLayout(links)
        left_column = QWidget(); left_stack = QVBoxLayout(left_column)
        left_stack.setContentsMargins(0, 0, 0, 0); left_stack.setSpacing(12)
        left_stack.addWidget(language); left_stack.addWidget(about); left_stack.addStretch()
        grid.addWidget(left_column, 0, 0); layout.addWidget(content)
        row = QHBoxLayout(); row.addWidget(label("Bấm Lưu cài đặt để áp dụng lịch tự động và ghi nhớ các lựa chọn. Chỉ thu gọn lịch sử sau một lần cập nhật hợp lệ.", "caption"), 1)
        self.preferences_save_button = self.icon_button("Lưu cài đặt", "save", self.save_interface_preferences, True)
        row.addWidget(self.preferences_save_button); layout.addLayout(row); layout.addStretch()

    def save_interface_preferences(self):
        body = {"language": self.language_choice.currentData(), "history_limits": {game: spin.value() for game, spin in self.draw_limit_inputs.items()}, "analysis_window": self.analysis_window,
                "auto_updates": {game: {"enabled": toggle.isChecked(), "time": self.auto_time_inputs[game].time().toString("HH:mm")} for game, toggle in self.auto_update_inputs.items()}}
        undo = None
        if body["auto_updates"] != self.preferences["auto_updates"] or any(value["enabled"] for value in body["auto_updates"].values()):
            try:
                undo = configure_schedules(body, self.store.path, self.preferences_path, self.preferences)
            except RuntimeError as error:
                raise ValueError(f"Không thể lưu lịch Windows: {error}") from error
        try:
            save_preferences(self.preferences_path, body)
        except (OSError, ValueError):
            if undo is not None:
                try:
                    undo()
                except RuntimeError as error:
                    raise ValueError("Không lưu được cài đặt và chưa khôi phục đủ lịch Windows; hãy lưu lại để sửa lịch.") from error
            raise
        self.preferences = body
        self.notice.setText("Đã lưu cài đặt giao diện.")

    def apply_language(self, language):
        if language == self.language:
            return
        self.language = language
        set_language(language)
        self.setWindowTitle(APP_TITLE)
        for widget in self.findChildren(QWidget):
            blocker = QSignalBlocker(widget)
            if widget is self.model:
                pass  # Provider model IDs and the user's typed value are data, not display copy.
            elif isinstance(widget, (TextLabel, ThemedComboBox, ThemeToggle, LocalizedTextBrowser)):
                widget.retranslate()
            elif isinstance(widget, QPushButton) and widget.property("i18n_setText") is not None:
                widget.setText(tr(widget.property("i18n_setText")))
            elif isinstance(widget, QListWidget):
                for index in range(widget.count()):
                    item = widget.item(index)
                    source = item.data(Qt.ItemDataRole.UserRole + 2)
                    if source is not None:
                        item.setText(tr(source))
            elif isinstance(widget, QTableWidget):
                for column in range(widget.columnCount()):
                    header = widget.horizontalHeaderItem(column)
                    if header:
                        header.setText(tr(header.data(Qt.ItemDataRole.UserRole + 2)))
                        tooltip = header.data(Qt.ItemDataRole.UserRole + 3)
                        if tooltip:
                            header.setToolTip(tr(tooltip))
            for setter in ("setToolTip", "setAccessibleName", "setAccessibleDescription", "setPlaceholderText"):
                source = widget.property("i18n_" + setter)
                if source is not None:
                    getattr(widget, setter)(tr(source))
            widget.update()
            del blocker
        for table in (self.odds_table, self.stats_table):
            for row in range(table.rowCount()):
                for column in range(table.columnCount()):
                    item = table.item(row, column)
                    if item:
                        item.setText(tr(item.data(Qt.ItemDataRole.UserRole + 2)))
        self.nav.update_tooltips(); self.refresh_source_links()
        self.render_statistics_summary(*self.stats_presentation)
        self.refresh_report_view()
        self.refresh_odds()
        self.nav.doItemsLayout(); self.nav.viewport().update()

    def play_context(self):
        return self._play_context if self.rule.kind == "dice" else None

    def build_ticket_controls(self, layout):
        box = QFrame(); box.setObjectName("fieldPanel")
        grid = QGridLayout(box); grid.setContentsMargins(0, 0, 0, 0); grid.setSpacing(8)
        play = ThemedComboBox(); choice = ThemedComboBox()
        for key, text in BINGO_LABELS.items():
            play.addItem(text, key)
        first, second = QLineEdit("007"), QLineEdit("123")
        for field in (first, second):
            field.setMaxLength(3)
            field.setValidator(QRegularExpressionValidator(QRegularExpression("[0-9]{3}"), field))
            field.setMinimumWidth(0)
            bind_text(field, "setToolTip", "Giữ đủ ba chữ số, kể cả số 0 đầu.")
        labels = [label(text, "caption") for text in ("Cách chơi", "Vé đang xem xác suất", "Bộ 1", "Bộ 2")]
        for column, (caption, field) in enumerate(zip(labels, (play, choice, first, second))):
            grid.addWidget(caption, 0, column); grid.addWidget(field, 1, column); grid.setColumnStretch(column, 1)
            caption.setBuddy(field)
        item = {"box": box, "play": play, "choice": choice, "first": first, "second": second, "labels": labels}
        self.ticket_controls.append(item)
        self.actions.extend((play, choice, first, second))
        play.currentIndexChanged.connect(lambda: self.change_play(play.currentData()))
        choice.currentIndexChanged.connect(lambda: self.change_sample(choice.currentData()))
        for field in (first, second):
            field.editingFinished.connect(lambda: self.guard(lambda: self.change_max_sample(first.text(), second.text())))
        layout.addWidget(box)

    def change_play(self, context):
        self._play_context = context
        self._bingo_sample = bingo_choices(context)[0]
        self.update_ticket_controls(); self.refresh_odds(); self.refresh_overview()

    def change_sample(self, selection):
        if selection is not None:
            self._bingo_sample = selection
            self.update_ticket_controls(); self.refresh_odds(); self.refresh_overview()

    def change_max_sample(self, first, second):
        if any(len(value) != 3 or not value.isascii() or not value.isdigit() for value in (first, second)):
            raise ValueError("Cần bộ ba chữ số đúng định dạng.")
        self._max_sample = [first, second]
        self.update_ticket_controls(); self.refresh_odds(); self.refresh_overview()

    def update_ticket_controls(self):
        rule = self.rule
        for controls in self.ticket_controls:
            controls["box"].setVisible(rule.kind != "set")
            fields = (controls["play"], controls["choice"], controls["first"], controls["second"])
            blockers = [QSignalBlocker(field) for field in fields]
            controls["play"].setCurrentIndex(controls["play"].findData(self._play_context))
            choice = controls["choice"]; choice.clear()
            for selection in bingo_choices(self._play_context):
                value = selection["main"][0] if selection["main"] else None
                text = SIZE_LABELS[value] if selection["play"] == "size" else "Ba số bất kỳ" if value is None else f"{value:02}"
                choice.addItem(text, selection)
            choice.setCurrentIndex(choice.findData(self._bingo_sample))
            controls["first"].setText(self._max_sample[0]); controls["second"].setText(self._max_sample[1])
            for index, field in enumerate(fields):
                visible = rule.kind == "dice" if index < 2 else rule.kind == "triples" and (index == 2 or rule.selected == 2)
                field.setVisible(visible); controls["labels"][index].setVisible(visible)
                controls["box"].layout().setColumnStretch(index, 1 if visible else 0)
            del blockers
        self.count.setMaximum(min(100, ticket_capacity(rule, self.play_context())))
        self.count_hint.setText(f"Tối đa {self.count.maximum()} bộ khác nhau")

    def refresh_odds(self):
        rule = self.rule
        try:
            ticket = self.sample_ticket()
            odds = probabilities(rule, ticket)
            fill(self.odds_table, [[name, f"{p.numerator}/{p.denominator:,}", f"{float(p):.8%}"] for name, p in odds.items()])
            self.odds_table.setMinimumHeight(max(300,46*(len(odds)+1)+8) if rule.kind != "set" else 300)
            if rule.kind == "triples":
                note = "Quay công bằng, độc lập, có hoàn lại. Các hạng giải có thể chồng lấp; không cộng các hàng. Dòng trúng ít nhất một giải đã tính hợp sự kiện. Không suy ra tiền thưởng."
            elif rule.kind == "dice":
                note = "Ba lần quay công bằng, độc lập: 216 kết quả có thứ tự. Xác suất phụ thuộc đúng cách chơi và lựa chọn, không phụ thuộc tần suất lịch sử."
            else:
                note = "Giả định quay công bằng và các kỳ độc lập. Keno hiển thị phân phối số trùng, chưa phải bảng trả thưởng." if rule.game_id == "keno" else "Giả định quay công bằng và các kỳ độc lập. Mọi bộ số hợp lệ cùng loại vé có xác suất lý thuyết như nhau."
            self.odds_note.setText(note)
            tier, probability = self.top_probability()
            self.jackpot_card.title.setText(tier)
            self.jackpot_card.value.setText(f"{float(probability):.6%}" if rule.kind != "set" else f"{probability.numerator} / {probability.denominator:,}")
            self.jackpot_card.delta.setText(f"{float(probability):.8%} mỗi vé · {rule.name}")
            if rule.kind == "dice":
                value = ticket.selections["main"][0] if ticket.selections["main"] else ""
                self.ticket_note.set_parts("Vé đang xem: ", BINGO_LABELS[ticket.selections["play"]], " · ", SIZE_LABELS.get(value, str(value)), " · 10.000đ")
            else:
                self.ticket_note.setText(f"Vé đang xem: {' / '.join(ticket.selections['main'])} · 10.000đ" if rule.kind == "triples" else f"Vé mẫu: 1..{rule.selected} · {rule.price_vnd:,}đ / vé")
            if rule.kind != "set":
                self.suggestion_odds.set_parts(f"{float(probability):.6%}\n", "Trúng ít nhất một giải")
            else:
                self.suggestion_odds.set_parts(f"{probability.numerator} / {probability.denominator:,}\n", tier, f" · {rule.name}")
        except ValueError as error:
            fill(self.odds_table, []); self.odds_note.setText(str(error)); self.suggestion_odds.setText("Chưa bật xác suất")
        self.odds_content.setVisible(rule.math_ready); self.odds_empty.setVisible(not rule.math_ready)
        self.suggestion_odds_hint.setVisible(rule.kind != "set")

    def update_analysis_copy(self):
        window = self.analysis_window
        self.suggestion_description.setText(f"Áp dụng tần suất {window} kỳ và xác suất nền để tạo trọng số chọn số.")
        self.method_requirements.setText(f"Bayes và tần suất cần ít nhất {window} kỳ. Đồng đều dùng được khi chưa có lịch sử.")
        self.ai_history_callout.text.setText(f"Chọn AI phân tích sẽ gửi {window} kỳ tới nhà cung cấp và có thể tính phí. Không tự retry khi lỗi.")
        for combo, method_window in ((self.method, window), (self.verify_method, self.backtest_history_window)):
            labels = {"bayes90_v1": f"Xác suất–thống kê {method_window} kỳ (Bayes)", "frequency90_laplace1_v1": f"Tần suất {method_window} kỳ", AI_METHOD: f"AI phân tích lịch sử ({method_window} kỳ)"}
            for method, text in labels.items():
                index = combo.findData(method)
                combo.setItemData(index, text, Qt.ItemDataRole.UserRole + 2); combo.setItemText(index, tr(text))
        effective = self.backtest_history_window
        adjusted = len(self.draws) >= 2 and effective < window
        insufficient = len(self.draws) < 2
        self.verify_adjustment.setVisible(adjusted or insufficient)
        self.verify_setup.hint.setVisible(not (adjusted or insufficient))
        self.verify_adjustment.setText("Chưa đủ dữ liệu" if insufficient else f"{window} → {effective} kỳ")
        if insufficient:
            requirements = "Cần ít nhất 2 kỳ đã lưu: một kỳ làm lịch sử và một kỳ đối chiếu. AI chưa hỗ trợ kiểm chứng hàng loạt."
        elif adjusted:
            requirements = f"Đặt {window} kỳ; kiểm chứng tự dùng {effective} kỳ để dành {len(self.draws) - effective} kỳ đối chiếu. Cài đặt chung giữ nguyên. AI chưa hỗ trợ kiểm chứng hàng loạt."
        else:
            requirements = f"Cần ít nhất {effective + 1} kỳ. Chạy một phương pháp đang chọn; AI chưa hỗ trợ kiểm chứng hàng loạt."
        self.verify_requirements.setText(requirements)
        bind_text(self.verify_adjustment, "setToolTip", requirements)
        text = f"{window} kỳ gần nhất"
        self.window_size.setItemData(0, window)
        self.window_size.setItemData(0, text, Qt.ItemDataRole.UserRole + 2); self.window_size.setItemText(0, tr(text))
        button = self.stats_segments.group.button(0)
        button.setProperty("i18n_setText", f"{window} kỳ"); button.setText(tr(f"{window} kỳ"))
        self.history_badge.setText(f"Đủ {window} kỳ" if len(self.draws) >= window else f"{len(self.draws)} / {window} kỳ")
        self.history_badge.set_variant("green" if len(self.draws) >= window else "amber")
        self.update_method_note()

    def set_analysis_window(self, window):
        if type(window) is not int or not 1 <= window <= 2000:
            raise ValueError("Số kỳ phân tích phải là số nguyên từ 1 đến 2000.")
        self.analysis_window = window
        self.update_analysis_copy(); self.refresh_overview(); self.refresh_statistics()
        if self.generated is None and self.explanation._ui_source is not None:
            self.explanation.set_ui_text(self.generation_help())
        self.notice.setText(f"Đã chọn {window} kỳ phân tích cho lần tạo/kiểm chứng tiếp theo. Bộ số đang xem giữ nguyên; bấm Lưu cài đặt để ghi nhớ.")

    @property
    def backtest_history_window(self):
        return min(self.analysis_window, max(1, len(self.draws) - 1))

    def generation_help(self):
        return f"Chọn phương pháp rồi bấm Tạo bộ số tham khảo. Bayes và tần suất tính tại máy; AI phân tích {self.analysis_window} kỳ bằng model đã cấu hình. Chưa có bằng chứng các cách chọn này tăng xác suất trúng."

    def refresh(self):
        rule = self.rule
        self.history_limit.setValue(self.draw_limit_inputs[rule.game_id].value())
        self.mode.setVisible(rule.game_id == "keno")
        self.draws = self.store.list_draws(rule)
        self.generated = None
        self.report.clear()
        fill(self.suggestion_table, [])
        self.explanation.set_ui_text(self.generation_help())
        self.refresh_source_links()
        self.count_label.setText(f"{rule.name} • {len(self.draws)} kỳ đã lưu")
        self.latest.setText(f"Kỳ #{self.draws[-1].draw_id}\n{number_text(self.draws[-1].payload)}" if self.draws else "Chưa có lịch sử. Bấm Cập nhật lịch sử để bắt đầu.")
        self.summary.setText(f"{len(self.draws)} kỳ đã lưu. Phạm vi đầy đủ chưa được xác nhận.\nDatabase: {self.store.path}")
        fill(self.history_table, [[d.draw_id, draw_date(d), number_text(d.payload), d.source_url] for d in reversed(self.draws)])
        self.filter_history()
        self.saved_label.setText(f"Đã lưu {len(self.store.suggestions(rule))} bộ cho trò/biến thể này.")
        self.update_analysis_copy()
        self.refresh_statistics()
        self.update_ticket_controls()
        self.refresh_odds()
        self.update_auto_status(self.store.auto_update_runs())
        self.refresh_overview()

    def refresh_statistics(self):
        size = self.window_size.currentData()
        history = self.draws[-size:] if size else self.draws
        info = describe(self.rule, history)
        rows = []
        for n, count in sorted(info["frequencies"].items()):
            interval = info.get("wilson95", {}).get(n)
            observed = (f"{count/len(history):.2%}" if self.rule.kind == "set" else f"{count/len(history):.2f} lần/kỳ") if history else "—"
            rows.append([n, count, observed,
                         f"{info['expected_per_number']:.2f}" if "expected_per_number" in info else "—",
                         f"{interval[0]:.2%} – {interval[1]:.2%}" if interval else "—"])
        fill(self.stats_table, rows)
        self.stats_segments.setCurrentIndex(self.window_size.currentIndex())
        self.stats_empty.setVisible(not history); self.stats_content.setVisible(bool(history))
        self.heatmap.set_data(info["frequencies"])
        self.heat_card.title.setText(f"Bản đồ nhiệt {len(info['frequencies'])} số")
        self.histogram.set_data(info["frequencies"].values())
        self.stats_presentation = (info, len(history), size)
        self.render_statistics_summary(*self.stats_presentation)

    def render_statistics_summary(self, info, history_count, size):
        note = tr(info["note"])
        self.stats_note.setText(f"{history_count} kỳ thực tế trong phạm vi chọn. {note}")
        values = list(info["frequencies"].values())
        mean = sum(values) / len(values) if values else 0
        hot = sorted(((n, v) for n, v in info["frequencies"].items() if v >= mean + 2), key=lambda item: -item[1])[:3]
        self.stats_metrics[0].value.setText(str(history_count))
        self.stats_metrics[0].delta.setText(f"phạm vi: {size} kỳ gần nhất" if size else "phạm vi: toàn bộ đã lưu")
        expected = info.get("expected_per_number")
        self.stats_metrics[1].value.setText(f"{expected:.2f}" if expected is not None else "—")
        self.stats_metrics[1].delta.setText(f"quan sát: {mean:.2f} lần/số")
        self.stats_metrics[2].value.setText(" · ".join(f"{n:02}" if isinstance(n, int) else n for n, _ in hot) or "—")
        self.stats_metrics[2].delta.setText("Lệch trên trung bình ≥ 2 lần; không dự báo")
        expectation = tr(f"{expected:.2f} lần/số") if expected is not None else tr("chưa có mức nền")
        interval = "Wilson 95%" if info.get("wilson95") else tr("Chưa áp dụng")
        self.distribution_detail.setText(f"Trung bình quan sát: {mean:.2f} lần/số\nKỳ vọng lý thuyết: {expectation}\nKhoảng tin cậy: {interval}")

    def sample_ticket(self):
        choices = self._bingo_sample if self.rule.kind == "dice" else {"main": self._max_sample[:self.rule.selected]} if self.rule.kind == "triples" else sample_selections(self.rule)
        return Ticket(self.rule.game_id, self.rule.mode_id, self.rule.rule_version, choices, cost_vnd=self.rule.price_vnd)

    def make_suggestions(self):
        try:
            rule, method = self.rule, self.method.currentData()
            self.generated = None
            fill(self.suggestion_table, []); self.explanation.clear()
            if method == AI_METHOD:
                self.make_ai_suggestions()
                return
            window = self.analysis_window
            context = self.play_context()
            tickets = generate(rule, self.draws, self.count.value(), method, SystemRandom(), history_window=window, play_context=context)
            detail = explain_ticket(rule, self.draws, tickets[0], method, history_window=window, play_context=context)
            snapshot = self.store.snapshot(rule, self.draws)
            metadata = {"history_window": window, "history_used": detail["history_used"], "prior_equivalent_draws": detail["prior_equivalent_draws"]}
            if rule.kind != "set":
                metadata.update(play_context=context, observation_unit=detail["observation_unit"])
            self.generated = (rule, method, tickets, snapshot, metadata)
            fill(self.suggestion_table, [[i+1, number_text(t.selections)] for i, t in enumerate(tickets)])
            lines = [self.method.itemData(self.method.currentIndex(), Qt.ItemDataRole.UserRole + 2), f"Dùng {detail['history_used']} kỳ; kết thúc tại #{detail['cutoff_draw_id']}.", detail["formula"], "", "Chi tiết bộ đầu tiên:"]
            for row in detail["selected_number_stats"]:
                value = f"{row['number']:02}" if isinstance(row["number"], int) else row["number"]
                lines.append(f"Số {value}: {row['count']} lần; mức nền {row['fair_rate']:.2%}; trọng số mô hình {row['model_rate']:.2%}.")
            if "special_stats" in detail:
                s = detail["special_stats"]
                lines.append(f"Số đặc biệt {s['number']:02}: {s['count']} lần; trọng số {s['model_rate']:.2%}.")
            if "jackpot_probability" in detail:
                p = detail["jackpot_probability"]
                lines.append(f"Xác suất giải cao nhất của một bộ: {p['numerator']}/{p['denominator']:,}.")
            if "win_probability" in detail:
                p = detail["win_probability"]
                lines.append(f"Xác suất trúng ít nhất một giải của bộ đầu tiên: {p['numerator']}/{p['denominator']:,}.")
            lines.extend(["", detail["note"], "Chưa có bằng chứng cách chọn này làm tăng xác suất trúng."])
            self.explanation.set_ui_text("\n".join(lines))
            self.notice.setText(f"Đã tạo {len(tickets)} bộ tham khảo. Điền kỳ dự định chơi rồi bấm Lưu nếu muốn đối chiếu sau.")
        except ValueError as error:
            hint = "" if self.method.currentData() == AI_METHOD else (" Hãy cập nhật lịch sử hoặc chọn ngẫu nhiên đồng đều." if self.rule.kind == "set" else " Hiện có thể xem lịch sử và thống kê.")
            self.notice.set_parts(str(error), hint)

    def update_method_note(self):
        window = self.analysis_window
        self.method_note.setText(f"AI nhận {window} kỳ đã lưu, dùng model ở AI & cấu hình với mức suy luận High. Bấm tạo sẽ gửi dữ liệu tới nhà cung cấp và có thể tính phí; không dùng web search." if self.method.currentData() == AI_METHOD else f"Tính tại máy, không gọi AI. Phương pháp Bayes và tần suất cần ít nhất {window} kỳ.")

    def make_ai_suggestions(self):
        rule, history, count, config = self.rule, list(self.draws), self.count.value(), self.current_config()
        window = self.analysis_window
        context = self.play_context()
        build_generation_request(config, rule, history, count, history_window=window, play_context=context)
        snapshot = self.store.snapshot(rule, history)
        self.explanation.set_ui_text("Đang nhận phân tích AI; chỉ dùng bộ số sau khi phản hồi hoàn tất và kiểm tra hợp lệ.\n\n")
        def task(cancel, progress, delta):
            return generate_with_ai(config, rule, history, count, cancel=cancel, on_delta=delta, history_window=window, play_context=context)
        def complete(result):
            tickets, metadata = result["tickets"], result["metadata"]
            self.generated = (rule, AI_METHOD, tickets, snapshot, metadata)
            fill(self.suggestion_table, [[i+1, number_text(ticket.selections)] for i, ticket in enumerate(tickets)])
            lines = [tr(f"AI phân tích lịch sử ({window} kỳ)"), tr(f"Model yêu cầu: {metadata['requested_model']}"),
                     tr(f"Mức suy luận yêu cầu: {metadata['reasoning_effort']}"),
                     tr(f"Dùng {metadata['history_used']} kỳ, tới #{metadata['cutoff_draw_id']}."),
                     "", tr("Giải thích do AI cung cấp:"), metadata["explanation"], "", tr(metadata["notice"])]
            if rule.game_id in ("mega", "power", "lotto"):
                tier = {"mega": "Jackpot", "power": "Jackpot 1", "lotto": "Độc Đắc"}[rule.game_id]
                p = probabilities(rule, tickets[0])[tier]
                lines.append(tr(f"App tính độc lập xác suất giải cao nhất cho một bộ: {p.numerator}/{p.denominator:,}."))
            self.explanation.setPlainText("\n".join(lines))
            self.notice.setText(f"Đã nhận và kiểm tra {len(tickets)} bộ do AI đề xuất. Điền kỳ dự định chơi nếu muốn lưu.")
        self.start_task(task, complete, f"Đang gửi {window} kỳ cho AI phân tích và đề xuất bộ số…", streaming=True, delta_target=self.explanation)

    def save_generated(self):
        if not self.generated:
            raise ValueError("Tạo bộ số trước khi lưu.")
        rule, method, tickets, snapshot, metadata = self.generated
        self.store.save_suggestions(rule, tickets, self.target.text().strip(), method, snapshot, metadata=metadata)
        self.saved_label.setText(f"Đã lưu {len(self.store.suggestions(rule))} bộ cho trò/biến thể này.")
        self.notice.setText("Đã lưu bộ số cùng phương pháp và bản dữ liệu đối chiếu. Chưa xác nhận thời điểm khóa kỳ đích.")

    def open_history_source(self, row, column):
        url = self.history_table.item(row, 3).text()
        parsed = QUrl(url)
        if parsed.scheme() == "https" and parsed.host() and not parsed.userName() and not parsed.password():
            QDesktopServices.openUrl(parsed)

    def start_task(self, task, on_result, message, streaming=False, allow_partial=False, delta_target=None):
        if self.worker:
            raise ValueError("Đợi thao tác hiện tại hoàn tất hoặc bấm Hủy.")
        self.worker = Worker(task, self, allow_partial=allow_partial)
        def receive(result):
            if not allow_partial and result.get("status") == "incomplete":
                self.notice.setText("Kết quả chưa hoàn tất; chưa lưu dữ liệu.")
                return
            if self.worker and (not self.worker.cancelled.is_set() or (allow_partial and result.get("status") == "incomplete")):
                self.guard(lambda: on_result(result))
        self.worker.result.connect(receive)
        self.worker.failed.connect(lambda text: self.notice.setText(text))
        self.worker.progress.connect(self.show_progress)
        if streaming:
            self.worker.delta.connect(lambda text: self.append_delta(text, delta_target))
        self.worker.finished.connect(self.task_finished)
        for widget in self.actions+[self.game, self.mode, self.base, self.model, self.key, self.method,
                                    self.count, self.target, self.query, self.history_limit,
                                    self.window_size, self.stats_segments, self.verify_method,
                                    self.history_search, self.history_filter]:
            widget.setEnabled(False)
        for widget in [self.language_choice, self.analysis_window_input, *self.draw_limit_inputs.values(), *self.auto_update_inputs.values(), *self.auto_time_inputs.values()]:
            widget.setEnabled(False)
        self.progress.setRange(0, 0); self.progress.show(); self.cancel_button.show()
        self.status_text.setText("●  Đang xử lý")
        self.notice.setText(message); self.worker.start()

    def show_progress(self, done, total):
        self.progress.setRange(0, total); self.progress.setValue(done)
        self.status_text.setText(f"●  {done} / {total}")

    def append_delta(self, text, target=None):
        target = self.answer if target is None else target
        target.moveCursor(QTextCursor.MoveOperation.End)
        target.insertPlainText(text)

    def cancel_task(self):
        if self.worker:
            self.worker.cancelled.set()
            self.notice.setText("Đang hủy; cần chờ thao tác mạng hiện tại trả về. Yêu cầu AI đã gửi có thể vẫn tính phí.")

    def task_finished(self):
        worker, self.worker = self.worker, None
        worker.deleteLater()
        for widget in self.actions+[self.game, self.mode, self.base, self.model, self.key, self.method,
                                    self.count, self.target, self.query, self.history_limit,
                                    self.window_size, self.stats_segments, self.verify_method,
                                    self.history_search, self.history_filter]:
            widget.setEnabled(True)
        for widget in [self.language_choice, self.analysis_window_input, *self.draw_limit_inputs.values(), *self.auto_update_inputs.values()]:
            widget.setEnabled(True)
        for game, clock in self.auto_time_inputs.items():
            clock.setEnabled(self.auto_update_inputs[game].isChecked())
        self.progress.hide(); self.cancel_button.hide()
        self.status_text.setText("●  Sẵn sàng")
        self.refresh_generation_view()
        if self.closing:
            self.close()

    def sync(self):
        rule, limit, path = self.rule, self.history_limit.value(), self.store.path
        known = self.store.sync_window(rule, limit)
        def task(cancel, progress, delta):
            receipt = OfficialSource(path.parent/"source-cache", max_attempts=1).fetch_history(rule, limit, cancel=cancel, progress=progress, known_draws=known)
            if cancel():
                raise CancelledError("Đã hủy tải; chưa nhập dữ liệu.")
            return receipt
        def complete(receipt):
            def check_cancel():
                if self.worker and self.worker.cancelled.is_set():
                    raise CancelledError("Đã hủy cập nhật; giữ nguyên lịch sử.")
            counts = self.store.apply_sync(rule, receipt, limit, check_cancel=check_cancel)
            self.refresh()
            self.notice.set_parts(f"Cập nhật: {counts}. ", receipt["note"])
        self.start_task(task, complete, f"Đang kiểm tra kỳ mới của {rule.name}; giữ tối đa {limit} kỳ…")

    def update_auto_status(self, runs):
        latest = {}
        for row in runs:
            latest.setdefault(row["game_id"], row)
        for game, status in self.auto_status_labels.items():
            row = latest.get(game)
            if row is None:
                status.setText("Chưa có lần tự cập nhật nào.")
                continue
            state = {"running": "đang chạy", "success": "hoàn tất", "failed": "thất bại"}.get(row["status"], row["status"])
            prefix = f"{row['day']}: tự cập nhật {state}."
            if row["status"] == "failed":
                detail = "Bản ghi cũ chưa có chi tiết lỗi." if row["message"].startswith("Scheduled update failed (") else row["message"]
                status.set_parts(prefix, " ", detail, " ", "Không tự thử lại trong ngày; bấm Cập nhật lịch sử để thử thủ công.")
            else:
                status.setText(prefix)

    def poll_background_updates(self):
        if self.worker or self.closing:
            return
        try:
            runs = self.store.auto_update_runs()
            self.update_auto_status(runs)
            current = {(row["game_id"], row["day"]): (row["status"], row["message"]) for row in runs}
            changed = [row for row in runs if self._auto_results.get((row["game_id"], row["day"])) != (row["status"], row["message"])]
            self._auto_results = current
            draws = self.store.list_draws(self.rule)
            if draws != self.draws:
                self.draws = draws
                fill(self.history_table, [[draw.draw_id, draw_date(draw), number_text(draw.payload), draw.source_url] for draw in reversed(draws)])
                self.filter_history(); self.update_analysis_copy(); self.refresh_statistics(); self.refresh_overview()
                self.notice.setText("Lịch sử đã được cập nhật bên ngoài; bộ số và báo cáo đang xem giữ nguyên.")
            today = datetime.now(timezone(timedelta(hours=7))).date().isoformat()
            for row in changed:
                if row["day"] == today and row["game_id"] == self.rule.game_id and row["status"] in ("success", "failed"):
                    name = get_rule(row["game_id"]).name
                    if row["status"] == "success":
                        self.notice.setText(f"Tự cập nhật {name}: hoàn tất. Bộ số và báo cáo đang xem giữ nguyên.")
                    else:
                        detail = "Bản ghi cũ chưa có chi tiết lỗi." if row["message"].startswith("Scheduled update failed (") else row["message"]
                        self.notice.set_parts(f"Tự cập nhật {name}: thất bại. ", detail, " ", "Không tự thử lại trong ngày; bấm Cập nhật lịch sử để thử thủ công.")
                    break
        except (ValueError, OSError, sqlite3.Error) as error:
            self.notice.setText(f"Chưa đọc được kết quả tự cập nhật: {error}")

    def import_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, tr("Nhập lịch sử"), "", "CSV (*.csv)")
        if filename:
            with Path(filename).open("rb") as stream:
                raw = stream.read(20*1024*1024+1)
            counts = self.store.add_draws(self.rule, import_csv(raw, self.rule))
            self.refresh(); self.notice.setText(f"Đã nhập CSV: {counts}")

    def current_config(self):
        return ai.AIConfig(base_url=self.base.text().strip(), model=self.model.currentText().strip(), api_key=self.key.text().strip())

    def clear_model_catalog(self):
        current = self.model.currentText()
        self.model.clear()
        self.model.setCurrentText(current)

    def load_models(self):
        config = self.current_config()
        def task(cancel, progress, delta):
            return fetch_models(config, cancel)
        def complete(result):
            current = self.model.currentText()
            self.model.clear()
            for name in result["models"]:
                QComboBox.addItem(self.model, name)
            self.model.setCurrentText(current)
            self.notice.setText(f"Đã tải {len(result['models'])} model. Chọn trong danh sách hoặc nhập tên thủ công.")
        self.start_task(task, complete, "Đang tải danh sách model…")

    def save_config(self):
        save_settings(self.current_config(), self.config_path)
        self.notice.setText("Đã lưu base_url, api_key, model trong config.json.")

    def run_ai(self, test=False):
        config, rule = self.current_config(), self.rule
        query = self.query.text().strip() or f"Tìm lịch sử kết quả và thể lệ {rule.name}."
        query += f"\nNguồn chính thức: {BASE+rule.result_path}\nThể lệ: {rule.rules_url}"
        ai.build_request(config, "Chỉ trả lời OK." if test else query, web_search=not test)
        self.answer.clear()
        def task(cancel, progress, delta):
            return ai.test_model(config, cancel=cancel, on_delta=delta) if test else ai.search(config, query, cancel=cancel, on_delta=delta)
        def complete(result):
            self.answer.setPlainText(result["text"])
            for source in result["sources"]:
                self.answer.append(f'<p><a href="{escape(source["url"], quote=True)}">{escape(source["title"])}</a></p>')
            self.notice.setText(result["notice"])
        self.start_task(task, complete, "Đang test model với endpoint tự động…" if test else "Đang tìm nguồn trên web với endpoint tự động…", streaming=True)

    def backtest(self):
        if self.rule.kind != "set":
            raise ValueError("Kiểm chứng Max/Bingo18 chưa được bật; hiện hỗ trợ xác suất và bộ tham khảo.")
        rule, draws, method = self.rule, list(self.draws), self.method.currentData()
        window = self.backtest_history_window
        if method == AI_METHOD:
            raise ValueError("Phương pháp AI chưa hỗ trợ backtest hàng loạt. Chọn Bayes, tần suất hoặc đồng đều để kiểm chứng tại máy; không tự phát sinh nhiều yêu cầu API.")
        self.report.clear()
        def task(cancel, progress, delta):
            return run_backtest(rule, draws, {"method": method, "seed": 42, "history_window": window}, cancel=cancel, progress=progress)
        def complete(report):
            identifier = self.store.save_report(report)
            saved = self.store.reports()[0]
            self.report.setPlainText(json.dumps({k: v for k, v in saved.items() if k not in ("rows", "manifest")}, ensure_ascii=False, indent=2))
            state = "chưa hoàn tất, chỉ gồm phần đã chạy" if saved["status"] != "completed" else "hoàn tất"
            self.notice.set_parts(f"Đã lưu báo cáo #{identifier}: ", state, ". ", saved["conclusion"])
        self.start_task(task, complete, "Đang kiểm chứng theo thời gian; không dùng dữ liệu kỳ đích để tạo vé…", allow_partial=True)

    def run_simulation(self):
        rule = self.rule
        if rule.kind != "set":
            raise ValueError("Mô phỏng hiện hỗ trợ Mega, Power, Lotto và Keno; trò đang chọn còn chờ xác minh luật.")
        ticket = self.generated[2][0] if self.generated else self.sample_ticket()
        self.report.clear()
        def task(cancel, progress, delta):
            return simulate(rule, ticket, 10_000, 42, cancel=cancel, progress=progress)
        def complete(report):
            self.report.setPlainText(json.dumps({"ticket": ticket.selections, **report}, ensure_ascii=False, indent=2))
            prefix = "Mô phỏng chưa hoàn tất. " if report["status"] != "completed" else ""
            self.notice.set_parts(prefix, report["note"])
        self.start_task(task, complete, "Đang mô phỏng 10.000 kỳ…", allow_partial=True)

    def closeEvent(self, event):
        if self.worker:
            self.closing = True; self.cancel_task(); event.ignore()
        else:
            if self.isVisible():
                try:
                    path = self.config_path.with_name("window_geometry.bin")
                    path.parent.mkdir(parents=True, exist_ok=True)
                    geometry = self.saveGeometry()
                    file = QSaveFile(str(path))
                    if not (file.open(QIODevice.OpenModeFlag.WriteOnly)
                            and file.write(geometry) == geometry.size() and file.commit()):
                        raise OSError("Could not save window geometry")
                except OSError:
                    self.notice.setText("Chưa lưu được kích thước cửa sổ. Lần mở sau sẽ dùng trạng thái đã lưu trước đó.")
            self.history_poll.stop()
            self.store.close(); event.accept()


def main(db_path=None):
    application = QApplication.instance() or QApplication(sys.argv[:1])
    application.setApplicationName(APP_NAME)
    application.setApplicationDisplayName(APP_TITLE)
    application.setApplicationVersion(__version__)
    application.setFont(QFont(["Segoe UI Variable Text", "Segoe UI"], 9))
    application.setWindowIcon(QIcon(str(ASSETS / "generated" / "07-ticket-gold.ico")))
    window = Desktop(db_path, CONFIG_PATH); window.show()
    if not show_policy(window, data_directory() / "policy-acceptance.txt"):
        window.close()
        return 0
    show_onboarding(window, first_run=True)
    return application.exec()
