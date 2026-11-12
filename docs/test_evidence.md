# Evidence — checkpoint 0.1.0-dev

Ngày 2026-11-09. Runtime Windows, Python 3.11.9 64-bit, PySide6 6.11.2 đã có sẵn; không cài dependency mới.

## Unit và regression

Đã chạy từ thư mục gốc:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
python main.py self-check
```

Kết quả suite revision 1.1: **47 tests, 0 failures, exit code 0**. Suite hiện tại revision 1.2 là 60 tests, xem phần bổ sung cuối. Self-check math/import exit 0, không gọi website hoặc provider.

Phạm vi: domain/validation, xác suất Fraction, Power bonus, Lotto special, Wilson/Holm, generator, CSV/parser fixture thật, revision/snapshot/migration SQLite, backtest leakage/holdout/baseline và SSE/JSON/citations/error. Test API chỉ dùng mock transport và sự kiện cục bộ; không phải probe Vilao.

## Public source và tích hợp thật

`work/verify_vietlott.py` trong workspace chat đã chạy thành công, exit code 0. Chỉ request host Vietlott, không có request Vilao.

| Trò | Số kỳ trong lần xác minh cuối | Mã kỳ |
|---|---:|---|
| mega | 3 | 01586 đến 01584 |
| power | 3 | 01421 đến 01419 |
| lotto | 3 | 00997 đến 00995 |
| keno | 12 | 0302349 đến 0302338 |
| max3d | 3 | 01155 đến 01153 |
| max3dpro | 3 | 00802 đến 00800 |
| bingo18 | 12 | 0195352 đến 0195341 |

Tích hợp Mega: **100 kỳ**, #01487–#01586, thống kê 600 số chính, tạo 5 vé; backtest 10 kỳ đích với 200 baseline hoàn tất trong khoảng 1.144 giây trên máy này. Đây là phép đo core ở cấu hình/dữ liệu nêu trên, không phải cam kết hiệu năng cho toàn bộ lịch sử hoặc GUI.

Backtest là **exploratory_only** vì chỉ có 10 kỳ sau warm-up. Không báo lợi thế, không khẳng định lợi nhuận. Snapshot input đã lưu/đọc lại đúng; mọi raw_sha256 của 100 kỳ tìm được cache tương ứng. 99 fragment cũ trong cache kiểm tra được tái dựng từ chính raw JSON đã lưu trước bản sửa provenance; không sửa bộ số.

## Prototype

Đã chạy cả render offscreen và Qt Windows native:

```powershell
python main.py preview --screenshot "duong-dan-anh.png"
```

Exit code 0; chụp được tổng quan, xác suất và AI; kiểm tra chuyển cả bảy trang. Đã xem ảnh trực tiếp. Offscreen ban đầu không có font Windows trong font database; prototype nạp font Segoe UI khi cần và ảnh sau sửa đọc được tiếng Việt. Ảnh native được lưu trong outputs của chat.

Ở checkpoint 1.1 chưa có nghiệm thu người dùng. Sang 1.2, người dùng đã duyệt bố cục và GUI thật đã nối worker/core. Prototype vẫn giữ riêng; chưa nghiệm thu DPI 150%/screen reader đầy đủ.

## Review

Có hai lượt read-only review core theo skill requesting-code-review; agent chính tái hiện bằng test và sửa các lỗi provenance, incomplete response, snapshot input, payout unverified, collision snapshot rỗng và backup handle Windows. Suite cuối pass sau các sửa đó. Không có Git/PR/commit ở thư mục mới này.

## Chưa kiểm tra hoặc chưa triển khai

- Vilao live không được gọi theo yêu cầu người dùng; mặc định endpoint/model/streaming đã có trong request builder.
- Nguồn live không chứng minh toàn bộ lịch sử, mọi biến thể hoặc ngày hiệu lực luật đã xác minh.
- GUI/worker đã nối ở 1.2; nghiệm thu mọi biến thể, installer/frozen/AV gate vẫn chưa thực hiện.
- Không có upload, phát hành, mua vé hoặc giao dịch tài chính.


## Bổ sung revision 1.2 — GUI và phản hồi người dùng

Lệnh full suite và self-check nêu trên đã chạy lại sau bản sửa cuối: **60 tests, 0 failures, exit code0**, self-check pass. Thêm test Bayes shrinkage/prior/cửa sổ90, manual model test không web tool, và10 integration Qt/SQLite/transport giả lập. Có red→green cho GUI còn thiếu, lỗi callback khi nguồn không hợp lệ và mất báo cáo incomplete sau cancel.

Qt Windows native (`application.platformName() == "windows"`) mở app với **bản sao DB kiểm tra 100 kỳ Mega** #01487–#01586, dùng90 kỳ tới#01586 để tạo5 bộ Bayes; chuyển được7 trang. Ảnh `bo-so-tham-khao.png` và `ai-va-cau-hinh.png` trong outputs checkpoint chat đã được xem. Dùng config tạm key rỗng; config thật không được sửa hoặc đưa vào ảnh. CLI generate mặc định Bayes và legacy preview sau tách widget helper đều exit0.

Các integration mới kiểm tra: source theo7 trò, DB trống, missing history, create/save method+snapshot, sync hợp lệ, invalid batch giữ DB nguyên và báo lỗi, Test model Responses streaming không tool, web search kèm link chính thức, lỗi provider trở lại idle, hủy/đóng tải không commit, simulation/backtest hủy vẫn hiện/saved incomplete với số mẫu thực chạy. Không dùng mạng hoặc paid provider trong test.

Reviewer read-only phát hiện mất report incomplete khi hủy; đã sửa và chạy lại test. Lượt review cuối xác nhận60 tests pass và không có lỗi quan trọng còn lại trong thay đổi này.

Giới hạn: chưa live Vilao, chưa network cancel thật; chưa full DPI150%/keyboard/screen reader, dữ liệu dài hoặc biến thể chưa đủ luật. Không dùng kết quả Bayes/report thăm dò để tuyên bố tăng xác suất trúng. GUI thật vẫn chưa phải sản phẩm cuối đã nghiệm thu toàn bộ.


## Bổ sung revision 1.3 — AI đề xuất bộ số

Full suite sau sửa cuối: `python -m unittest discover -s tests -p "test_*.py"` → **69 tests, 0 failures, exit0**. Self-check pass. Thêm 4 test AI generation và 5 integration UI: đúng cửa sổ90, Responses/stream không web tool, input không key, schema/miền số/trùng bộ/Lotto special, context Keno dưới10.000 ký tự, không retry, output lỗi/cancel không cho lưu, metadata model và snapshot, không backtest AI hàng loạt. Có kiểm tra delta xuất hiện trên trang tạo số trước response cuối.

Reviewer read-only tìm được sai lệch snapshot nếu một tiến trình khác sửa lịch sử sau khi GUI đã đọc. Đã viết regression tái hiện cho local và AI (red), sửa Store.snapshot nhận captured draws và hai caller (green). Snapshot giờ bám đúng dữ liệu đã dùng, record stale khi DB mới hơn.

Render Qt Windows native dùng DB kiểm tra 100 kỳ và config tạm key rỗng: chọn AI phân tích lịch sử 90 kỳ, hiển thị Kỳ dự định chơi 01587 và lời giải thích. Không bấm tạo hoặc gửi provider để chụp ảnh. Ảnh phuong-phap-ai.png ở outputs checkpoint chat đã xem trực tiếp. Lỗi encoding stdout của helper chụp ảnh được sửa bằng UTF-8; app chính đã cấu hình UTF-8 từ trước.

Không live Vilao hoặc kiểm chứng lợi thế AI. Giới hạn provider/AI thống kê và các giới hạn toàn sản phẩm trước đó vẫn còn. Streaming reuse giao thức đã có; đối chiếu tài liệu chính thức https://developers.openai.com/api/docs/guides/streaming-responses có response.output_text.delta và response.completed.
