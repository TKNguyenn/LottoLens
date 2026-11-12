# LottoLens Gradient — đã duyệt và tích hợp

Mở **[lottolens-gradient.html](lottolens-gradient.html)** bằng browser. File có CSS/JS inline, không tải font hoặc thư viện từ mạng; logo/icon dùng assets chung ở `../assets/`.

## Ý đồ

Giữ nhận diện đen–đỏ / trắng–đỏ và bố cục đã duyệt. Dùng gradient để nối các bề mặt mềm hơn, tập trung vào card kết quả và nút chính; bảng, input và văn bản giữ tương phản rõ ràng.

| Bề mặt | Light | Dark |
|---|---|---|
| Canvas | Trắng/xám với ánh hồng nhẹ | Đen graphite với ánh đỏ ở đầu trang |
| Card | Trắng sang xám hơi tím | Graphite sang đen, viền sáng nhẹ |
| Card kỳ gần nhất | Trắng hồng dịu | Ánh đỏ mận rất nhẹ |
| Nút chính | Đỏ `#D9324C → #C71D38 → #A5122E`, chữ trắng | Đỏ `#FF7385 → #FF4D67 → #F23554`, chữ tối `#18050B` |
| Bóng số | Trắng ngọc, viền và bóng mềm | Graphite, highlight nhẹ |

Không dùng nền chuyển động hoặc glow nhấp nháy. Hiệu ứng được tắt khi browser có `prefers-reduced-motion`.

## Cách review

- **Phẳng / Gradient**: so sánh bề mặt, giữ nguyên trang, theme, trò chơi và sidebar.
- **Nền sáng / Nền tối** hoặc **T**: đổi giữa hai theme. Gõ T trong input không đổi theme.
- Nút panel ở đầu sidebar: 236px ↔ 68px; mở rộng có logo/tên/nút bên phải, thu gọn ẩn logo/tên và căn giữa nút như ảnh Piaz Switch. Rê icon khi thu gọn để xem nhãn.
- Sidebar đủ 7 trang; dropdown trò chơi có các trạng thái trống từ bản mẫu gốc.
- Nội dung là snapshot/mẫu cho thiết kế; các nút tải/AI không gửi request hoặc ghi vào app.

## Dựng lại mẫu

```powershell
& 'C:/Users/kietj/AppData/Local/Programs/Python/Python311/python.exe' docs/redesign/gradient/build_preview.py
```

Builder lấy cấu trúc và nội dung từ `../vietlott-sidebar-toggle.html`, thay branding LottoLens, thêm lớp gradient/công tắc so sánh và cập nhật đầu sidebar. Mọi artifact riêng của bản gradient nằm trong folder này. App PySide6 đã áp dụng gradient cho cả hai theme; công tắc Phẳng/Gradient chỉ là công cụ so sánh trong HTML.

## Kiểm chứng

Đã kiểm tra browser: **7 trang × 2 theme ở 1000px và 1440px**, không tràn ngang; sidebar 236px/68px; Phẳng/Gradient giữ theme/trang/sidebar; logo/assets tải thành công; không có lỗi JavaScript. Kiểm tra thêm heatmap có đủ lớp màu và histogram 10 cột cao 88px sau khi khôi phục block CSS thứ hai của mẫu gốc.

Nút CTA đạt tương phản thấp nhất **4.66:1 ở light** và **5.08:1 ở dark** tại các điểm gradient đã định. Hover ở light được làm tối nhẹ. Chữ ô heatmap light mức 4/5 dùng `#18050B`; mức 5 đạt **4.62:1**, đã kiểm tra trên ảnh Qt render.

Ảnh review: [dark](preview-dark.png), [light](preview-light.png), [sidebar thu gọn](preview-compact.png), [thống kê dark](preview-stats-dark.png).

## Tích hợp Qt native — 2026-11-10

- `app/theme.py`: hai dict token, QSS `str.format`, gradient canvas/rail/topbar/statusbar/card/CTA/badge/callout. Card kỳ gần nhất có ánh đỏ nhẹ riêng; border chuyển sắc. Không thêm chế độ hoặc trường cấu hình mới.
- Các component QPainter hiện có vẽ bóng số 3 điểm màu, icon, nav active, thanh tần suất/histogram. Không dùng WebEngine hoặc thêm dependency. Dùng border/highlight chuyển sắc thay cho shadow effect nặng trên từng card.
- Toggle panel được chuyển vào đầu rail. Cả hai theme giữ animation 220ms và chiều rộng 236/68px, tooltip, phím Space, đảo chiều nhanh, trạng thái trang/input/bộ số. Logo/tên ẩn khi thu gọn. Không lưu trạng thái sidebar.
- Full suite: **69 passed, 23 subtests passed**. `scripts/check_gradient.py`, `scripts/check_sidebar.py`, `scripts/check_redesign.py` pass; kiểm tra trực tiếp pixel gradient/heatmap, tương phản CTA cả hover, không lỗi QSS/QPainter. Native Windows gradient/sidebar và smoke entrypoint pass; không gọi AI/history.
- Ảnh app Windows thật: [mở dark](native-expanded/overview-dark.png), [mở light](native-expanded/overview-light.png), [thu dark](native-compact/overview-dark.png), [thu light](native-compact/overview-light.png). Hai folder chứa đủ 7 trang × 2 theme và 7 ảnh cửa sổ nhỏ 1000×700. Chụp bằng `../tools/capture.py --gradient --native [--collapsed]`, DB/config tạm.
- Không thay lõi, API hợp đồng Desktop, storage, hành vi mạng hoặc tests; 22 file được bảo vệ giữ nguyên hash. Báo cáo backtest incomplete vẫn giữ hợp đồng test hiện có.
- Giới hạn: chưa nghiệm thu thủ công mixed-DPI/nhiều màn hình; không gọi provider live. Qt dùng titlebar Windows và không sao chép browser shadow/glow theo pixel tuyệt đối.

Kế hoạch/checklist: [native-plan.md](native-plan.md). Hồ sơ chuẩn: `../../../implementation_handoff.md`, mục 11.
