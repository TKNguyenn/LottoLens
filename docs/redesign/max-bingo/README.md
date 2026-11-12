# Max 3D / Pro / Bingo18

Triển khai ngày 2026-11-11 theo [thiết kế đã duyệt](design.md). [Nguồn và bằng chứng luật](source-evidence.md), [kế hoạch và kết quả](implementation-plan.md), ảnh Windows ở [reviews/](reviews/).

## Sử dụng

- Chọn Max 3D, Max 3D Pro hoặc Bingo18 trên thanh trò chơi.
- Trang **Xác suất**: Max nhập chuỗi ba chữ số; Pro nhập Bộ1/Bộ2, giữ thứ tự, được chọn cặp trùng. Bingo chọn cách chơi và một lựa chọn để xem xác suất. Các ô tương ứng ở trang Bộ tham khảo được đồng bộ.
- Trang **Bộ tham khảo**: chọn phương pháp và số bộ. Nhóm chơi Bingo quyết định phạm vi sinh; ô “Vé đang xem xác suất” chỉ chọn ví dụ xem odds, không ép tất cả bộ được tạo bằng ví dụ đó.
- Đồng đều không cần đủ N kỳ. Tần suất/Bayes/AI cần đúng N kỳ đã đặt trong Cài đặt. Bấm Tạo rồi điền mã kỳ dự định chơi và Lưu nếu muốn giữ kết quả.
- Bingo có38 lựa chọn: single6, double6, triple6, any_triple1, sum16, size3. UI tách “Ba số bất kỳ” thành mục riêng để làm rõ batch này chỉ có một vé. Lớn–Hòa–Nhỏ chỉ tạo tối đa3 bộ khác nhau; Tổng tối đa16.

## Mô hình

`gameplay.py` chứa lựa chọn hợp lệ và xác suất chính xác `Fraction`. Lịch sử/rule_version/mode/Store giữ nguyên; kiểu vé Bingo nằm trong selections, không sinh thêm38 lịch sử hoặc lịch tải.

Bingo dùng216 kết quả có thứ tự theo giả định ba lần quay công bằng độc lập. Một số trùng có ba hạng xuất hiện đúng1/2/3lần; Hai số trùng là ít nhất2; ba số giống nhau gồm6 lựa chọn cụ thể và một lựa chọn bất kỳ; tổng3–18; Nhỏ3–9/Hòa10–11/Lớn12–18. Không loại bộ ba khỏi Nhỏ/Lớn.

Max/Pro dùng quay công bằng độc lập có hoàn lại, đã đối chiếu thể lệ quay July2026. Với q=999/1000, xác suất một chuỗi xuất hiện trong m lượt là1−q^m. Cặp khác nhau A/B cùng xuất hiện là1−2q^m+(998/1000)^m; cặp A/A cần ít nhất2 lượt, xác suất1−q^m−m(1/1000)q^(m−1). Dùng công thức đóng chính xác thay DP vì đã đủ biểu diễn các sự kiện yêu cầu.

Hạng đặc biệt Pro đúng thứ tự và ngược thứ tự có xác suất1/1.000.000; với cặp trùng, hai sự kiện này trùng nhau. Xác suất từng hạng là xác suất biên, không phải các phần của một phân phối loại trừ nhau. Có dòng hợp “Trúng ít nhất một giải” và dòng Không trúng riêng; không cộng các hạng. Phân số dài được rút gọn chính xác, cột có thể elide nhưng tooltip giữ đủ giá trị.

Không hiển thị tiền thưởng/EV hoặc tự mở Kiểm chứng/Mô phỏng Max/Bingo: chưa xác minh đầy đủ cách nhân tiền khi kết quả lặp. Nguồn chứng minh event không tự chứng minh số tiền nhận.

## Sinh và AI

Max đọc20 kết quả/kỳ, đếm lần xuất hiện của chuỗi; Bingo đếm số kỳ trúng sự kiện lựa chọn. Bayes giữ prior90kỳ; phương pháp mới dùng đúng đơn vị quan sát. Các trò tập số đi qua nhánh cũ, seeded baseline không đổi.

API liên quan nhận thêm tham số cuối `play_context=None`; Bingo mặc định single, hoặc double/triple/any_triple/sum/size. AI phải trả đúng play và kiểu dữ liệu; chuỗi Max không đổi thành số nguyên, cặp Pro không sort. Count vượt số vé khác nhau bị từ chối.

AI Max encode20chuỗi/kỳ thành60ký tự cố định, kèm thứ tự/size nhóm2/4/6/8, giữ đủ N kỳ và ID kỳ. Không nhét lại1000tần suất dẫn xuất vào input. N90 được kiểm tra dưới10.000ký tự; input dài vẫn bị chặn trước HTTP, không tự cắt N hay tăng cap. Request một lần, High/no-web, không retry; kết quả chỉ được Lưu qua suggestions khi người dùng bấm, không ghi lịch sử hoặc key.

## Kiểm tra

- `scripts/check_max_bingo_core.py`:38vé, strict validation, enum216, các xác suất số/tổng/cửa biết trước, brute-force không gian thu nhỏ đối chiếu công thức cặp, union/chồng lấp.
- `scripts/check_max_bingo_generation.py`: ba phương pháp local ×mọi context; số bộ hợp lệ/khác nhau, N/cutoff/prior, parser Pro/context, request90đủ dữ liệu, cap/no-HTTP khi thiếu/quá lớn, AI mock một lần và metadata không chứa key.
- `scripts/check_max_bingo_ui.py`: nối Desktop→AI mock, chọn/sync mẫu, dynamic count, tạo/Lưu, VI/EN/theme/cửa sổ nhỏ, khóa input worker, không startup HTTP/AI.
- `capture.py`:26ảnh Windows với DB tạm, N90 giả lập, mock chặn mạng/AI; không đăng ký lịch hoặc xóa dữ liệu thật.

CLI cũ không có flag chọn cách chơi Bingo; không sửa main.py trong đợt này. Các kiểm tra provider dùng mock, không gọi dịch vụ trả phí. Chưa nghiệm thu mixed-DPI/nhiều màn hình hoặc tiền thưởng lịch sử.
