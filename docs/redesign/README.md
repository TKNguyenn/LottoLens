# LottoLens — tất cả tài liệu và bản review giao diện

Các mẫu HTML, ảnh, assets và công cụ thiết kế được gom trong thư mục này. Giao diện Python đang chạy vẫn ở `app/`; hồ sơ triển khai chuẩn là `../../implementation_handoff.md`.

## Thiết kế hiện hành — đã triển khai

**[LottoLens Gradient](gradient/lottolens-gradient.html)** — đã được duyệt và áp dụng vào app PySide6: đủ 7 trang, 2 theme đen–đỏ/trắng–đỏ, sidebar thu gọn kiểu Piaz Switch. Mẫu HTML giữ nút **Phẳng / Gradient** để so sánh; app dùng gradient cho cả hai theme.

Toàn bộ artifact riêng của theme này ở **[gradient/](gradient/README.md)**: HTML, script dựng mẫu, ảnh browser, ảnh Qt native mở/thu sidebar, kế hoạch và kết quả kiểm chứng.

**[Cài đặt và ngôn ngữ trực tiếp](settings/README.md)** — trang thứ 8 đã bổ sung: Việt/Anh đổi ngay, số kỳ tải riêng cho từng trò (mặc định 100, giữ toàn bộ lịch sử), phần giới thiệu và GitHub chờ URL. Kế hoạch, công cụ chụp và ảnh Windows mới nằm chung trong `settings/`.

Trang này có thêm **Số kỳ gần nhất để phân tích** (mặc định90), áp dụng thật cho tổng quan/tạo số/AI/backtest, tách khỏi số kỳ tải. [Ảnh N120](settings/reviews/analysis-window/settings-vi-dark-120.png), [kế hoạch và phạm vi ngoại lệ core được duyệt](settings/analysis-window-plan.md).

**Bổ sung 2026-11-11:** [đồng bộ tăng dần, giới hạn lịch sử và lịch Windows từng trò](settings/README.md). Công tắc +giờ UTC+7 chạy cả app đóng khi user đăng nhập/máy bật, defaultoff; thêm/xóa lịch sử atomic, giữ snapshot đã lưu. [Ảnh cài đặt mới](settings/reviews/daily-sync/settings-vi-dark-expanded.png), [kế hoạch](settings/incremental-sync-plan.md).

## Hướng dẫn sử dụng — đã duyệt và triển khai

- [Hướng dẫn sử dụng lần đầu](onboarding/lottolens-onboarding.html). Đã tích hợp thành popup Qt native, Chính sách → Hướng dẫn 8 bước → Trợ giúp. Bước AI có Tải danh sách model / Fetch models, chọn model và test. Ảnh WebP lossless 3×, copy Việt/Anh và công cụ tạo ảnh nằm chung trong `onboarding/`. File HTML tiếp tục mở offline để review, dùng **T** đổi theme, **L** đổi ngôn ngữ và **Mô phỏng lần đầu** để chạy lại luồng.

## Bản đã duyệt và triển khai

- [Thiết kế gốc đủ 7 trang](vietlott-redesign.html).
- [Mẫu sidebar thu gọn đã duyệt](vietlott-sidebar-toggle.html).
- [Handoff kỹ thuật và hợp đồng API](HANDOFF.md).
- [Kết quả triển khai PySide6](IMPLEMENTATION.md).
- [Kế hoạch triển khai UI](implementation-plan.md).
- [Ghi chú thiết kế/asset ban đầu](reference-notes.md) — tài liệu lịch sử; các mục “chưa làm” trong đó không phản ánh trạng thái hiện tại.

Tên Vietlott trong filename các bản gốc được giữ để không làm đứt đường dẫn tham chiếu lịch sử. App và bản gradient mới dùng tên LottoLens.

## Tổ chức file

```text
docs/redesign/
  README.md                        chỉ mục này
  vietlott-redesign.html            bản thiết kế gốc
  vietlott-sidebar-toggle.html      mẫu sidebar đã duyệt
  HANDOFF.md / IMPLEMENTATION.md    tài liệu kỹ thuật
  implementation-plan.md           kế hoạch UI
  reference-notes.md / PROMPT.md    tài liệu tham chiếu gốc
  assets/                          logo/icon dùng chung; app đang tham chiếu
  settings/                        cài đặt, live VI/EN, kế hoạch và ảnh native
  max-bingo/                       xác suất/bộ tham khảo Max/Pro/Bingo18, nguồn và ảnh native
  reviews/
    native-ui/                     ảnh Qt 7 trang/2 theme
    native-sidebar/                ảnh Qt sidebar đã tích hợp
    sidebar-html/                  ảnh review mẫu HTML sidebar
  tools/
    build_sidebar_preview.py       dựng lại mẫu sidebar
    capture.py                     chụp app Qt trên DB/config tạm
  gradient/
    lottolens-gradient.html         mở file này để review theme mới
    build_preview.py               dựng HTML từ mẫu sidebar đã duyệt
    README.md                      ý đồ, cách xem và kiểm chứng
    preview-*.png                  ảnh theme mới
    native-plan.md                 kế hoạch tích hợp và checklist
    native-expanded/               ảnh app Qt Windows, sidebar mở
    native-compact/                ảnh app Qt Windows, sidebar thu
```

`preview-hero.png` và `preview-dark.png` ở gốc là ảnh tham chiếu của thiết kế ban đầu. `.redesign-work/` ở project chỉ giữ backup/hash kỹ thuật; các artifact review đã chuyển vào đây. Không chuyển hoặc đổi đường dẫn database/config của app.
