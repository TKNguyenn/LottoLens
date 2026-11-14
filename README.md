<p align="center"><img src="docs/redesign/assets/generated/07-ticket-gold.png" width="88" alt="Biểu tượng LottoLens"></p>
<h1 align="center">LottoLens</h1>
<p align="center">Lịch sử Vietlott, xác suất và thống kê — trong một ứng dụng desktop.</p>
<p align="center"><strong>Tiếng Việt</strong> · <a href="README.en.md">English</a></p>
<p align="center">
  <img src="https://img.shields.io/badge/version-1.0.0-C81E33" alt="Phiên bản 1.0.0">
  <img src="https://img.shields.io/badge/platform-Windows_10%2F11-0078D4" alt="Windows 10 và 11">
  <img src="https://img.shields.io/badge/Python-3.11-3776AB" alt="Python 3.11">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-GPLv3-blue" alt="Giấy phép GPLv3"></a>
</p>
<p align="center"><strong><a href="https://github.com/TKNguyenn/LottoLens/releases/download/v1.0.0/LottoLens-Setup-1.0.0.exe">Tải bộ cài Windows V1.0.0</a></strong> · <a href="https://github.com/TKNguyenn/LottoLens/releases/tag/v1.0.0">Ghi chú phát hành</a></p>

![Tổng quan LottoLens với giao diện tối](docs/images/vi-overview-dark.png)

**LottoLens** là ứng dụng Python/PySide6 giúp bạn tra cứu lịch sử Vietlott, khám phá dữ liệu đã lưu, xem xác suất lý thuyết và kiểm chứng phương pháp chọn số. Dữ liệu lưu tại máy bằng SQLite; AI là tính năng tùy chọn.

> LottoLens không cổ súy cá cược, cờ bạc hoặc mê tín dị đoan. Thống kê quá khứ, bộ số tham khảo và nội dung AI không bảo đảm dự đoán được kỳ tiếp theo hay tăng khả năng trúng. Đọc [chính sách sử dụng Việt–Anh](POLICY.md).

*Ảnh được chụp từ app thật với dữ liệu mẫu, không phải kết quả quay chính thức. Mở ảnh để xem kích thước đầy đủ.*

## Bản phát hành v1.0.0

Bổ sung hai phương pháp AI cho cả bảy trò, lịch tự cập nhật theo giờ quay và xử lý HTTP 429 có thời gian nghỉ theo nguồn. Xem [ghi chú phát hành Việt–Anh](docs/releases/v1.0.0.md). Sau khi nâng cấp, bấm **Lưu cài đặt** để đăng ký lại lịch tự cập nhật.

## Điểm nổi bật

- **Lịch sử có nguồn:** tải kết quả từ Vietlott, tìm theo kỳ/số và mở nguồn để đối chiếu. Đồng bộ tăng dần khi có mốc lịch sử đã xác minh.
- **Thống kê và xác suất:** tần suất, heatmap và xác suất theo mô hình luật; chọn số kỳ gần nhất dùng để phân tích.
- **Bộ số tham khảo:** đồng đều, tần suất, Bayes hoặc AI. Lưu bộ số cùng phương pháp và snapshot lịch sử đã dùng.
- **Mô phỏng và kiểm chứng:** mô phỏng vé và so phương pháp với lựa chọn ngẫu nhiên trên cả bảy trò. Báo cáo hiển thị số vé trúng, tỷ lệ và từng hạng giải.
- **Tự cập nhật từng trò:** theo lịch quay hoặc giờ tự đặt, chạy qua Windows Task Scheduler ngay cả khi đóng app.
- **Giao diện Việt/Anh:** đổi ngôn ngữ trực tiếp, theme sáng/tối có gradient, sidebar thu gọn, hướng dẫn bằng ảnh và luật từng trò.
- **AI tùy chọn:** endpoint HTTPS OpenAI-compatible, tải danh sách model, nhập model thủ công và streaming.
- **Cập nhật ứng dụng:** kiểm tra GitHub từ sidebar, có công tắc tự kiểm tra và xác nhận trước khi tải bộ cài.

<details>
<summary>Xem giao diện sáng</summary>

![Tổng quan LottoLens với giao diện sáng](docs/images/vi-overview-light.png)

</details>

## Bắt đầu

### Bộ cài Windows

Tải [LottoLens-Setup-1.0.0.exe](https://github.com/TKNguyenn/LottoLens/releases/download/v1.0.0/LottoLens-Setup-1.0.0.exe) cho **Windows 10/11 x64**. Nếu đã cài LottoLens, hãy đóng app và chọn lại thư mục cài hiện tại để tiếp tục dùng dữ liệu trong thư mục `data`.

Bộ cài cho chọn thư mục lưu app và dữ liệu. Trang cuối có ô tạo shortcut Desktop và mở app. Khi gỡ, chọn **giữ dữ liệu** hoặc **xóa toàn bộ dữ liệu**. Cả hai dọn lịch tự cập nhật của bản cài đó. Setup chưa ký số, Windows có thể báo nhà phát hành không xác định.

Từ V0.8.0, dùng **Kiểm tra cập nhật** ở cuối sidebar. App mặc định tự kiểm tra sau khi mở và mỗi giờ khi đang chạy. Để tắt, vào **Cài đặt → Cập nhật LottoLens** rồi bấm **Lưu cài đặt**. App hỏi trước khi tải bản mới và kiểm tra SHA-256 của bộ cài.

### Chạy từ source

Đã kiểm tra với **Windows x64, Python 3.11 và PySide6 6.11.2**.

```powershell
git clone https://github.com/TKNguyenn/LottoLens.git
cd LottoLens
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Lần mở đầu, cửa sổ chính hiện cùng popup chính sách. Tích riêng **Đã đọc** và **Chấp nhận** để tiếp tục tới hướng dẫn bằng ảnh. Mở lại hướng dẫn bằng **Trợ giúp** trên thanh trên; chính sách nằm trong **Cài đặt → Giới thiệu**.

## Hướng dẫn sử dụng

### 1. Chọn trò và tải lịch sử

Chọn trò ở thanh trên, rồi bấm **Cập nhật lịch sử**. Lần đầu app tải phạm vi đã đặt, mặc định 100 kỳ. Những lần sau app lấy phần mới tới vùng đã đồng bộ; khi tăng giới hạn hoặc cần xác minh dữ liệu, app có thể tải lại đủ phạm vi.

Sau lượt tải hợp lệ, app giữ tối đa số kỳ đã chọn và loại kỳ cũ ngoài phạm vi. Bộ số, báo cáo và snapshot đã lưu được giữ. Lỗi, hủy hoặc tải chưa hoàn tất không thay lịch sử đang có. **Nhập CSV** hỗ trợ các trò tập số theo [mẫu bên dưới](#csv-và-dòng-lệnh).

![Bảng lịch sử và kết quả hiển thị bằng bóng số](docs/images/vi-history-light.png)

### 2. Xem thống kê và xác suất

Mở **Thống kê** để xem tần suất và heatmap. Mở **Xác suất** để xem mô hình lý thuyết theo trò, loại vé hoặc cách chơi. **Hướng dẫn trò chơi** giải thích cách chọn số, quay thưởng và điều kiện trúng từng hạng, kèm nguồn chính thức.

**Tần suất quan sát được không phải xác suất dự báo.** Với giả định quay công bằng, các bộ hợp lệ cùng loại vé có xác suất lý thuyết như nhau.

![Thống kê và heatmap trên dữ liệu mẫu](docs/images/vi-stats-dark.png)

### 3. Tạo bộ tham khảo và kiểm chứng

Trong **Bộ số tham khảo**, chọn phương pháp và số bộ rồi tạo. Đồng đều dùng được khi chưa có lịch sử; tần suất, Bayes và AI cần đủ cửa sổ phân tích. Chỉ nhập **Kỳ dự định chơi** khi muốn lưu để đối chiếu sau này.

Trong **Kiểm chứng**, chọn phương pháp để so với lựa chọn ngẫu nhiên. Nếu đặt phân tích 100 kỳ nhưng chỉ lưu 100, kiểm chứng dùng tối đa 99 làm đầu vào, chừa kỳ để đối chiếu và hiện ghi chú. Cần ít nhất hai kỳ. **Chạy kiểm chứng AI** gửi lịch sử trước kỳ mới nhất tới model đã cấu hình và có thể tính phí. App tự chấm vé trên một kỳ đã lưu rồi so với 200 lượt chọn ngẫu nhiên tại máy. Model có thể đã biết kết quả công khai, nên đây là phép thử tham khảo.

Bấm **Chạy mô phỏng** để thử một vé qua 10.000 kỳ giả lập. Với Max 3D, Max 3D Pro và Bingo18, chọn vé ngay trên trang Kiểm chứng. Kiểm chứng Bingo18 dùng cùng cách chơi và tối đa 5 vé khác nhau mỗi kỳ. **Lớn–Hòa–Nhỏ** có 3 lựa chọn, **Ba số bất kỳ** có 1 lựa chọn.

Để tạo các dòng như kết quả Bingo18, vào **Bộ số tham khảo → Kết quả giả lập (3 số)**, chỉnh **Số bộ** rồi bấm **Tạo kết quả giả lập**. Mỗi dòng có ba số từ 01 đến 06 và có thể lặp số. Các dòng chỉ hiện trên bảng. Để xem xác suất của một cửa và lựa chọn cụ thể, dùng trang **Xác suất**.

Kiểu bộ ba hỗ trợ đồng đều, tần suất, Bayes và AI. Tần suất và Bayes đếm riêng từng vị trí trên số kỳ phân tích đã đặt. Bayes dùng prior tương đương 90 kỳ đồng đều. AI dùng model đã cấu hình, có thể tính phí và chỉ được gọi khi bấm tạo.

Báo cáo kiểm chứng cho biết số vé trúng và so tỷ lệ với chọn ngẫu nhiên. Báo cáo mô phỏng cho biết vé đã thử, số kỳ trúng và tần suất từng hạng giải trong lần chạy. Chọn **Xem dữ liệu JSON** để xem dữ liệu kỹ thuật.

Trang **Bộ số tham khảo** có thêm hai phương pháp AI cho cả bảy trò. **AI tối ưu hạng giải** chọn nhóm bộ theo hạng bạn quan tâm, rồi so tỷ lệ có ít nhất một bộ đạt mục tiêu với nhóm tối ưu tại máy và một nhóm ngẫu nhiên cùng số bộ. Báo cáo ghi rõ khi dùng mô phỏng. **AI tìm và kiểm chứng tín hiệu** cần ít nhất 20 kỳ. Model chọn một quy tắc tần suất hoặc Bayes từ đoạn lịch sử cũ. App giữ các kỳ cuối để thử quy tắc tại máy và so với ngẫu nhiên, Bayes và tối ưu tại máy. Cả hai lấy số kỳ đầu vào từ **Số kỳ gần nhất để phân tích**, trong phạm vi lịch sử có sẵn sau khi dành các kỳ kiểm chứng. Yêu cầu quá 10.000 ký tự báo lỗi trước khi gọi. App chỉ gửi khi bấm tạo và có thể tính phí. Với **Kết quả giả lập (3 số)** của Bingo18, mục tiêu là khớp đúng ba số theo thứ tự.

### 4. Cài đặt số kỳ và lịch tự cập nhật

| Cài đặt | Mặc định | Tác dụng |
| --- | --- | --- |
| Số kỳ giữ lại, riêng từng trò | 100 | Phạm vi lịch sử lưu sau cập nhật hợp lệ |
| Số kỳ gần nhất để phân tích | 90 | Đầu vào tổng quan, tần suất, Bayes, AI và warm-up kiểm chứng |

Trong **Cài đặt**, bật **Tự động** cho từng trò, chọn **Theo lịch quay** hoặc **Giờ tùy chọn**, rồi bấm **Lưu cài đặt**. Lịch theo **UTC+7** và chạy khi máy bật, tài khoản Windows đang đăng nhập, dù app đã đóng. Các công tắc mặc định tắt.

**Theo lịch quay** dùng 18:45 vào ngày quay của Mega, Power, Max 3D và Max 3D Pro, 13:15 và 21:15 hằng ngày cho Lotto 5/35. Keno chờ 4 phút sau giờ quay dự kiến, kiểm tra mỗi 8 phút từ 06:12 đến 21:56. Bingo18 chờ 8 phút, kiểm tra mỗi 6 phút từ 06:13 đến 22:01. Hai trò dùng URL kết quả chính thức mặc định, một lượt tải mỗi mốc và giãn các request trong lượt ít nhất 2 giây. Nếu gặp HTTP 429, dừng ngay lượt tải; cả hai lịch cùng DB nghỉ ít nhất 1 giờ, hoặc lâu hơn theo `Retry-After` của nguồn. Thời điểm chờ được lưu trong chi tiết lỗi và không làm mất lịch sử cũ. Khoảng chờ dựa trên một số quan sát, không bảo đảm nguồn luôn có kết quả đúng giờ. **Giờ tùy chọn** chạy một lần mỗi ngày ở giờ đã đặt. Lịch cũ chuyển vào chế độ giờ tùy chọn.

Mỗi khung giờ thử một lần. Nếu nguồn chưa hiện kết quả, app ghi trạng thái chờ và sẽ kiểm tra ở lượt đã lên lịch tiếp theo. Bạn cũng có thể bấm **Cập nhật lịch sử**. Lịch Keno cập nhật chung kết quả cho cả 10 kiểu chọn số.

![Cài đặt ngôn ngữ, cửa sổ phân tích và lịch tự cập nhật](docs/images/vi-settings-light.png)

### 5. Dùng AI — tùy chọn

Tính năng tại máy không cần API key. Để dùng AI:

1. Mở **AI & cấu hình**, nhập Base URL HTTPS, mặc định `https://api.openai.com/v1`.
2. Nhập API key, bấm **Tải danh sách model** rồi chọn; có thể nhập model thủ công.
3. Bấm **Test model** để kiểm tra hoặc **Lưu cấu hình** để giữ cấu hình tại máy.
4. Chủ động dùng tìm nguồn web hoặc **AI phân tích lịch sử** khi cần.

App tự chọn Responses → Chat Completions → Completions, chỉ chuyển khi 404/405 xác định endpoint không hỗ trợ. Lỗi key/model/giới hạn/mạng, lỗi mơ hồ hoặc phản hồi đã bắt đầu sẽ dừng. Mỗi lần dò tối đa ba đường dẫn. Không tự gọi AI khi mở app. Web search và mức suy luận High cần provider/model hỗ trợ; Legacy Completions không hỗ trợ hai tính năng đó.

**AI có thể tính phí và đưa ra nội dung sai.** Phân tích lịch sử gửi dữ liệu cần thiết tới provider bạn chọn. Nếu bấm lưu, API key nằm rõ trong `config.json`; không đưa file này lên Git. Kết quả AI không được nhập làm kết quả quay chính thức.

![Cấu hình AI và tải danh sách model](docs/images/vi-ai-dark.png)

## Các trò được hỗ trợ

Cả 7 trò đều có lịch sử, thống kê, xác suất lý thuyết và bộ số tham khảo cho các cách chơi bên dưới.

| Trò | Phạm vi xác suất và bộ tham khảo | Mô phỏng kỳ quay | Kiểm chứng trên lịch sử theo hạng giải |
| --- | --- | --- | --- |
| Mega 6/45 | Vé cơ bản | Có | Có |
| Power 6/55 | Vé cơ bản, tính riêng số bonus | Có | Có |
| Lotto 5/35 | Vé cơ bản, tính riêng số đặc biệt | Có | Có |
| Keno chọn 1–10 | Vé chọn 1–10 số, xác suất theo số lượng trùng | Theo số lượng trùng và hạng giải | Có, gồm hạng trùng 0 số của bậc 8–10 |
| Max 3D | Vé một bộ `000–999`, xác suất theo sự kiện trúng | Có | Có |
| Max 3D Pro | Vé hai bộ có thứ tự, cho phép hai bộ giống nhau | Có | Có, tính các hạng có thể cùng trúng |
| Bingo18 | Đủ 38 lựa chọn trong các nhóm được mô hình hóa | Có | Có, theo cách chơi đã chọn |

Mô phỏng và kiểm chứng Keno, Max 3D, Max 3D Pro và Bingo18 báo số lần trúng theo luật hiện được mô hình hóa. Một vé Max có thể xuất hiện ở nhiều hạng trong cùng kỳ và chỉ được đếm một lần trong tỷ lệ vé trúng. Tiền thưởng lịch sử và EV của bốn trò vẫn chưa được xác minh. Chơi bao, Keno bổ sung và Max 3D+ cần mô hình riêng. Xem [ma trận hỗ trợ](docs/game_support_matrix.md) và [nguồn kiểm chứng luật](docs/source_audit.md).

## Dữ liệu được lưu ở đâu?

| Cách chạy | Lịch sử và báo cáo | Cấu hình |
| --- | --- | --- |
| Bộ cài / EXE | `data/history.sqlite3` cạnh EXE | Cùng thư mục `data` |
| Python source | `%LOCALAPPDATA%/VietlottDesktop/history.sqlite3` | Gốc dự án |

`ui_preferences.json`, `theme.json`, `window_geometry.bin` tách khỏi cấu hình AI. EXE lưu xác nhận chính sách/hướng dẫn và cache nguồn trong `data`; source lưu chúng cạnh DB. Không đồng bộ cloud hoặc tự chuyển dữ liệu source sang bản cài. Đóng app trước khi sao lưu DB/cấu hình; với bản cài có thể sao lưu cả `data`.

## CSV và dòng lệnh

Mẫu CSV cho trò tập số:

```csv
draw_id,draw_date,main,special
01586,2026-11-08,01 02 14 20 23 36,
```

Ví dụ trong môi trường Python đã cài dependency:

```powershell
python main.py self-check
python main.py sync --game mega --limit 100
python main.py history --game mega
python main.py odds --game power
python main.py odds --game keno --mode pick8
python main.py import-csv --game mega "history.csv"
```

Dùng giao diện desktop để mô phỏng vé Max 3D, Max 3D Pro và Bingo18 hoặc kiểm chứng các cách chơi Bingo18. Xem `python main.py --help` để biết các lệnh CLI.

## Phát triển và kiểm tra

```powershell
python -m pip install pytest pytest-subtests
python -m pytest tests/ -q
python scripts/check_packaging.py
```

Test AI dùng phản hồi giả lập, không gọi provider thật. Bộ cài dùng PyInstaller và Inno Setup; xem [hướng dẫn build](packaging/README.md). Chụp lại ảnh README bằng `docs/images/capture.py`: chỉ dùng dữ liệu giả trong thư mục tạm và chặn mạng.

## License

**Copyright © 2026 TKNguyen.** **GNU GPLv3 only (`GPL-3.0-only`)** — [LICENSE](LICENSE), [COPYRIGHT](COPYRIGHT). Phân phối bản nhị phân hoặc bản sửa đổi phải tuân thủ GPLv3, bao gồm mã nguồn tương ứng. Thành phần bên thứ ba giữ license riêng. [POLICY.md](POLICY.md) mô tả mục đích/giới hạn app, không thêm hạn chế đối với quyền GPL.
