# Redesign UX/UI — Vietlott Desktop

Ngày 2026-11-10. Đây là **đề xuất thiết kế để review**, chưa sửa code app.

## Mở gì để xem

`vietlott-redesign.html` — mở bằng trình duyệt (Chrome/Edge). File tự chứa, không cần mạng.
Bấm `T` hoặc nút **Nền tối** để đổi theme; click sidebar để đổi trang; click dropdown trò chơi để đổi game.

## Nội dung

| Mục | Nội dung |
|---|---|
| 01 | Mockup tương tác — đủ 7 trang, số liệu thật từ `history.sqlite3` (Mega & Power 100 kỳ) |
| 02 | Trước/sau — 6 cặp ảnh, "trước" là app thật chụp bằng `w.grab()` |
| 03 | **10 mẫu icon do AI render** — lọc theo nhóm, bấm ★ để chọn, có hàng thử 32px nền tối/sáng |
| 04 | Logo vector (3 phương án) + bộ 32 icon 24px + hàng thử kích thước |
| 05 | Design system — token màu 2 theme, kiểu chữ, component, nhịp bố cục |
| 06 | Audit 19 vấn đề + bảng map CSS → QSS + thứ tự implement |

## Theme

- **Sáng:** nền `#FFFFFF` / page `#FAFAFA`, nhấn `#C81E33`, hover `#A8162A`
- **Tối:** nền `#0F0F13` / page `#06060A`, nhấn `#FF3B4E` (nâng sáng để đạt AA), chữ trên nút đỏ dùng `#14050A`
- Nhấn phụ: vàng jackpot `#A9761D`/`#F2C05C`, xanh xác nhận `#0F7A57`/`#34D399`, hổ phách cảnh báo

## 10 mẫu icon AI — chọn mẫu nào?

| # | Tên | Nhóm | Ghi chú |
|---|---|---|---|
| 01 | V + bóng 3D | bóng số | Nền trong suốt thật, dùng được cả 2 theme. **Đề xuất chính** |
| 02 | Bóng xếp vòng cung | bóng số | Hợp dark mode nhất, có quỹ đạo đỏ |
| 03 | Bóng phẳng tối giản | bóng số | Sắc nét nhất ở 16px |
| 04 | Đường phân phối neon | dữ liệu | Thiên "phân tích", ít liên tưởng xổ số |
| 05 | Huy hiệu tròn | bóng số | Đọc như con dấu/medal, đơn giản |
| 06 | Chùm 6 bóng | bóng số | Gợi đúng luật Mega 6/45 nhất |
| 07 | Vé số + cỏ may mắn | may mắn | Rõ "vé số" nhất, nền đỏ |
| 08 | Móng ngựa + bóng đỏ | may mắn | Sang, tương phản mạnh, nền đen |
| 09 | Xu vàng + bóng | may mắn | Tài lộc, nhưng hơi "casino" |
| 10 | Cỏ bốn lá phẳng | may mắn | Nhẹ nhàng, không khí cờ bạc |

Đã kiểm tra thật: **06 và 09 mất chi tiết dưới 32px** — nếu chọn thì cần bản đơn giản hoá riêng cho taskbar, hoặc chỉ dùng cho shortcut/Start menu.

## Assets

`assets/` — logo vector + icon tự vẽ:

- `logo-a-v-ball.svg` / `logo-a-512.png` / `logo-a-1024.png` — phương án đề xuất
- `logo-b-three-balls.svg`, `logo-c-frame-pulse.svg` — hai phương án thay thế
- `vietlott-desktop.ico` — 7 kích thước (16/24/32/48/64/128/256), header đã verify
- `icons-sprite.svg` — 32 `<symbol>` để nhúng một lần
- `icon-*.svg` — từng icon rời, `stroke="currentColor"` nên đổi màu theo theme

`assets/generated/` — 10 mẫu AI đã làm sạch:

- `NN-<tên>.png` (512×512), `NN-<tên>@1024.png`, `NN-<tên>.ico` (7 size)
- `_contact-sheet.png` — bảng so sánh kèm hàng 16/24/32px và dải nền tối
- `_taskbar-dark-32px.png` — kiểm tra taskbar tối

Mọi file AI đã cắt viền ngoài ~7.5% (bỏ halo/checkerboard của model), mask squircle bán kính 23.5% hoặc giữ alpha gốc nếu model đã xuất nền trong suốt, rồi resize LANCZOS.

## Chưa làm (chờ chốt)

1. Chưa sửa `app/ui.py` hay `app/widgets.py`.
2. Chưa viết `app/theme.py` sinh QSS từ token.
3. Chưa chốt phương án logo / icon — đang chờ bạn chọn.
