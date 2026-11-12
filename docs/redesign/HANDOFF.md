# HANDOFF — Implement lại giao diện Vietlott Desktop (PySide6)

Tài liệu này dành cho model/agent sẽ viết code. Đọc hết trước khi sửa một dòng nào.

---

## 0. Bối cảnh

Repo: `C:\Users\kietj\Documents\FINEPRO\Image Processing\New folder`
App desktop Python 3.11 + PySide6 6.11.2, đọc lịch sử Vietlott từ SQLite local, có gọi AI (streaming) khi người dùng bấm.

**Nhiệm vụ của bạn: thay tầng trình bày.** Không đổi lõi tính toán, không đổi storage, không đổi hành vi mạng.

```bash
# chạy app
"C:/Users/kietj/AppData/Local/Programs/Python/Python311/python.exe" main.py
# chạy test (BẮT BUỘC pass 69 test trước khi bàn giao)
"C:/Users/kietj/AppData/Local/Programs/Python/Python311/python.exe" -m pytest tests/ -q
```

Baseline hiện tại: **69 passed, 23 subtests passed**.

---

## 1. Đọc gì, theo thứ tự

| File | Vì sao |
|---|---|
| `docs/redesign/vietlott-redesign.html` | Bản thiết kế chuẩn. Mở bằng browser, bấm `T` đổi theme, click sidebar đổi trang. **Đây là nguồn sự thật về layout/màu/spacing.** |
| `docs/redesign/README.md` | Tóm tắt quyết định thiết kế + danh sách asset |
| `docs/redesign/assets/` | Logo SVG, `vietlott-desktop.ico`, bộ 32 icon `icon-*.svg` + `icons-sprite.svg` |
| `docs/redesign/assets/generated/07-ticket-gold.png` / `.ico` | **Icon app đã được chốt** (mẫu 07) |
| `app/ui.py` (470 dòng) | Code hiện tại — đọc kỹ, đây là thứ bạn thay |
| `app/widgets.py` (58 dòng) | QSS + helper hiện tại — sẽ bị thay bằng `app/theme.py` |
| `tests/test_ui.py` (257 dòng) | **Hợp đồng API.** 13 test gọi trực tiếp attribute/method của `Desktop` |
| `app/workers.py` | `Worker(QThread)`, không được đổi |

---

## 2. Ràng buộc cứng — vi phạm là fail

### 2.1 Hợp đồng test — 14 widget + 6 state + 9 method

Đây là **toàn bộ** những gì `tests/test_ui.py` chạm vào. Đã đối chiếu bằng script, không phải ước lượng.

**14 widget bắt buộc giữ tên** (đổi tên = test đỏ):

```
game  nav  pages  source_links  notice
history_table  suggestion_table
method  count  target  explanation
report  answer  key
```

**6 attribute state** (không phải widget):

```
store  worker  closing  generated  draws  test_button
```

**9 method** gọi trực tiếp: `refresh`, `sync`, `make_suggestions`, `save_generated`, `run_ai`, `backtest`, `run_simulation`, `save_config`, `cancel_task`. Cộng `.close()` của QMainWindow.

Được phép **thay kiểu widget** (QTableWidget → QTableView + model, QTextBrowser → QWidget tự vẽ) miễn là giữ các method mà test gọi trên chúng:

- `history_table` / `suggestion_table`: `.rowCount()`, `.item(row, col).text()`
- `explanation` / `report` / `answer`: `.toPlainText()`, `.toHtml()`, `.setPlainText()`, `.clear()`, `.append()`, `.moveCursor()`, `.insertPlainText()`
- `notice` / `source_links`: `.text()`, `.setText()`
- `nav`: `.setCurrentRow(int)`, `.currentRowChanged` signal
- `pages`: `.currentIndex()`
- `method`: `.findData(x)`, `.setCurrentIndex(i)`, `.currentData()`
- `count`: `.setValue(int)`, `.value()`
- `key` / `target`: `.setText()`, `.text()`
- `game`: `.setCurrentIndex(i)`, `.currentData()`
- `test_button`: `.click()`, `.isEnabled()`

**17 widget còn lại KHÔNG bị test ràng buộc** — đổi tên, gộp, xoá, thay bằng component khác đều được:

```
base  model  mode  query  actions  config_path
count_label  latest  summary  saved_label  method_note
history_limit  window_size  progress  cancel_button
stats_table  stats_note  odds_table  odds_note
```

> Ghi chú: `base`, `model`, `mode`, `query`, `progress`, `cancel_button`, `stats_table`, `odds_table`, `history_limit`, `window_size` vẫn **cần tồn tại về mặt chức năng** (để `refresh()`, `start_task()`, `run_ai()` hoạt động), chỉ là test không gọi tên chúng. Nếu đổi tên, phải sửa mọi chỗ tham chiếu trong `ui.py` — nhưng không ảnh hưởng test.

### 2.2 Giữ nguyên các method

```
__init__  rule(property)  nav setter  refresh  make_suggestions  save_generated
make_ai_suggestions  update_method_note  run_ai  backtest  run_simulation
sync  import_file  save_config  current_config  sample_ticket
start_task  show_progress  append_delta  cancel_task  task_finished
closeEvent  refresh_statistics  open_history_source  guard  button  heading
```

### 2.3 Được tự do thay đổi

- Bố cục, container, kiểu widget, QSS, icon, animation
- Thêm file mới (`app/theme.py`, `app/components/*.py`) thoải mái
- `app/widgets.py` — xoá được nếu thay hết

### 2.4 Không được chạm

- `app/ai.py`, `app/ai_generation.py`, `app/backtest.py`, `app/domain.py`, `app/evaluation.py`,
  `app/generation.py`, `app/probability.py`, `app/rules.py`, `app/settings.py`, `app/simulation.py`,
  `app/sources.py`, `app/statistics.py`, `app/storage.py`, `app/workers.py`, `main.py`
- `tests/` — không sửa test để test pass

### 2.5 Hành vi không được đổi

Đây là app tài chính có chi phí thật. Các ràng buộc sau là **yêu cầu nghiệp vụ**, không phải chi tiết UI:

1. **Không tự gọi mạng.** Mở app không được phát sinh request. Chỉ khi user bấm nút.
2. **Không auto-retry.** Lỗi HTTP/key/model → hiện lỗi, dừng. Không thử lại.
3. **Không lưu kết quả dở.** Worker trả `incomplete` thì không ghi vào `store`.
4. **Không ghi số do AI trả vào lịch sử.** Bộ số AI chỉ lưu qua `save_suggestions` khi user bấm Lưu.
5. **Không lưu API key vào record.** `save_suggestions(..., metadata=...)` không được chứa key.
6. **Không hardcode trạng thái thành công.** Trạng thái hiển thị phải lấy từ response thật.
7. **Disable input khi worker chạy** (`start_task` đã làm — giữ nguyên danh sách `self.actions + [game, mode, base, model, key, method]`).
8. **`closeEvent`** phải cancel worker và `event.ignore()` nếu đang chạy, chỉ `store.close()` khi idle.

---

## 3. Bản thiết kế — cách đọc

File HTML có 6 mục. Khi implement, mục **01 (mockup)** là chuẩn:

| Trang trong app | `nav` row | Mockup function (trong HTML) |
|---|---|---|
| Tổng quan | 0 | `pgOverview()` |
| Lịch sử | 1 | `pgHistory()` |
| Thống kê | 2 | `pgStats()` |
| Xác suất | 3 | `pgOdds()` |
| Bộ số tham khảo | 4 | `pgSuggest()` |
| Kiểm chứng | 5 | `pgVerify()` |
| AI & cấu hình | 6 | `pgAI()` |

Mở HTML → F12 → tìm function tương ứng để đọc chính xác cấu trúc HTML/CSS của trang đó. CSS class → QSS xem bảng ở mục **06** của HTML.

### 3.1 Layout khung

```
┌───────────────────────────────────────────────────────────┐
│ Titlebar 40px  [logo 26] Vietlott Desktop — Lịch sử & …   │  (native Qt title bar được thay bằng custom)
├──────────┬────────────────────────────────────────────────┤
│ Rail     │ Topline 56px:  ● Mega 6/45 · 100 kỳ   [game ▾] │
│ 236px    ├────────────────────────────────────────────────┤
│          │ Canvas  padding 20/22                          │
│ brand    │  pagehead (h1 21px + sub 12.5px + actions)     │
│ nav 7    │  ┌─────────────────────────────────────────┐   │
│          │  │  bento grid — 2 hoặc 3 cột               │   │
│ foot     │  └─────────────────────────────────────────┘   │
│ +theme   ├────────────────────────────────────────────────┤
│          │ Statusbar 34px:  ● Sẵn sàng      …notice…      │
└──────────┴────────────────────────────────────────────────┘
```

Lưới: `QGridLayout` với `setColumnStretch(0, 1.65)` / `(1, 1)` cho `b-2`; `(1,1,1)` cho `b-3`; `(1, 352)` cho `b-split`.

### 3.2 Token — 2 theme

Định nghĩa trong `app/theme.py` dạng dict, sinh QSS bằng `str.format` (KHÔNG dùng f-string cho QSS — dấu `{}` của QSS sẽ vỡ).

```python
LIGHT = dict(
    page="#F1F1F3", bg="#FFFFFF", bg_sunken="#FAFAFA", bg_elevated="#FFFFFF",
    fg="#101014", fg_muted="#5F5F6B", fg_subtle="#8C8C97",
    border="#E3E3E8", border_strong="#D2D2DA",
    red="#C81E33", red_hover="#A8162A", red_bright="#F0394E",
    red_soft="#FCEDEF", red_ink="#8E1224",
    gold="#A9761D", gold_soft="#FBF3E2",
    green="#0F7A57", green_soft="#E8F6F0",
    amber="#9A6A0B", amber_soft="#FDF4E3",
    ball_bg="#FFFFFF", ball_ring="#E3E3E8", ball_hit="#C81E33",
    on_red="#FFFFFF",
)
DARK = dict(
    page="#06060A", bg="#0F0F13", bg_sunken="#0A0A0D", bg_elevated="#16161C",
    fg="#F4F4F6", fg_muted="#A0A0AC", fg_subtle="#6F6F7C",
    border="#232329", border_strong="#33333D",
    red="#FF3B4E", red_hover="#FF5F70", red_bright="#FF6B7B",
    red_soft="#2A1116", red_ink="#FF8A96",
    gold="#F2C05C", gold_soft="#2A2314",
    green="#34D399", green_soft="#0F2A22",
    amber="#F0B84E", amber_soft="#2A2213",
    ball_bg="#1A1A20", ball_ring="#34343E", ball_hit="#FF3B4E",
    on_red="#14050A",   # ← chữ trên nền đỏ ở dark phải TỐI, không phải trắng
)
```

Nhịp: `4 / 6 / 8 / 10 / 12 / 14 / 18 / 22` px. Bán kính: `6 / 8 / 10 / 14 / 18` + pill. Font: `Segoe UI Variable Text` fallback `Segoe UI`. Số: `Cascadia Mono`.

### 3.3 Dark mode — 4 điều dễ sai

1. Đỏ phải **nâng sáng** `#C81E33` → `#FF3B4E`, không giữ nguyên (chìm trên nền tối).
2. Chữ trên nút đỏ đặc ở dark dùng **`#14050A`**, không dùng `#FFFFFF`.
3. `red_soft` ở dark là **hex đục** `#2A1116`, không phải `rgba(255,59,78,.12)` — Qt xử lý alpha QSS kém, dùng hex đã blend sẵn.
4. Không được chỉ đảo màu. `bg` không phải `#000000` mà `#0F0F13`, `page` sâu hơn `#06060A`.

### 3.4 Component cần viết

| Component | Ghi chú |
|---|---|
| `BallLabel` | QLabel 26/42/52px, `QPainterPath` vẽ ellipse + text, `paintEvent`. Biến thể: normal / hit (đỏ đặc) / gold (số đặc biệt). |
| `Badge` | QLabel pill 20px, 5 màu: neutral / red / gold / green / amber. Dùng `setProperty("variant", ...)` + QSS selector. |
| `StatCard` | label 11px + value 27px tabular + delta 11px |
| `SectionCard` | QFrame `border-radius:14px`, header 12.5px + optional icon 24px |
| `Callout` | QFrame, 3 loại: warn / info / success. Icon 14px + rich text |
| `EmptyState` | icon 46px + h4 13px + p 11.5px + đúng 1 CTA |
| `NumberHeatmap` | grid 9 cột, mỗi ô aspect 1:1, 7 bậc màu theo tần suất. `QWidget` + `paintEvent`. |
| `SidebarNav` | QListWidget custom `QStyledItemDelegate` để vẽ icon + text + badge + thanh đỏ trái 2.5px |
| `SegmentedControl` | QButtonGroup 3 nút, nút active nền `bg` + shadow |
| `MiniBar` | QFrame 4px cao, phần fill theo % |

`BallLabel` là component quan trọng nhất — mọi trang đều dùng. Viết đúng trước, các trang sau nhanh hơn.

> **Đã verify** trên PySide6 6.11.2 / Python 3.11.9: `str.format` QSS, `themed_icon()` (QSvgRenderer + recolor + cache), `BallLabel.paintEvent` (3 variant × 4 size), `NumberHeatmap` 45 ô, `QFrame` + `WA_StyledBackground`, và `QIcon` load `.ico` ở đủ 7 size 16→256. Snippet trong mục 4, 5 và trên đây chạy thật, không phải code mẫu lý thuyết.

### Icon đã chốt — 07

`07-ticket-gold.ico` đọc rõ ở cả 16px trên nền tối và nền sáng (đã render thật qua `QIcon`). Vé nghiêng + 3 chấm đỏ + cỏ vàng vẫn phân biệt được ở 16px; không cần bản đơn giản hoá riêng.

---

## 4. Icon — dùng gì

Đã chốt: **`assets/generated/07-ticket-gold.ico`** làm icon app.

```python
from PySide6.QtGui import QIcon
icon = QIcon(r"docs/redesign/assets/generated/07-ticket-gold.ico")
app.setWindowIcon(icon)     # main.py hoặc app/ui.py main()
window.setWindowIcon(icon)
```

Icon điều hướng: `assets/icons-sprite.svg` (32 `<symbol>`) hoặc từng `icon-*.svg`.
Qt không đọc SVG `<symbol>` trực tiếp → dùng từng file `icon-*.svg` với `QSvgRenderer`, hoặc convert sang PNG 2x.

**Recolor theo theme:** `stroke="currentColor"` không hoạt động trong Qt. Cách đúng:

```python
def themed_icon(path: str, color: str, size: int = 20) -> QIcon:
    """Đọc SVG, thay currentColor bằng hex, render ra QPixmap."""
    svg = Path(path).read_text(encoding="utf-8").replace("currentColor", color)
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    pix = QPixmap(size * 2, size * 2)   # 2x cho HiDPI
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    renderer.render(painter)
    painter.end()
    pix.setDevicePixelRatio(2)
    return QIcon(pix)
```

Cache theo `(path, color, size)` — đừng render lại mỗi lần `refresh()`.

---

## 5. Native Windows 11

```python
# dark titlebar
import ctypes
DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_SYSTEMBACKDROP_TYPE = 38
value = ctypes.c_int(1 if dark else 0)
ctypes.windll.dwmapi.DwmSetWindowAttribute(
    int(window.winId()), DWMWA_USE_IMMERSIVE_DARK_MODE,
    ctypes.byref(value), ctypes.sizeof(value))
```

Nếu làm custom titlebar (mockup có), cần `Qt.FramelessWindowHint` + tự xử lý drag/resize/min/max/close. **Cân nhắc: bỏ custom titlebar, dùng native cho an toàn** — native titlebar không vẽ được theo mockup nhưng không bug khi snap/multi-monitor/DPI.

QSS **không có** `box-shadow`. Dùng `QGraphicsDropShadowEffect` (chỉ 1 effect/widget, không lồng nhau).

---

## 6. QSS — những chỗ hay vỡ

| CSS trong mockup | QSS thật |
|---|---|
| `border-radius: 10px` | giống hệt ✓ |
| `box-shadow` | ❌ không có → `QGraphicsDropShadowEffect` |
| `backdrop-filter: blur()` | ❌ không có → acrylic native hoặc bỏ |
| `gap` | ❌ → `setSpacing()` trên layout |
| CSS Grid | ❌ → `QGridLayout` + `setColumnStretch` |
| `::before` / `::after` | ❌ → widget riêng hoặc custom `paintEvent` |
| `font-variant-numeric: tabular-nums` | ❌ → chọn font mono, hoặc `QFont.setStyleStrategy` |
| `color-mix()` | ❌ → tính sẵn hex trong Python |
| `var(--x)` | ❌ → `str.format(**tokens)` |
| `:hover` | `QPushButton:hover` ✓ |
| transition | ❌ → `QPropertyAnimation` thủ công |

**Bẫy QSS lớn nhất:** khi set `border-radius` cho `QFrame`, phải `setAttribute(Qt.WA_StyledBackground, True)` nếu không nền không vẽ. Và `QWidget` con **kế thừa** QSS của cha — dùng `objectName` hoặc `setProperty` + `style().unpolish/polish` để tách.

---

## 7. Thứ tự implement

1. **`app/theme.py`** — 2 dict token + `build_qss(tokens)` + `apply_theme(app, name)`.
2. **`app/components/`** — `BallLabel` trước, rồi `Badge`, `SectionCard`, `StatCard`, `Callout`, `EmptyState`.
3. **Shell** — rail + topline + statusbar + `QStackedWidget`, chưa cần nội dung trang.
4. **Từng trang**, thứ tự: `overview` → `history` → `stats` → `odds` → `suggest` → `verify` → `ai`.
5. **Heatmap + segmented control** (stats), **reveal key** (ai).
6. **Theme toggle** — lưu vào `config.json` (thêm key `theme`; `load_settings` sẽ từ chối key lạ → phải sửa `app/settings.py`, nhưng đó là file ngoài danh sách cấm, được phép **chỉ khi** bạn cập nhật `tests` tương ứng... **tốt hơn: lưu theme ra file riêng** `theme.json` cạnh config).

> Cảnh báo: `app/settings.py::load_settings` raise nếu `set(body) != {"base_url","api_key","model"}`. Đừng thêm `theme` vào `config.json`. Dùng `Path(CONFIG_PATH).parent / "theme.json"`.

Sau **mỗi** trang: chạy `pytest tests/ -q`. 69 test phải luôn xanh.

---

## 8. Checklist bàn giao

```
[ ] pytest tests/ -q                  → 69 passed, 23 subtests
[ ] python main.py                    → app mở, không exception
[ ] Bấm hết 7 mục sidebar             → không crash, nội dung đúng
[ ] Đổi Mega → Power → Lotto → Keno   → số kỳ / bảng / link nguồn cập nhật
[ ] Đổi qua lại light ↔ dark 2 lần    → không mất trạng thái, không lệch màu
[ ] Resize 1000×700 và 1920×1080      → không tràn, không cắt chữ
[ ] Lotto/Keno chưa có dữ liệu        → EmptyState hiện, CTA bấm được
[ ] Bấm "Cập nhật lịch sử" khi offline → lỗi hiện trong notice, app không treo
[ ] Đóng app khi đang tải             → không crash, không ghi dở
[ ] Không có request mạng nào khi mở app (kiểm bằng log/proxy)
```

---

## 9. Nếu bạn là model không đọc được ảnh

Mockup HTML có đủ thông tin dạng text: mỗi trang là một hàm JS trả về string HTML với inline style. Search `function pgOverview`, `function pgHistory`… để đọc cấu trúc chính xác. CSS ở đầu file, có comment `/* === */` chia mục.

Ảnh `docs/redesign/preview-hero.png` và `preview-dark.png` chỉ để tham khảo tổng thể — không cần, không nên đoán từ ảnh.

Nếu vẫn mơ hồ: **hỏi lại**, đừng đoán. Đặc biệt đừng đoán về hành vi mạng (mục 2.5) — đó là ràng buộc nghiệp vụ có chi phí thật.

---

## 10. Câu hỏi mở cần chốt với người dùng

1. Custom titlebar hay native titlebar Windows? (mockup vẽ custom; native an toàn hơn)
2. Có cần animation chuyển trang không, hay cắt hết cho nhẹ?
3. Font `Segoe UI Variable` không có trên Windows 10 — có cần support Win10 không?
4. Có cần export báo cáo ra PDF/PNG không? (mockup có nút "Xuất CSV" ở trang Xác suất nhưng chưa nối logic)
