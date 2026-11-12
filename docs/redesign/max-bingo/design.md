# Max 3D / Max 3D Pro / Bingo18 — xác suất và bộ tham khảo

Ngày: 2026-11-11. Trạng thái: **người dùng đã duyệt và đã triển khai**. Kết quả thực tế và các quyết định kỹ thuật xem README.md/implementation-plan.md cùng thư mục; nội dung dưới giữ bản thiết kế đã duyệt.

## Yêu cầu đã xác nhận

- Bổ sung xác suất lý thuyết và tạo bộ tham khảo cho Max 3D, Max 3D Pro và Bingo18.
- Người dùng chọn **đầy đủ các cách chơi Bingo18**, không giới hạn ở số đơn/tổng.
- Max 3D: vé cơ bản một chuỗi `000`–`999`. Max 3D Pro: vé cơ bản hai chuỗi `000`–`999`, giữ thứ tự, chấp nhận hai chuỗi giống nhau.
- Tiếp tục ghi thay đổi vào `implementation_handoff.md`; tài liệu/ảnh liên quan tập trung tại thư mục này.

## Hiện trạng đã đọc

`rules.py` chỉ bật `math_ready` cho nhóm tập số. `generation.py` và `generation_profile` chỉ nhận `kind=set`; nhánh AI dùng chung profile. `domain.py` đã kiểm tra chuỗi ba chữ số nhưng từ chối vé Bingo18. UI tạo vé mẫu bằng số nguyên, giải thích dùng định dạng số nguyên và có thông báo xác suất giống nhau vốn không đúng giữa các lựa chọn Bingo18. Không thể chỉ bật cờ hỗ trợ.

`probability.py` hiện trả phân phối loại trừ nhau cho các trò tập số; Max có các sự kiện hạng giải chồng lấp. `evaluation.py` chưa đối chiếu Max/Bingo. Store đã lưu selections/metadata dạng JSON, nên tính năng này không cần đổi schema hoặc nhân bản lịch sử.

## Cách thực hiện đề xuất

Mở rộng mô hình vé và các hàm hiện có, thêm một mô-đun nhỏ cho luật/công thức riêng nếu cần để tránh nhồi vào UI. Đây là hướng phù hợp với kiến trúc đang dùng: cùng `Ticket`, `Draw`, snapshot và quy trình Lưu. Một bộ máy độc lập sẽ trùng validation/storage; dùng AI tính xác suất không tạo được kết quả xác định để kiểm chứng.

Không đổi mode lịch sử của Bingo18: kiểu dự thưởng là dữ liệu trong `Ticket.selections`. Các lựa chọn cùng đọc ba kết quả đã lưu, dùng chung một lịch cập nhật, không tạo thêm 38 bản lịch sử.

### Giao diện

- Giữ tám trang, theme, sidebar và hợp đồng widget/method Desktop hiện có.
- Bingo18 thêm chọn nhóm chơi: Một số trùng / Hai số trùng / Ba số trùng / Cộng tổng / Lớn–Hòa–Nhỏ. Nhóm Ba số có thêm lựa chọn Ba số bất kỳ.
- Trang Xác suất hiển thị lựa chọn đang xem, xác suất từng kết quả nhận giải và không trúng. Có thể chọn số/tổng/cửa cụ thể để xem, không cần tạo số trước.
- Trang Bộ tham khảo chọn cùng nhóm chơi; generator chỉ tạo vé hợp lệ trong nhóm đó. Hiển thị và giới hạn số bộ khác nhau theo số lựa chọn của nhóm; ví dụ Lớn–Hòa–Nhỏ chỉ có ba vé khác nhau, Ba số bất kỳ chỉ có một.
- Nhóm Ba số có bộ chọn phụ “Số cụ thể / Bất kỳ”: số cụ thể có sáu lựa chọn; Bất kỳ là context cố định chỉ có một vé. Không vừa cho chọn cả bảy vừa áp giới hạn batch bằng một.
- Max giữ nguyên số 0 đầu. Pro hiển thị rõ Bộ 1 / Bộ 2, không sort mất thứ tự.
- Giải thích phân biệt xác suất nền và trọng số theo lịch sử. Không dùng câu “mọi vé đều cùng xác suất” giữa các tổng/cửa Bingo18 hoặc giữa cặp Pro trùng và khác nhau.
- Chuyển Việt/Anh tức thì; cả hai theme, rail thu/mở và cửa sổ nhỏ. Khóa lựa chọn khi worker chạy.

### Danh mục Bingo18

Theo bảng sản phẩm Vietlott SMS:

| Nhóm | Lựa chọn | Số lượng |
| --- | --- | ---: |
| Một số trùng | Chọn 1–6; nhận giải theo xuất hiện đúng 1, 2 hoặc 3 lần | 6 |
| Hai số trùng | Chọn số 1–6 xuất hiện ít nhất hai lần | 6 |
| Ba số trùng | Chọn số 1–6 xuất hiện ba lần; hoặc ba số giống nhau bất kỳ | 7 |
| Cộng tổng | Tổng chính xác 3–18 | 16 |
| Lớn–Hòa–Nhỏ | Nhỏ 3–9; Hòa 10/11; Lớn 12–18 | 3 |

Tổng cộng 38 lựa chọn thuộc năm nhóm. Không tự áp luật Sic Bo hoặc loại trường hợp bộ ba khỏi Lớn/Nhỏ.

### Xác suất

- Tính bằng số nguyên / `Fraction`; định dạng phần trăm chỉ ở tầng hiển thị.
- Bingo18 duyệt toàn bộ `6**3 = 216` kết quả có thứ tự theo giả định ba lần quay công bằng, độc lập. Một predicate luật dùng cho đếm xác suất và đối chiếu fixture, phân biệt xuất hiện đúng một lần với ít nhất một lần.
- Max cần xác minh mô hình lặp giữa các lượt quay từ tài liệu nguồn trước khi bật. Khi mỗi chuỗi có xác suất 1/1000 và các lượt độc lập, tính sự kiện xuất hiện ít nhất một lần trong nhóm; không thay bằng số lượt/1000 khi có khả năng lặp.
- Với Max/Pro phải đọc rõ “trùng một bộ”, “trùng bất kỳ hai bộ” và trường hợp kết quả lặp là một sự kiện hay nhiều tổ hợp nhận giải. Không suy ra predicate hoặc số lần nhận giải chỉ từ tên hạng; đây là phần tra nguồn của implementer, không đẩy sang người dùng và không bật `math_ready` bằng giả định chưa xác minh.
- Pro xử lý riêng cặp khác nhau / cặp giống nhau, đặc biệt đúng / ngược thứ tự, từng nhóm giải và hợp sự kiện của tất cả nhóm. Dùng đếm trạng thái tổ hợp/DP với ba loại kết quả A/B/khác (A/khác cho cặp trùng), tránh duyệt `1000**20` hay mô phỏng để báo xác suất chính xác.
- Xác suất từng hạng Max là xác suất biên, có thể chồng lấp và không bắt buộc tổng bằng 1. Tính riêng xác suất trúng ít nhất một giải và không trúng bằng hợp sự kiện, không lấy tổng các hạng. Giao diện phải nói rõ điều này.
- Tiền thưởng, nếu hiển thị, là theo bảng hiện hành và giả định mệnh giá cơ bản; không suy ra tiền thưởng chính xác cho kỳ lịch sử chưa xác minh thời gian hiệu lực.

### Tạo bộ tham khảo

- Đề xuất mở đủ bốn phương pháp đang có: đồng đều, tần suất, Bayes và AI phân tích lịch sử. ID/phân phối của các trò đã hỗ trợ không đổi.
- Đồng đều lấy mẫu trên vé hợp lệ của nhóm đang chọn. Pro lấy mẫu cặp có thứ tự và cho phép cặp trùng; giữ các bộ tham khảo trong cùng batch không trùng nhau.
- Tần suất/Bayes dùng đúng N kỳ từ cài đặt, validate/sort/cutoff như hiện tại. Max đọc chuỗi trong các nhóm giải; Bingo tính sự kiện ứng với nhóm chơi. Mẫu số và mức nền phải theo đúng đơn vị quan sát; không áp nguyên công thức tập số không hoàn lại cho mọi trò.
- Giữ prior 90 kỳ cho Bayes; công thức và đơn vị quan sát của mô hình mới được ghi trong metadata/giải thích. Trọng số chỉ phục vụ chọn bộ tham khảo, không thay xác suất lý thuyết.
- AI nhận đúng kiểu vé, lịch sử và constraints; kiểm tra output, số bộ, trùng bộ, số 0 đầu, thứ tự và loại chơi tại máy. Bật AI không cho phép tự gọi mạng, retry, lưu dở hoặc ghi kết quả vào lịch sử. Giữ giới hạn input 10.000 ký tự; quá dài thì chặn trước HTTP.
- Thêm tham số cuối tùy chọn `play_context=None` xuyên suốt `generation_profile`, `generate`, `explain_ticket`, `build_generation_request`, `generate_with_ai`, `parse_tickets`. Caller cũ giữ hành vi mặc định; context chỉ chứa giá trị whitelist. Parser kiểm tra kiểu chơi đúng context đã yêu cầu, không để AI đổi nhóm. Chuẩn hóa và khóa chống trùng giữ thứ tự Pro, không sort cặp như vé tập số.
- Kiểm tra ngân sách input AI Max bằng fixture N=90 trước khi khẳng định dùng được ở mặc định. Chọn biểu diễn compact vẫn giữ đủ N kỳ, nhóm giải và thứ tự; bỏ phần profile dẫn xuất nếu có thể tái tính. Nếu vẫn quá 10.000 ký tự thì thông báo rõ trước HTTP, không cắt N, không nâng cap. Bốn phương pháp được nối vào UI nhưng AI chỉ chạy khi đầu vào đáp ứng giới hạn hiện có.
- Snapshot, metadata và lưu bộ tham khảo tiếp tục qua API Store hiện có. Không lưu key.

## Phạm vi sửa và phần giữ nguyên

- Cần mở rộng đúng chức năng mới trong `rules.py`, `domain.py`, `probability.py`, `generation.py`, `ai_generation.py`; có thể thêm mô-đun luật dùng chung. Đây là mở rộng lõi theo yêu cầu mới, không còn chỉ sửa UI.
- UI/i18n/components cần hỗ trợ nhãn vé và lựa chọn kiểu chơi; tránh đưa thuật toán vào widget.
- Chưa mở rộng backtest/mô phỏng hoặc mua vé. Nếu cần helper đối chiếu sự kiện để chứng minh công thức thì tách helper đó; không tự mở tính năng Kiểm chứng cho các trò mới.
- Không sửa `tests/`, `main.py`, AI transport, cài đặt key, schema/storage, nguồn tải hoặc lịch Windows. CLI cũ giữ nguyên giao diện; chưa thêm flag chọn các kiểu Bingo18.
- Không đổi rule_version/mode lịch sử khiến dữ liệu đang lưu biến mất. Chụp snapshot luật/metadata mới khi lưu bộ mới; dữ liệu cũ giữ nguyên.

## Kiểm tra bắt buộc

- Chạy nguyên bộ `tests/`; không sửa test để qua.
- Thêm checks ở `scripts/`: đủ 38 lựa chọn, enum 216 kết quả Bingo độc lập để đối chiếu; tổng phân phối loại trừ nhau bằng 1; xác suất Lớn/Nhỏ đối xứng; ba số bất kỳ bằng hợp sáu bộ ba cụ thể.
- Max/Pro kiểm tra chuỗi 000/007/999, cặp đảo thứ tự, cặp trùng, chồng giải, công thức không trúng và xác suất hợp. Dùng không gian rút gọn với brute-force độc lập để kiểm chứng DP; kiểm tra giới hạn [0,1] và không cộng xác suất biên thành tổng.
- Mỗi phương pháp: vé hợp lệ, đủ số bộ, không trùng, thiếu N bị chặn, N thay đổi có tác dụng, provenance và snapshot đúng, baseline của các trò cũ không đổi.
- AI dùng transport mock, xác minh một lần gọi, cancel/incomplete/JSON sai không lưu, không rò key; không gọi provider tính phí khi kiểm tra.
- UI: đổi trò/nhóm, số bộ vượt số lựa chọn, lưu/mở lại, VI/EN và light/dark, worker lock/cancel/close; lịch sử cũ không bị chuyển mode/xóa.

## Nguồn và phần phải xác minh thêm

- https://info.vietlott-sms.vn/hdsd/game_3d.html — vé một bộ và các nhóm giải Max.
- https://info.vietlott-sms.vn/hdsd/game_3dp.html — hai bộ có thứ tự, cặp giống nhau, nhiều giải đồng thời.
- https://info.vietlott-sms.vn/game_bingo.html — năm nhóm và đầy đủ 38 lựa chọn Bingo18.
- https://vietlott.vn/vi/choi/bingo/cach-choi — trang sản phẩm nêu 38 lựa chọn.

Đã đọc nội dung các trang Vietlott SMS qua web ngày 2026-11-11. Công cụ web bị 403 khi mở trực tiếp các trang hướng dẫn/PDF trên vietlott.vn; HTTP 200 từ lượt requests riêng chưa chứng minh nội dung đó là thể lệ đầy đủ. Trong triển khai phải lấy/đọc được bằng chứng cơ chế quay Max và lưu nguồn cụ thể trước khi khẳng định mô hình lý thuyết tương ứng. Không ghi “đã xác minh” cho phần chưa đọc được.

## Trạng thái

Người dùng duyệt bản thiết kế ngày2026-11-11. Đã triển khai và kiểm tra RED→GREEN, chưa gọi provider trả phí hoặc thay dữ liệu người dùng. Builder check độc lập trước triển khai đã bổ sung predicate Max, context/parser và ngân sách input. Bằng chứng luật Max đã được giải quyết bằng thể lệ quay2026 và luật dự thưởng/demo chính thức, xem source-evidence.md. Quyết định triển khai: dùng công thức đóng thay DP cho các sự kiện cặp và tách mục Ba số bất kỳ khỏi Triple trong combo (vẫn năm nhóm luật/38lựa chọn), tránh context batch nhập nhằng.
