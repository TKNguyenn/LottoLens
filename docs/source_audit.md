# Khảo sát nguồn — 2026-11-09

## Những gì đã đọc trực tiếp

Trang chủ `https://vietlott.vn/` và trang kết quả/hướng dẫn của bảy sản phẩm trả HTTP 200 trong lần khảo sát. Đây là đọc nguồn công khai; không gọi dịch vụ Vilao.

| Trò | Trang kết quả chính thức | Hướng dẫn chính thức |
|---|---|---|
| Mega | https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/645 | https://vietlott.vn/vi/choi/mega-6-45/cach-choi |
| Power | https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/655 | https://vietlott.vn/vi/choi/power-6-55/cach-choi |
| Lotto | https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/535 | https://vietlott.vn/vi/choi/lotto535/gioi-thieu-san-pham-535 |
| Keno | https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/winning-number-keno | https://vietlott.vn/vi/choi/keno/cach-choi |
| Max 3D | https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/max-3d | https://vietlott.vn/vi/choi/max3d/cach-choi |
| Max 3D Pro | https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/max-3dpro | https://vietlott.vn/vi/choi/max3dpro/cach-choi |
| Bingo18 | https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/winning-number-bingo18 | https://vietlott.vn/vi/choi/bingo/cach-choi |

Lotto giới thiệu ghi rõ chọn 5 số trong 01–35, một số đặc biệt trong 01–12 và đơn vị dự thưởng 10.000 VND. Mega/Power có bảng hạng giải ngay trang kết quả; các bảng này không tự chứng minh giá trị giải hoặc ngày hiệu lực cho mọi năm lịch sử.

## Cách tải đã kiểm tra

- Mega/Power/Lotto/Max/Max Pro: đọc kết quả trang đầu, theo nút kỳ trước và gọi cùng AJAX proxy công khai mà trang sử dụng. Proxy/key được đọc từ nội dung trang, không đoán mã kỳ giảm dần hoặc endpoint ngoài nguồn.
- Keno/Bingo: dùng bảng kết quả và AJAX phân trang. Phải lấy số dòng trả về từ trang 0 rồi truyền `TotalRow` cho trang sau; nếu luôn truyền 0 sẽ có thể báo không có kết quả dù vẫn còn kỳ.
- Keno cần ngày để tìm lịch sử đúng phạm vi. Bộ lọc “Toàn bộ” của chẵn/lẻ, lớn/nhỏ có giá trị 2 trong nguồn khảo sát. Không dùng -1 vì đó là một điều kiện lọc riêng.
- Nguồn có thể sinh kỳ mới trong lúc tải. Code gộp theo mã kỳ, sắp lại trước khi áp dụng limit; không nối kỳ vừa xuất hiện vào cuối danh sách cũ.
- Trang Keno thông báo tìm kiếm trong vòng 6 tháng. Đây là giới hạn nguồn đã thấy, chưa có bằng chứng toàn bộ lịch sử từ ngày phát hành.
- `draw_at_utc` của nguồn chỉ có ngày là một bucket thứ tự với `payload.time_precision=date`, không phải giờ quay đã xác minh. `published_at_utc` để None.

## Dữ liệu và bằng chứng kiểm tra

Lần tích hợp đã lấy 100 kỳ Mega liên tiếp #01487–#01586. Có 600 quan sát số chính trong thống kê, sinh được 5 vé hợp lệ và chạy 10 kỳ backtest sau warm-up 90 với 200 baseline. Kết quả chỉ là thăm dò.

Đã kiểm tra thêm các mẫu live: Mega #01586–#01584; Power #01421–#01419; Lotto #00997–#00995; Max #01155–#01153; Max Pro #00802–#00800; Keno 12 kỳ liên tiếp #0302349–#0302338; Bingo18 12 kỳ liên tiếp #0195352–#0195341. Những mã kỳ trên là snapshot của lần kiểm tra, không phải cam kết “mới nhất” khi đọc tài liệu sau này.

`tests/fixtures/` lưu một số HTML thật phục vụ regression. `fixtures/manifest.json` ghi hash và nguồn cho các fixture đó. Cache của lần chạy thật lưu cả response gốc và HTML parser thực đọc; `raw_sha256` của từng Draw phải tìm được file `.bin` cùng hash. Trong database kiểm tra ban đầu đã tái dựng 99 fragment parser từ chính AJAX JSON đã lưu để khôi phục liên kết bằng chứng, không đổi bộ số lịch sử.

## Nguồn dùng cho mô phỏng và kiểm chứng

- Keno dùng bảng trùng số theo từng bậc tại Điều 6 của [thể lệ quay số](https://media.vietlott.vn/main/08.2019/cms/game/the-le-quay-so-keno.pdf). Bậc 8–10 có hạng trùng 0 số. Giới hạn trả thưởng theo kỳ nằm trong [cơ cấu giải công bố](https://vietlott.vn/vi/choi/keno/gioi-thieu-san-pham-keno).
- Max 3D và Max 3D Pro dùng nhóm kết quả và điều kiện trúng trong [đối chiếu nguồn chính thức](redesign/max-bingo/source-evidence.md), gồm thứ tự giải đặc biệt, cặp giống nhau và các hạng chồng lấp của Pro.
- Bingo18 dùng ba kết quả quay và điều kiện theo lựa chọn. [Kỳ #0182241](https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/view-detail-bingo18-result?id=0182241&nocatche=1) minh họa cách xác định số lần xuất hiện, cửa tổng và Lớn–Hòa–Nhỏ.

## Chưa xác minh

- Toàn bộ thời gian hiệu lực của từng phiên bản luật, toàn bộ lịch sử của bảy sản phẩm và mọi biến thể/chơi bao.
- Mốc công bố lịch sử và việc dữ liệu đã có sẵn trước mỗi kỳ trong quá khứ.
- Số tiền thực trả khi Max/Pro lặp kết quả, giới hạn chia giải lịch sử của Keno và tiền thưởng lịch sử Bingo18. Các phép thử đếm sự kiện trúng theo mô hình.
- Khả năng endpoint còn giữ cùng cấu trúc trong những lần chạy sau; parser lỗi phải dừng batch và giữ DB cũ.

Không có lời xác nhận rằng đã khảo sát xong toàn bộ T01 hoặc đạt T10.
