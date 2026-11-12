"""Standalone, disposable design preview. No database or network calls."""
import argparse
from pathlib import Path
import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFormLayout, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QMainWindow, QPushButton, QProgressBar,
    QScrollArea, QSpinBox, QStackedWidget, QTableWidget, QTableWidgetItem,
    QTextBrowser, QVBoxLayout, QWidget, QHeaderView,
)

from app.widgets import STYLE, label, surface, table


class Preview(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vietlott Desktop — Bản xem giao diện")
        self.resize(1280, 850); self.setMinimumSize(1000, 700)
        central = QWidget(); self.setCentralWidget(central)
        root = QHBoxLayout(central); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
        sidebar = QFrame(); sidebar.setObjectName("sidebar"); sidebar.setFixedWidth(225)
        left = QVBoxLayout(sidebar); left.setContentsMargins(18, 30, 18, 24); left.setSpacing(14)
        left.addWidget(label("Vietlott Desktop", "brand"))
        left.addWidget(label("Lịch sử & xác suất", "subtle")); left.addSpacing(20)
        self.nav = QListWidget()
        self.nav.addItems(["Tổng quan", "Lịch sử", "Thống kê", "Xác suất", "Bộ số tham khảo", "Kiểm chứng", "AI & cấu hình"])
        left.addWidget(self.nav, 1)
        left.addWidget(label("Bản xem giao diện\nChưa nối dữ liệu hoặc dịch vụ AI.", "subtle"))
        root.addWidget(sidebar)
        workspace = QWidget(); workspace.setObjectName("workspace")
        right = QVBoxLayout(workspace); right.setContentsMargins(32, 24, 32, 22); right.setSpacing(18)
        header = QHBoxLayout()
        self.game = QComboBox(); self.game.addItems(["Mega 6/45", "Power 6/55", "Lotto 5/35", "Keno", "Max 3D", "Max 3D Pro", "Bingo18"])
        self.game.setMinimumWidth(200); header.addWidget(self.game); header.addStretch()
        header.addWidget(label("Dữ liệu minh họa • chưa gọi mạng", "subtle")); right.addLayout(header)
        right.addWidget(label("Bạn đang xem prototype. Các kết quả và thao tác bên dưới dùng để duyệt bố cục.", "banner"))
        self.pages = QStackedWidget()
        builders = [self.overview, self.history, self.statistics, self.odds, self.suggestions, self.backtest, self.ai]
        for builder in builders:
            page = QWidget(); page.setObjectName("workspace"); layout = QVBoxLayout(page); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(18)
            builder(layout)
            scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame); scroll.setWidget(page)
            self.pages.addWidget(scroll)
        right.addWidget(self.pages, 1)
        self.notice = label("Thống kê quá khứ không tự làm tăng xác suất trúng kỳ tiếp theo.", "subtle")
        right.addWidget(self.notice); root.addWidget(workspace, 1)
        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex); self.nav.setCurrentRow(0)
        self.game.currentTextChanged.connect(lambda game: self.notice.setText(f"Đang xem bố cục cho {game}. Dữ liệu ở prototype vẫn là minh họa."))

    def button(self, text, action=None, primary=False):
        button = QPushButton(text)
        if primary:
            button.setObjectName("primary")
        button.clicked.connect(action or (lambda: self.notice.setText("Thao tác minh họa: chưa cập nhật dữ liệu, ghi key hoặc gọi API.")))
        return button

    def heading(self, layout, title, subtitle):
        layout.addWidget(label(title, "title")); layout.addWidget(label(subtitle, "subtle"))

    def overview(self, layout):
        self.heading(layout, "Tổng quan Mega 6/45", "Theo dõi kết quả và kiểm tra phạm vi dữ liệu trước khi phân tích.")
        frame, content = surface()
        content.addWidget(label("Kỳ minh họa #01586 • 08/11/2026", "subtle"))
        balls = QHBoxLayout(); balls.setSpacing(14)
        for number in ("01", "02", "14", "20", "23", "36"):
            ball = QLabel(number); ball.setFixedSize(68, 68); ball.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ball.setStyleSheet("background:#C8253F;color:white;border-radius:34px;font-size:24px;font-weight:650;")
            balls.addWidget(ball)
        balls.addStretch(); content.addLayout(balls)
        content.addWidget(label("Nguồn dự kiến: kết quả chính thức Vietlott. Ở app thật, mỗi kỳ có liên kết nguồn và bản lưu đối chiếu.", "subtle"))
        actions = QHBoxLayout(); actions.addWidget(self.button("Cập nhật lịch sử", primary=True)); actions.addWidget(self.button("Xem các kỳ trước", lambda: self.nav.setCurrentRow(1))); actions.addStretch(); content.addLayout(actions)
        layout.addWidget(frame)
        layout.addWidget(table(["Phần dữ liệu", "Trạng thái minh họa", "Ý nghĩa"], [
            ["Lịch sử đã lưu", "100 kỳ", "Có thể phân tích tại máy"],
            ["Độ đầy đủ", "Chưa xác nhận", "100 kỳ không đồng nghĩa toàn bộ lịch sử"],
            ["Gợi ý đã lưu", "Chưa có", "Chỉ lưu trước kỳ đích khi biết đủ thời điểm"],
        ]))

    def history(self, layout):
        self.heading(layout, "Lịch sử kết quả", "Kết quả chính, số đặc biệt và nguồn được giữ riêng.")
        tools = QHBoxLayout(); tools.addWidget(self.button("Cập nhật lịch sử", primary=True)); tools.addWidget(self.button("Nhập CSV")); tools.addStretch(); layout.addLayout(tools)
        layout.addWidget(table(["Kỳ", "Ngày quay", "Bộ số chính", "Nguồn"], [
            ["01586", "08/11/2026", "01 02 14 20 23 36", "Vietlott • minh họa"],
            ["01585", "06/11/2026", "01 10 37 38 39 45", "Vietlott • minh họa"],
            ["01584", "04/11/2026", "07 14 20 30 34 40", "Vietlott • minh họa"],
        ]))
        layout.addWidget(label("Nếu nguồn sửa kết quả, app giữ bản cũ và bản sửa; báo cáo dùng dữ liệu cũ được đánh dấu cần kiểm tra lại.", "subtle"))

    def statistics(self, layout):
        self.heading(layout, "Thống kê xuất hiện", "So sánh số lần quan sát với mức kỳ vọng khi quay ngẫu nhiên.")
        filters = QHBoxLayout(); filters.addWidget(label("Phạm vi")); window = QComboBox(); window.addItems(["90 kỳ gần nhất", "30 kỳ gần nhất", "Toàn bộ dữ liệu đã lưu"]); filters.addWidget(window); filters.addStretch(); layout.addLayout(filters)
        frame, body = surface(); body.addWidget(label("Tần suất minh họa trong 90 kỳ"))
        for number, count in (("01", 16), ("02", 11), ("14", 15), ("20", 13), ("23", 9), ("36", 12)):
            line = QHBoxLayout(); line.addWidget(label(number)); bar = QProgressBar(); bar.setRange(0, 20); bar.setValue(count); bar.setFormat(f"{count} lần"); line.addWidget(bar, 1); body.addLayout(line)
        body.addWidget(label("Một số cụ thể có kỳ vọng 90 × 6/45 = 12 lần. Dao động quanh mức này có thể hoàn toàn do ngẫu nhiên.", "subtle")); layout.addWidget(frame)
        layout.addWidget(self.button("Xem cặp số và khoảng cách xuất hiện")); layout.addStretch()

    def odds(self, layout):
        self.heading(layout, "Xác suất lý thuyết", "Tính theo luật và tổ hợp; không thay đổi theo tần suất lịch sử.")
        frame, body = surface(); body.addWidget(label("Khớp cả 6 số Mega 6/45", "subtle"))
        number = label("1 trên 8.145.060"); number.setStyleSheet("font-size:36px;font-weight:650;color:#C8253F;"); body.addWidget(number)
        formula = label("C(45, 6) = 45! / (6! × 39!)\nP(khớp 6 số) = 1 / C(45, 6)\nGiả định: 6 số khác nhau được quay công bằng từ 45 số, không xét thứ tự.")
        formula.hide(); body.addWidget(self.button("Xem cách tính", lambda: formula.setVisible(not formula.isVisible()))); body.addWidget(formula)
        layout.addWidget(frame)
        layout.addWidget(table(["Phép tính", "Đầu vào", "Diễn giải"], [
            ["Một vé, một kỳ", "1 bộ số", "Mỗi bộ hợp lệ có xác suất như nhau"],
            ["Nhiều vé cùng kỳ", "Các bộ khác nhau", "Cần xét giao nhau theo hạng giải"],
            ["Nhiều kỳ", "Các kỳ độc lập", "Không có mốc chắc chắn sẽ trúng"],
        ]))

    def suggestions(self, layout):
        self.heading(layout, "Bộ số tham khảo", "Lưu cách chọn và dữ liệu đã dùng để đối chiếu sau kỳ quay.")
        frame, body = surface(); form = QFormLayout()
        method = QComboBox(); method.addItems(["Chọn ngẫu nhiên đồng đều", "Tần suất 90 kỳ • thử nghiệm"])
        count = QSpinBox(); count.setRange(1, 100); count.setValue(5)
        target = QLineEdit(); target.setPlaceholderText("Nhập mã kỳ đích")
        form.addRow("Phương pháp", method); form.addRow("Số bộ", count); form.addRow("Kỳ đích", target); body.addLayout(form)
        body.addWidget(self.button("Tạo bộ số tham khảo", primary=True)); body.addWidget(label("Chưa có bằng chứng phương pháp tần suất tăng xác suất trúng. Bản xem giao diện không tạo hoặc lưu vé thật.", "subtle")); layout.addWidget(frame); layout.addStretch()

    def backtest(self, layout):
        self.heading(layout, "Kiểm chứng phương pháp", "Dùng dữ liệu trước mỗi kỳ đích, so với chọn ngẫu nhiên cùng chi phí.")
        frame, body = surface(); body.addWidget(label("Dành riêng dữ liệu để đánh giá"))
        body.addWidget(label("90 kỳ làm nền → giai đoạn phát triển → tập kiểm tra cuối giữ riêng", "subtle"))
        body.addWidget(self.button("Chạy kiểm chứng", primary=True)); body.addWidget(label("Ví dụ trạng thái: có 100 kỳ, còn 10 kỳ sau warm-up. Chỉ báo cáo thăm dò; chưa đủ để có tập kiểm tra cuối theo quy tắc bản đầu.", "subtle")); layout.addWidget(frame)
        layout.addWidget(table(["Chỉ số", "Phương pháp", "Ngẫu nhiên"], [["Tỷ lệ vé nhận giải", "Chưa chạy", "Chưa chạy"], ["Khoảng dao động", "Chưa đủ dữ liệu", "200 lượt baseline dự kiến"]])); layout.addStretch()

    def ai(self, layout):
        self.heading(layout, "AI & cấu hình", "Tìm nguồn trên web và giải thích; dữ liệu kỳ quay vẫn được xác minh riêng.")
        frame, body = surface(); form = QFormLayout()
        base = QLineEdit("https://api.openai.com/v1"); model = QLineEdit("gpt-6.1-sol")
        key = QLineEdit(); key.setEchoMode(QLineEdit.EchoMode.Password); key.setPlaceholderText("Nhập tại máy; prototype chưa lưu")
        form.addRow("Base URL", base); form.addRow("API key", key); form.addRow("Model", model); body.addLayout(form)
        body.addWidget(label("Lưu trong config.json • endpoint /responses • streaming bật", "subtle")); body.addWidget(self.button("Lưu cấu hình")); layout.addWidget(frame)
        query = QLineEdit(); query.setPlaceholderText("Ví dụ: tìm nguồn lịch sử và thể lệ Power 6/55")
        layout.addWidget(query); layout.addWidget(self.button("Tìm trên web", primary=True))
        answer = QTextBrowser(); answer.setPlainText("Phản hồi sẽ xuất hiện từng phần tại đây.\n\nNguồn trích dẫn hiển thị riêng để mở kiểm tra.\n\nPrototype chưa gửi yêu cầu tới Vilao và không ghi API key."); answer.setMinimumHeight(145); layout.addWidget(answer)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--screenshot", type=Path)
    args = parser.parse_args()
    application = QApplication.instance() or QApplication(sys.argv[:1])
    if not QFontDatabase.families():
        for filename in ("segoeui.ttf", "seguisb.ttf"):
            QFontDatabase.addApplicationFont(str(Path("C:/Windows/Fonts")/filename))
    application.setFont(QFont("Segoe UI", 10)); application.setStyleSheet(STYLE)
    window = Preview(); window.show()
    if args.screenshot:
        def capture():
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            for index, name in ((0, "overview"), (3, "odds"), (6, "ai")):
                window.nav.setCurrentRow(index); application.processEvents()
                target = args.screenshot if index == 0 else args.screenshot.with_name(args.screenshot.stem+"-"+name+".png")
                if not window.grab().save(str(target)):
                    raise RuntimeError("Không lưu được ảnh prototype.")
            # All seven pages must be reachable without touching the real services.
            for index in range(7):
                window.nav.setCurrentRow(index); application.processEvents()
                assert window.pages.currentIndex() == index
            window.close(); application.quit()
        QTimer.singleShot(250, capture)
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
