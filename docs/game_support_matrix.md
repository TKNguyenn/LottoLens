# Ma trận hỗ trợ — LottoLens V0.2.0

Ngày cập nhật 2026-11-12. Danh mục lấy từ website chính thức Vietlott, không phải danh sách model do AI tạo. “Có code” và “nghiệm thu đầy đủ” là hai trạng thái khác nhau. Cửa sổ phân tích cấu hình được, mặc định 90 kỳ; nhãn 90 trong tên phương pháp là định danh lịch sử, prior Bayes vẫn tương đương 90 kỳ.

| game_id / mode_id | Lịch sử chính thức | Thống kê | Xác suất | Sinh số | Đối chiếu / backtest | Giới hạn còn lại |
|---|---|---|---|---|---|---|
| mega / normal | Có, trang và AJAX kỳ cũ | Có | Hạng giải, Fraction | Đồng đều, tần suất và Bayes 90 kỳ | Có core | Chưa xác minh toàn bộ thời gian hiệu lực luật; tiền lịch sử giữ unknown |
| power / normal | Có, tách 6 số chính/bonus | Có, bonus riêng | Hạng giải, tách Jackpot 2 | Có core | Có core | Jackpot/chia thưởng, thuế và lịch sử hiệu lực luật chưa đầy đủ |
| lotto / normal | Có, tách 5 số chính/số đặc biệt | Có | 5/35 × 1/12, hạng giải | Có core | Có core | Chia Độc Đắc/tiền lịch sử giữ unknown; không giả là tiền cố định mọi kỳ |
| keno / pick1–pick10 | Có, phân trang theo ngày | Có tần suất số chính | Phân phối số lượng trùng | Có | Có mô phỏng số lượng trùng. Chưa hỗ trợ backtest theo hạng giải | Chờ xác minh đầy đủ bảng trả thưởng và giới hạn chia giải |
| keno / chơi bổ sung | Dùng kết quả Keno | Chưa hoàn thiện cho cược phụ | Chưa bật | Chưa bật | Chưa bật | Cần từng luật bổ sung, không dùng công thức pickN thay thế |
| max3d / normal | Có, giữ nhóm giải 2/4/6/8 và số 0 đầu | Tần suất chuỗi | Fraction từng hạng + hợp/không trúng, có hoàn lại | Đồng đều/tần suất/Bayes/AI | Chưa bật | Xác suất sự kiện, chưa tính tiền thưởng khi lặp; AI giữ cap10.000ký tự |
| max3d / Max 3D+ | Dùng kết quả Max 3D | Chưa có phân tích vé hai bộ | Chưa bật | Chưa bật | Chưa bật | Cần luật/vé hai bộ; không đồng nhất với một bộ Max 3D |
| max3dpro / normal | Có, giữ thứ tự nhóm giải | Tần suất chuỗi | Fraction thứ tự/cặp trùng/chồng lấp + hợp/không trúng | Đồng đều/tần suất/Bayes/AI, cặp có thứ tự | Chưa bật | Chưa tính tiền thưởng/EV khi lặp; AI giữ cap10.000ký tự |
| bingo18 / 38 lựa chọn trong selections | Có ba kết quả, có thể lặp; chung mode normal | Tần suất, tổng cơ bản | Enum216, đầy đủ5nhóm/38lựa chọn | Đồng đều/tần suất/Bayes/AI theo nhóm, giới hạn batch hữu hạn | Chưa bật | Chưa backtest/mô phỏng/tiền lịch sử; CLI chưa có flag chọn nhóm |
| Mega/Power/Lotto/Max / chơi bao | Có lịch sử nền của sản phẩm | Phân tích lịch sử nền | Chưa tính vé bao | Chưa bật | Chưa bật | Giá vé/số đơn vị/độ phủ và chồng giải cần engine riêng |

Rule version hiện tại là `observed-2026-11-09`: mô hình quan sát từ nguồn hiện hành, không khẳng định đã chứng minh ngày bắt đầu/kết thúc hiệu lực cho mọi kỳ cũ. `effective_from/effective_to` còn chưa xác minh. Dữ liệu nguồn được gắn `historical_rule_unverified` để tránh khẳng định tiền giải lịch sử chính xác.

Nguồn và các kỳ đã kiểm tra nằm trong `source_audit.md`. GUI T09 đã nối core hiện có; tạo số cho trò tập số có cả đồng đều, tần suất và Bayes 90 kỳ. T09 còn đối chiếu/DPI/dữ liệu lớn; nghiệm thu toàn bộ phạm vi T10/T11 chưa hoàn thành. Dropdown không tự chứng nhận mọi biến thể được hỗ trợ.
