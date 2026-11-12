# Prompt để đưa cho model khác

Copy nguyên khối dưới đây, dán vào chat của model đó. Kèm theo 3 thứ:
`docs/redesign/HANDOFF.md`, `docs/redesign/vietlott-redesign.html`, thư mục `docs/redesign/assets/`, và repo (hoặc ít nhất `app/` + `tests/`).

---

```
Bạn là senior PySide6 engineer. Nhiệm vụ: implement lại tầng giao diện của một app desktop
Python có sẵn, theo bản thiết kế đã chốt. KHÔNG đổi lõi tính toán, KHÔNG đổi storage,
KHÔNG đổi hành vi mạng.

## Đọc trước khi làm

1. `docs/redesign/HANDOFF.md` — ràng buộc kỹ thuật, hợp đồng API, checklist. ĐỌC HẾT.
2. `docs/redesign/vietlott-redesign.html` — mở bằng browser. Đây là bản thiết kế chuẩn.
   Bấm phím T để đổi theme sáng/tối. Click sidebar để xem 7 trang.
   Mỗi trang là một hàm JS (`pgOverview`, `pgHistory`, `pgStats`, `pgOdds`,
   `pgSuggest`, `pgVerify`, `pgAI`) trả về HTML + inline style — đọc trực tiếp
   trong file nếu bạn không xem được ảnh. CSS ở đầu file có comment chia mục.
3. `app/ui.py` — code hiện tại (470 dòng). Đây là thứ bạn thay.
4. `tests/test_ui.py` — HỢP ĐỒNG API. 13 test gọi trực tiếp attribute/method của class Desktop.
5. `docs/redesign/assets/` — logo, icon, .ico đã sẵn sàng.

## Ràng buộc cứng

- Giữ nguyên 14 widget + 6 state + 9 method là hợp đồng test (danh sách đầy đủ ở HANDOFF mục 2.1).
  Được đổi KIỂU widget, nhưng phải giữ các method mà test gọi trên chúng
  (`.rowCount()`, `.item(r,c).text()`, `.toPlainText()`, `.setCurrentRow()`...).
  17 widget còn lại không bị ràng buộc — đổi tên/gộp/xoá đều được.
- Giữ nguyên 22 method của `Desktop` (HANDOFF mục 2.2).
- KHÔNG sửa: `app/ai.py`, `app/ai_generation.py`, `app/backtest.py`, `app/domain.py`,
  `app/evaluation.py`, `app/generation.py`, `app/probability.py`, `app/rules.py`,
  `app/settings.py`, `app/simulation.py`, `app/sources.py`, `app/statistics.py`,
  `app/storage.py`, `app/workers.py`, `main.py`, `tests/`.
- KHÔNG sửa test để test pass. Nếu test đỏ, code của bạn sai.

## Hành vi không được đổi (ràng buộc nghiệp vụ, app có chi phí thật)

1. Mở app KHÔNG phát sinh request mạng. Chỉ khi user bấm nút.
2. KHÔNG auto-retry khi lỗi HTTP/key/model.
3. KHÔNG lưu kết quả dở (worker trả `incomplete` → không ghi store).
4. KHÔNG ghi số do AI trả vào lịch sử.
5. KHÔNG để API key lọt vào record đã lưu.
6. KHÔNG hardcode trạng thái "thành công".
7. Disable input khi worker chạy.
8. `closeEvent` phải cancel worker + `event.ignore()`, chỉ `store.close()` khi idle.

## Thiết kế

- Theme sáng: nền `#FFFFFF`/page `#F1F1F3`, nhấn đỏ `#C81E33`.
- Theme tối: nền `#0F0F13`/page `#06060A`, nhấn `#FF3B4E` (nâng sáng).
  Chữ trên nút đỏ đặc ở dark dùng `#14050A`, KHÔNG dùng trắng.
- Bố cục: rail trái 236px + topbar 56px + canvas padding 20/22 + statusbar 34px.
  Nội dung là bento grid 2–3 cột (`QGridLayout` + `setColumnStretch`).
- Số kết quả hiển thị dạng quả bóng tròn (BallLabel), không phải chuỗi text.
- Icon app: `docs/redesign/assets/generated/07-ticket-gold.ico`.
- Icon điều hướng: `docs/redesign/assets/icon-*.svg` (32 file), recolor theo theme.
- Nhịp spacing: 4/6/8/10/12/14/18/22. Bán kính: 6/8/10/14/18.

## Thứ tự làm

1. `app/theme.py` — 2 dict token + `build_qss(tokens)` (dùng `str.format`, KHÔNG f-string).
2. `app/components/` — `BallLabel` trước, rồi `Badge`, `SectionCard`, `StatCard`,
   `Callout`, `EmptyState`, `NumberHeatmap`, `SidebarNav`, `SegmentedControl`.
3. Shell (rail + topline + statusbar + QStackedWidget), chưa cần nội dung.
4. Từng trang: overview → history → stats → odds → suggest → verify → ai.
5. Theme toggle — lưu ra `theme.json` RIÊNG, không thêm key vào `config.json`
   (vì `load_settings` raise ValueError nếu có key lạ).

## Verify sau MỖI trang

```bash
"C:/Users/kietj/AppData/Local/Programs/Python/Python311/python.exe" -m pytest tests/ -q
```

Baseline: `69 passed, 23 subtests passed`. Con số này không được giảm.

## Lưu ý QSS (Qt không giống CSS)

- KHÔNG có `box-shadow` → `QGraphicsDropShadowEffect`.
- KHÔNG có `gap` → `setSpacing()`.
- KHÔNG có CSS Grid → `QGridLayout`.
- KHÔNG có `::before`/`::after` → widget riêng hoặc custom `paintEvent`.
- KHÔNG có `var()` → `str.format(**tokens)`.
- `QFrame` có `border-radius` phải `setAttribute(Qt.WA_StyledBackground, True)`.
- `QWidget` con kế thừa QSS của cha → dùng `objectName` hoặc `setProperty` + unpolish/polish.
- `currentColor` trong SVG không hoạt động → đọc SVG, replace bằng hex, render qua `QSvgRenderer`.

## Khi xong

Chạy checklist bàn giao ở HANDOFF mục 8 và báo lại từng mục đã pass/chưa.
Nếu có điểm trong thiết kế không rõ, HỎI — đừng đoán, đặc biệt đừng đoán
về hành vi mạng.
```

---

## Mấy câu nên nói thêm khi giao việc

- **"Đọc HANDOFF.md hết rồi hẵng code."** — Model hay nhảy vào code luôn, rồi làm gãy test.
- **"Chạy pytest sau mỗi trang, báo lại con số."** — Bắt nó tự verify thay vì báo "xong".
- **"Nếu không xem được ảnh, đọc hàm JS trong HTML."** — File HTML có đủ thông tin dạng text.
- **"Không sửa test."** — Nói rõ, vì cách nhanh nhất để 69 test xanh là xoá test.

## Cái gì KHÔNG cần đưa

- `plan.md`, `task.md`, `implementation_handoff.md` (43KB + 30KB + 11KB) — đây là tài liệu
  lập kế hoạch cũ, không liên quan redesign, đưa vào chỉ làm loãng context.
- `docs/prototype/` — prototype cũ, đã bị thay bằng `docs/redesign/`.
- `__pycache__/`, `.vscode/`, `config.json` (chứa API key thật).
