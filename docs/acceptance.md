# Acceptance — 2026-11-09, revision 1.2

## Người dùng đã xác nhận

- Desktop Vietlott cho các trò; lịch sử, thống kê, xác suất, tạo/lưu và kiểm chứng bộ số.
- Bắt đầu code trong thư mục chỉ định.
- Vilao base URL/model, ba trường JSON, Responses/streaming; không probe lại capability web search.
- Phản hồi mới: bố cục còn lại ổn; bổ sung xác suất–thống kê vào tạo số, Test model ở AI/cấu hình và điền nguồn. Gate duyệt bố cục T02 đã đạt.

## Đã triển khai theo phản hồi

`python main.py` mở GUI thật; `preview` giữ prototype riêng. Bayes 90 kỳ tạo bộ tham khảo từ lịch sử, giải thích trọng số và odds. Test model chạy request ngắn Responses streaming khi bấm; web search riêng, tự kèm nguồn. Link kết quả/thể lệ Vietlott theo trò đang chọn.

GUI nối core/SQLite/worker. Test cục bộ 60/60 pass, Qt Windows native dùng DB kiểm tra 100 kỳ Mega để tạo5 bộ, mở7 trang và chụp ảnh. Xem `test_evidence.md`. Không gọi Vilao thật; không coi mock transport là nghiệm thu provider.

## Còn mở

Chưa có xác nhận người dùng sau khi dùng GUI bản mới, chưa nghiệm thu toàn bộ trò/biến thể, dữ liệu dài, DPI150%/keyboard/screen reader hoặc packaged build. T09 còn IN_PROGRESS; T10–T12 chưa hoàn thành. Không có EXE/installer.


## Revision1.3

Theo yêu cầu mới, đã thêm phương pháp AI phân tích 90 kỳ và giải thích/đổi nhãn Kỳ dự định chơi.69 test cục bộ và render Windows native pass; API chỉ giả lập, chưa nghiệm thu provider thật hoặc khả năng dự đoán. Các giới hạn sản phẩm và T09–T12 giữ nguyên.
