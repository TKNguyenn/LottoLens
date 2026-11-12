"""Offline summaries of Vietlott's published game rules."""
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QHBoxLayout, QPushButton, QTextBrowser, QVBoxLayout

from .i18n import tr
from .theme import apply_theme
from .widgets import label


GUIDES = {
    "mega": (
        "https://info.vietlott-sms.vn/quydinh/game_mega.html",
        """
### Cách chọn số và quay thưởng

Chọn 6 số khác nhau từ **01–45**. Vietlott quay 6 số khác nhau. Đếm số trùng, không xét thứ tự.

### Điều kiện trúng giải

- **Jackpot:** trùng 6 số.
- **Giải Nhất:** trùng 5 số.
- **Giải Nhì:** trùng 4 số.
- **Giải Ba:** trùng 3 số.
""",
        """
### Selection and draw

Choose 6 distinct numbers from **01–45**. Vietlott draws 6 distinct numbers. Count the matches in any order.

### Winning conditions

- **Jackpot:** match 6 numbers.
- **First prize:** match 5 numbers.
- **Second prize:** match 4 numbers.
- **Third prize:** match 3 numbers.
""",
    ),
    "power": (
        "https://vietlott.vn/static.vietlott.vn/uploads/Files/QUYET%20DINH/TH%E1%BB%82%20L%E1%BB%86%20THAM%20GIA%20D%E1%BB%B0%20TH%C6%AF%E1%BB%9ENG%20POWER%20655.pdf",
        """
### Cách chọn số và quay thưởng

Chọn 6 số khác nhau từ **01–55**. Kỳ quay có 6 số chính và 1 số đặc biệt lấy từ 49 số còn lại. Vé chỉ chọn 6 số; số đặc biệt dùng để phân biệt Jackpot 2 với giải Nhất. Thứ tự các số trên vé không ảnh hưởng.

### Điều kiện trúng giải

- **Jackpot 1:** trùng cả 6 số chính.
- **Jackpot 2:** trùng 5 số chính và số còn lại trên vé trùng số đặc biệt.
- **Giải Nhất:** trùng 5 số chính, số còn lại không trùng số đặc biệt.
- **Giải Nhì:** trùng 4 số chính.
- **Giải Ba:** trùng 3 số chính.
""",
        """
### Selection and draw

Choose 6 distinct numbers from **01–55**. The draw produces 6 main numbers and 1 bonus number from the remaining 49. The ticket has 6 selections; the bonus distinguishes Jackpot 2 from first prize. Ticket order does not matter.

### Winning conditions

- **Jackpot 1:** match all 6 main numbers.
- **Jackpot 2:** match 5 main numbers plus the bonus with the remaining ticket number.
- **First prize:** match 5 main numbers without the bonus.
- **Second prize:** match 4 main numbers.
- **Third prize:** match 3 main numbers.
""",
    ),
    "lotto": (
        "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/535",
        """
### Cách chọn số và quay thưởng

Chọn 5 số chính khác nhau từ **01–35** và 1 số đặc biệt từ **01–12**. Kỳ quay có 5 số chính và 1 số đặc biệt từ nhóm riêng. So số chính không theo thứ tự, rồi so số đặc biệt riêng.

### Điều kiện trúng giải

- **Độc Đắc:** 5 số chính và số đặc biệt.
- **Giải Nhất:** 5 số chính, sai số đặc biệt.
- **Giải Nhì:** 4 số chính và số đặc biệt.
- **Giải Ba:** 4 số chính, sai số đặc biệt.
- **Giải Tư:** 3 số chính và số đặc biệt.
- **Giải Năm:** 3 số chính, sai số đặc biệt.
- **Giải Khuyến Khích:** 0–2 số chính và trùng số đặc biệt.

Ở kỳ được Vietlott công bố chia Độc Đắc, phần chia có thể bổ sung vào giải Nhất đến giải Năm. Xem công bố của đúng kỳ để đối chiếu.
""",
        """
### Selection and draw

Choose 5 distinct main numbers from **01–35** and 1 special number from **01–12**. The draw produces 5 main numbers and 1 special number from a separate pool. Match main numbers in any order and check the special number separately.

### Winning conditions

- **Jackpot:** 5 main numbers and the special number.
- **First prize:** 5 main numbers without the special number.
- **Second prize:** 4 main numbers and the special number.
- **Third prize:** 4 main numbers without the special number.
- **Fourth prize:** 3 main numbers and the special number.
- **Fifth prize:** 3 main numbers without the special number.
- **Consolation prize:** 0–2 main numbers plus the special number.

In a draw designated by Vietlott for jackpot distribution, first through fifth prizes may receive a share. Check the announcement for the specific draw.
""",
    ),
    "keno": (
        "https://vietlott.vn/vi/choi/keno/gioi-thieu-san-pham-keno",
        """
### Cách chọn số và quay thưởng

Chọn từ 1 đến 10 số khác nhau trong **01–80**. Số lượng đã chọn là bậc. Mỗi kỳ quay 20 số khác nhau, dùng chung cho mọi bậc. Thứ tự không ảnh hưởng.

**Bậc đang chọn: {0} · Số khớp được thưởng: {1}.**

### Điều kiện trúng giải

| Bậc | Số khớp được thưởng |
| --- | --- |
{2}

### Cách chơi bổ sung

- **Chẵn/Lẻ:** chọn chẵn hoặc lẻ thì cần ít nhất 11 trong 20 số thuộc nhóm đã chọn. Hòa khi 10 chẵn, 10 lẻ.
- **Lớn/Nhỏ:** Lớn là 41–80, Nhỏ là 01–40. Cần ít nhất 11 số thuộc nửa đã chọn. Hòa khi mỗi nửa có 10 số.

Mức thưởng tùy số khớp hoặc nhóm đã chọn. Mục Xác suất của LottoLens hiện hiển thị phân phối số khớp cho các bậc 1–10.
""",
        """
### Selection and draw

Choose 1 to 10 distinct numbers from **01–80**. The number selected is your tier. Each draw produces 20 distinct numbers shared by all tiers. Order does not matter.

**Selected tier: {0} · Winning match counts: {1}.**

### Winning conditions

| Tier | Winning match counts |
| --- | --- |
{2}

### Additional plays

- **Even/Odd:** an even or odd selection requires at least 11 of the 20 numbers in the chosen group. A tie requires 10 even and 10 odd.
- **High/Low:** high is 41–80 and low is 01–40. At least 11 numbers must be in the chosen half. A tie requires 10 in each half.

Payouts depend on the match count or group selected. LottoLens shows match-count probabilities for tiers 1–10.
""",
    ),
    "max3d": (
        "https://info.vietlott-sms.vn/hdsd/game_3d.html",
        """
### Cách chọn số và quay thưởng

Vé Max 3D cơ bản chọn một bộ ba chữ số từ **000–999**. Giữ nguyên số 0 đầu và thứ tự chữ số, ví dụ `007` khác `070`. Mỗi kỳ có 20 bộ kết quả, chia thành 4 nhóm.

### Điều kiện trúng giải

- **Đặc biệt:** bộ đã chọn trùng một trong 2 kết quả của nhóm Đặc biệt.
- **Giải Nhất:** trùng một trong 4 kết quả của nhóm Nhất.
- **Giải Nhì:** trùng một trong 6 kết quả của nhóm Nhì.
- **Giải Ba:** trùng một trong 8 kết quả của nhóm Ba.

### Max 3D+

Chọn hai bộ ba và dùng cùng kết quả Max 3D. **Đặc biệt** cần trùng cả hai bộ Đặc biệt theo bất kỳ thứ tự nào. **Nhất/Nhì/Ba** cần hai bộ cùng khớp trong nhóm tương ứng. **Tư** cần hai bộ khớp trong 20 kết quả. **Năm** cần một bộ khớp trong nhóm Đặc biệt. **Sáu** cần một bộ khớp trong 18 kết quả còn lại. LottoLens hiện tính xác suất cho vé Max 3D một bộ.
""",
        """
### Selection and draw

A basic Max 3D ticket contains one three-digit number from **000–999**. Keep leading zeros and digit order: `007` differs from `070`. Each draw produces 20 results across four groups.

### Winning conditions

- **Special prize:** match one of the 2 results in the special group.
- **First prize:** match one of the 4 results in the first group.
- **Second prize:** match one of the 6 results in the second group.
- **Third prize:** match one of the 8 results in the third group.

### Max 3D+

Select two three-digit numbers and use the same Max 3D draw. **Special** requires both special results in either order. **First/second/third** require both numbers in the corresponding group. **Fourth** requires both numbers among the 20 results. **Fifth** requires one match in the special group. **Sixth** requires one match among the other 18. LottoLens currently calculates odds for the one-number Max 3D ticket.
""",
    ),
    "max3dpro": (
        "https://info.vietlott-sms.vn/hdsd/game_3dp.html",
        """
### Cách chọn số và quay thưởng

Chọn hai bộ ba chữ số từ **000–999**. Giữ thứ tự hai bộ, thứ tự chữ số và số 0 đầu. Hai bộ trên vé có thể giống nhau. Kỳ quay có 20 kết quả, chia theo nhóm Đặc biệt/Nhất/Nhì/Ba với lần lượt 2/4/6/8 kết quả.

### Điều kiện trúng giải

- **Đặc biệt:** hai bộ trên vé khớp hai kết quả Đặc biệt theo đúng thứ tự quay.
- **Phụ Đặc biệt:** hai bộ khớp hai kết quả Đặc biệt theo thứ tự ngược.
- **Nhất/Nhì/Ba:** hai bộ khớp hai vị trí trong cùng nhóm tương ứng, không xét thứ tự hai bộ.
- **Tư:** hai bộ khớp hai vị trí bất kỳ trong 20 kết quả.
- **Năm:** ít nhất một bộ khớp một kết quả trong nhóm Đặc biệt.
- **Sáu:** ít nhất một bộ khớp một trong 18 kết quả còn lại.

Với vé có hai bộ giống nhau, hạng cần khớp hai bộ đòi hỏi hai lần xuất hiện ở các vị trí hợp lệ. Một vé có thể thỏa nhiều hạng. Xem thể lệ để đối chiếu cách cộng giải.
""",
        """
### Selection and draw

Choose two three-digit numbers from **000–999**. Keep the pair order, digit order, and leading zeros. The pair may contain two identical numbers. The draw produces 20 results, split into the special, first, second, and third groups of 2, 4, 6, and 8 results.

### Winning conditions

- **Special prize:** match the two special results in draw order.
- **Reverse special prize:** match the two special results in reverse draw order.
- **First/second/third:** match two positions in the corresponding group in either pair order.
- **Fourth:** match two positions anywhere among the 20 results.
- **Fifth:** match at least one result in the special group.
- **Sixth:** match at least one of the other 18 results.

For an identical pair, a two-match tier requires two occurrences in eligible positions. A ticket can qualify for multiple tiers. Consult the official rules for how prizes are combined.
""",
    ),
    "bingo18": (
        "https://info.vietlott-sms.vn/game_bingo.html",
        """
### Cách chọn số và quay thưởng

Mỗi kỳ quay ra 3 số, mỗi số từ **1–6** và có thể lặp. Chọn một ô theo cách chơi: đếm số lần xuất hiện, chọn tổng hoặc chọn khoảng tổng. Thứ tự kết quả không ảnh hưởng các ô này.

### Điều kiện trúng giải

- **Một số trùng:** chọn một số. Số đó xuất hiện 1, 2 hoặc 3 lần thì có hạng tương ứng với số lần xuất hiện.
- **Hai số trùng:** số đã chọn xuất hiện ít nhất hai lần, kể cả khi xuất hiện cả ba lần.
- **Ba số trùng:** cả ba kết quả đều là số đã chọn. Với ô **Ba số bất kỳ**, cả ba chỉ cần giống nhau.
- **Cộng tổng:** tổng của ba kết quả đúng bằng số đã chọn từ 3 đến 18.
- **Lớn–Hòa–Nhỏ:** tổng **12–18** là Lớn, **10–11** là Hòa và **3–9** là Nhỏ.

Ví dụ kết quả `2, 2, 5` có tổng 9: thỏa ô Tổng 9, ô Nhỏ và ô Hai số 2 nếu đối chiếu từng lựa chọn riêng.
""",
        """
### Selection and draw

Each draw produces 3 numbers from **1–6**, with repeats possible. Choose a cell based on occurrences, an exact total, or a total range. Draw order does not affect these selections.

### Winning conditions

- **Single number:** choose a number. One, two, or three occurrences each qualify for a corresponding tier.
- **Double:** the chosen number appears at least twice, including three occurrences.
- **Triple:** all three results equal the chosen number. **Any triple** requires all three to match one another.
- **Total:** the three results sum to the selected number from 3 to 18.
- **Big–Tie–Small:** **12–18** is big, **10–11** is a tie, and **3–9** is small.

For example, `2, 2, 5` totals 9. It qualifies for Total 9, Small, and Double 2 when each selection is checked separately.
""",
    ),
}

# Match counts in Vietlott's basic-play matrix, indexed by tier minus one.
KENO_MATCHES = ("1", "2", "2, 3", "2–4", "3–5", "3–6", "3–7", "0 hoặc 4–8", "0 hoặc 4–9", "0 hoặc 5–10")


def show_game_guide(window, rule):
    source, vietnamese, english = GUIDES[rule.game_id]
    content = english if window.language == "en" else vietnamese
    if rule.game_id == "keno":
        matches = [row.replace("hoặc", "or") for row in KENO_MATCHES] if window.language == "en" else KENO_MATCHES
        rows = "\n".join(f"| {tier} | {counts} |" for tier, counts in enumerate(matches, 1))
        content = content.format(rule.selected, matches[rule.selected - 1], rows)

    title = f"{rule.name} · {tr('Hướng dẫn trò chơi')}"
    dialog = QDialog(window, Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
    dialog.setObjectName("gameGuide")
    dialog.setWindowTitle(title)
    dialog.setAccessibleName(title)
    dialog.resize(680, 560)
    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(22, 18, 22, 18)
    layout.setSpacing(10)
    layout.addWidget(label(title, "title"))
    browser = QTextBrowser()
    browser.setAccessibleName(title)
    browser.setMarkdown(content.strip())
    layout.addWidget(browser, 1)
    footer = QHBoxLayout()
    official = QPushButton(tr("Nguồn chính thức Vietlott") + " ↗")
    official.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(source)))
    footer.addWidget(official)
    footer.addStretch()
    close = QPushButton(tr("Đóng hướng dẫn"))
    close.clicked.connect(dialog.accept)
    footer.addWidget(close)
    layout.addLayout(footer)
    apply_theme(dialog, window.theme_name)
    dialog.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
    dialog.setFocus()
    dialog.exec()
