# LottoLens — Cài đặt và ngôn ngữ trực tiếp

Trang thứ 8, nằm sau AI & cấu hình; giữ nguyên vị trí và API của 7 trang trước. Cùng theme gradient sáng/tối và sidebar 236/68px đã duyệt. Ảnh tham chiếu Piaz Switch chỉ dùng cho bố cục giới thiệu/cài đặt; không sao chép nội dung về tài khoản hoặc hành vi mạng của app đó.

## Cách dùng

- **Tiếng Việt / English:** đổi ngay khi chọn, không cần mở lại app. Giữ trang, sidebar, lựa chọn, input, bộ số và kết quả. **Lưu cài đặt** giữ ngôn ngữ cho lần mở sau.
- **Số kỳ gần nhất để phân tích:** một giá trị chung 1–2000/default90, độc lập số kỳ tải. Đổi ngay cho tổng quan, Bayes/tần suất, AI và warm-up backtest; N kỳ cần ít nhất N kỳ đã lưu để sinh số thống kê/AI, backtest cần N+1. Trang Thống kê thay preset đầu bằng N và vẫn giữ bộ lọc riêng 30/toàn bộ. Lưu cài đặt giữ cho lần mở sau. Bộ số đang xem không bị tính lại; nó giữ metadata cửa sổ lúc tạo.
- **Số kỳ giữ lại:** mỗi trò có giá trị riêng 1–2000/default100; đồng bộ với ô cùng tên trên trang Lịch sử. Cập nhật thêm kỳ mới rồi xóa kỳ cũ ngoài giới hạn trong một giao dịch; snapshot/bộ số/báo cáo giữ nguyên. Chỉ chỉnh/lưu con số chưa xóa dữ liệu; thu gọn sau cập nhật hợp lệ. Keno dùng chung giới hạn cho các lựa chọn số.
- **Tự động + Giờ:** riêng từng trò, mặc định tắt/20:00; bật, chọn HH:mm và Lưu cài đặt để đăng ký lịch Windows. Chạy theo UTC+7, cả khi app đóng, khi máy bật và user còn đăng nhập. Không chạy bù/lặp lại sau lỗi trong ngày, không gọi AI. Tắt rồi Save xóa lịch của trò đó.
- **Giới thiệu:** logo LottoLens, mô tả ngắn và một nút GitHub. Chưa có URL nên nút vô hiệu hóa, có tooltip giải thích; không gắn link giả. URL sau này đặt tại `APP_GITHUB_URL` trong `app/ui.py`.

## Triển khai

- `app/preferences.py`: `ui_preferences.json` cạnh config.json, schema `{language, history_limits, analysis_window, auto_updates}`. Auto settings đủ7game, mỗi game `{enabled:bool,time:'HH:mm'}`; file cũ tự dùng tất cả tắt/20:00, analysis_window90 khi thiếu. Validate kiểu/range, không nhận bool làm số; ghi tạm rồi replace. Lỗi file/lưu không báo thành công hoặc tự ghi đè file hỏng.
- `app/i18n.py`: catalog EN cho copy thuộc app, template fullmatch giữ giá trị nội suy; `tr` và `bind_text` giữ source gốc. Widget label/button/combo/nav/header/tooltip lưu copy gốc để render lại theo ngôn ngữ; không dịch ngược chữ hiển thị.
- `apply_language`: không gọi `refresh()` hoặc tạo lại Desktop, không gọi mạng/ghi store. Summary thống kê render từ dữ liệu describe đã có; báo cáo chỉ đọc lại JSON hiện tại cho phần tóm tắt. Giữ định danh giải theo trò khi đổi qua lại.
- `LocalizedTextBrowser` chỉ dịch phần hướng dẫn/giải thích được đánh dấu thuộc app; `setPlainText`, streaming/append và JSON report vẫn giữ dữ liệu gốc. Không dịch input của người dùng hoặc phản hồi AI. Không đưa API key vào preferences.
- Language/count/analysis/schedule inputs và nút Lưu khóa theo worker; giờ chỉ bật khi công tắc tương ứng bật. GitHub tiếp tục disabled sau worker. Không thêm dependency hoặc đổi main.py/tests/AI. Ngoại lệ history-window trước đó ở3file math, yêu cầu mới 2026-11-11 mở thêm đúng phần sources/storage cho incremental và retention; xem handoff16.

## Đồng bộ tăng dần và lịch Windows — 2026-11-11

- `OfficialSource.fetch_history(...,known_draws=...)` đọc đầu nguồn rồi dừng khi gặp vùng đã có, vẫn đọc overlap để phát hiện sửa kỳ ở ranh giới. Đầu trang có thể chứa vài kỳ đã lưu. Nếu thiếu bằng chứng phạm vi liên tục hoặc tăng N, tải đầy đủ phạm vi trước khi dùng incremental. Không tự rà lại mọi sửa đổi sâu trong lịch sử ở mỗi lần cập nhật.
- SQLite lưu fingerprint của cửa sổ đồng bộ. Thay đổi CSV/SQL làm fingerprint lệch → lượt sau xác minh lại. `apply_sync` chỉ prune với receipt đầy đủ, rollback cả thêm/xóa/proof nếu lỗi/hủy; snapshot, suggestions, reports không xóa. Hai tham số `add_draws` cũ vẫn cộng thêm cho CSV/CLI. Bảng metadata thêm tương thích schema2, không migration phá dữ liệu.
- `apply_sync_many` ghi tất cả10 Keno modes trong một giao dịch. Một fetch, các mode cùng dữ liệu; lỗi ở mode2 hoặc tắt giữa chừng rollback cả mode1 đã xử lý. Không có trạng thái xóa một phần.
- `app/scheduling.py` đăng ký native XML CalendarTrigger+07:00, InteractiveToken/LeastPrivilege, pythonw/helper/DB/prefs đường dẫn tuyệt đối có quote. Taskname hash theo prefs profile +game; chỉ sửa own tasks. Save giữ XML cũ để rollback nếu đăng ký hoặc ghi prefs lỗi. All-off mặc định không gọi schtasks.
- `scripts/scheduled_sync.py` chạy độc lập GUI. Helper đọc opt-in, claim ngày Việt Nam vào DB trước mạng, mỗi game tối đa một lần tự thử/ngày kể cả thất bại. Chỉ một HTTP attempt mỗi request trong GUI/job, không web/AI. Disable được kiểm tra lại trước và trong giao dịch. Task không chạy bù, không restart-on-failure, không dùng mật khẩu/API key.
- App mở chỉ poll DB30giây, không gọi mạng. Khi job khác ghi history, cập nhật bảng/tổng quan/thống kê và note; giữ generated/input/raw AI/report đang xem. Nếu worker đang chạy thì đợi tới lượt poll rảnh. Thông báo kết quả tự động hôm nay hiện trong status notice.
- Kiểm chứng:16 core checks, daily scheduler checks và UI sync checks pass; original69tests/23subtests pass. Reviewer độc lập đã tái hiện/sửa/kiểm lại P1 multi-mode rollback, verdict Ship. Audit protected-file hiện17file giữ nguyên,5ngoại lệ cộng dồn (3history-window cũ +sources/storage mới); manifest gốc không đổi.
- **Windows thật:** đã tạo task tạm, query XML+07:00, `/Run` pythonw khi file prefs thực tế tắt, LastTaskResult0 và DB không được mở; task đã xóa/query xác nhận không còn. Enabled-job logic/transport kiểm tra giả lập với DB tạm, không gọi provider hoặc đăng ký lịch người dùng trong quá trình triển khai.

Ảnh mới: [Việt tối](reviews/daily-sync/settings-vi-dark-expanded.png), [Anh sáng](reviews/daily-sync/settings-en-light-expanded.png), [cuối trang/Save](reviews/daily-sync/settings-en-light-bottom.png). Dựng bằng `capture.py --daily-sync`; công tắc trong ảnh chỉ là preview chưa Save, không đăng ký job. Kế hoạch: `incremental-sync-plan.md`; hồ sơ chuẩn root handoff16.

## Cửa sổ phân tích — bổ sung 2026-11-10

Các API generation/AI thêm tham số cuối `history_window=90`, backtest config thêm cùng trường. Mặc định90 giữ đầu ra chọn số có seed như baseline trên Mega/Power/Lotto/Keno. ID phương pháp cũ vẫn giữ để tương thích; metadata lưu `history_window`, `history_used`, và prior cho kết quả tạo tại máy; báo cáo lưu config/warmup N. Bayes giữ prior90, công thức `(count+90*fair)/(N+90)`; chỉ cửa sổ quan sát thay đổi.

**Riêng giao diện Kiểm chứng tự dành ít nhất một kỳ để đối chiếu:** cửa sổ thực = min(N đã đặt, số kỳ đã lưu−1). Ví dụ đặt100/lưu100 →99, badge `100 → 99 kỳ` cạnh tiêu đề giải thích điều chỉnh; đặt100/lưu101 trở lên →100, ẩn badge. Cài đặt chung và tạo số giữ nguyên100. Ít hơn2 kỳ vẫn chưa thể kiểm chứng. Báo cáo ghi cửa sổ thực, core/CLI giữ kiểm tra N+1. [Ảnh trường hợp100/100](reviews/backtest-adjustment/verification-vi-light-100.png), [handoff mục15](../../../implementation_handoff.md).

AI gửi đúng N kỳ đã chọn và instructions tương ứng; metadata/hash dùng input/instructions thật. Giữ giới hạn input10.000 ký tự hiện có: N lớn có thể bị chặn trước transport, báo giảm số kỳ, không tự hạ N hoặc retry. Không gọi AI/backtest/generate khi chỉnh setting; không tự tải bổ sung hoặc xóa lịch sử.

Thêm `scripts/check_analysis_core.py` và `scripts/check_analysis_window.py`: TDD RED→GREEN, N1/30/120/2000, prior90, cửa sổ đúng/cutoff, metadata batch cũ sau thay N, mock AI thực qua UI, khóa input, thiếu lịch sử/size guard không HTTP, backtest chỉ dùng quá khứ/warmup/past-target isolation và VI/EN. Default baseline hashes trước thay đổi ở `analysis-defaults.json`, không phụ thuộc thư mục backup kỹ thuật.

Reviewer độc lập đã sửa và kiểm lại nhãn phương pháp backtest N/minN+1, verdict Ship. Audit protected-file: **19 file nguyên hash, đúng 3 file được người dùng cho phép thay phần số kỳ**. Đây là ngoại lệ mới sau kiểm chứng22file nguyên vẹn của mục Cài đặt ban đầu.

Ảnh mới tại [reviews/analysis-window/](reviews/analysis-window/): [Cài đặt N120 · Việt tối](reviews/analysis-window/settings-vi-dark-120.png), [tạo số N120 · Anh sáng](reviews/analysis-window/suggestions-en-light-120.png), [kiểm chứng N120](reviews/analysis-window/verification-vi-dark-120.png), [tổng quan N120](reviews/analysis-window/overview-vi-dark-120.png). Chụp bằng `capture_analysis.py`, dữ liệu giả lập trên DB tạm, không gọi mạng. Hồ sơ mới ở root handoff mục14, kế hoạch `analysis-window-plan.md`.

## Kiểm chứng

```powershell
& 'C:/Users/kietj/AppData/Local/Programs/Python/Python311/python.exe' -m pytest tests/ -q
& 'C:/Users/kietj/AppData/Local/Programs/Python/Python311/python.exe' scripts/check_preferences.py
& 'C:/Users/kietj/AppData/Local/Programs/Python/Python311/python.exe' scripts/check_redesign.py
& 'C:/Users/kietj/AppData/Local/Programs/Python/Python311/python.exe' scripts/check_sidebar.py
& 'C:/Users/kietj/AppData/Local/Programs/Python/Python311/python.exe' scripts/check_gradient.py
& 'C:/Users/kietj/AppData/Local/Programs/Python/Python311/python.exe' app/i18n.py
& 'C:/Users/kietj/AppData/Local/Programs/Python/Python311/python.exe' scripts/check_analysis_core.py
& 'C:/Users/kietj/AppData/Local/Programs/Python/Python311/python.exe' scripts/check_analysis_window.py
& 'C:/Users/kietj/AppData/Local/Programs/Python/Python311/python.exe' scripts/check_backtest_window.py
& 'C:/Users/kietj/AppData/Local/Programs/Python/Python311/python.exe' scripts/check_incremental_sync.py
& 'C:/Users/kietj/AppData/Local/Programs/Python/Python311/python.exe' scripts/check_daily_scheduler.py
& 'C:/Users/kietj/AppData/Local/Programs/Python/Python311/python.exe' scripts/check_sync_settings.py
```

Full suite **69 passed, 23 subtests passed**. Settings regression pass offscreen và Windows native: 8 trang × 2 ngôn ngữ × 2 theme × 2 kích thước × 2 trạng thái rail, live switch/state/raw content, count mặc định/cách ly game/giá trị thực truyền vào fetch, không prune, lỗi ghi/replace/file hỏng, worker locking. General UI check mở rộng 7 trò × 8 trang có dữ liệu ở cả VI/EN, giữ checks nguồn/ngày/nhóm Max3D và offline/incomplete. Phạm vi3file core được cho phép mới được ghi ở phần cửa sổ phân tích bên trên.

Reviewer độc lập phát hiện lẫn copy nội suy và mất tên giải khi dịch ngược; đã sửa bằng source gốc + render summary, thêm regression cho Mega/Lotto/Keno và xác nhận lại verdict Ship. Không còn actionable finding.

## Ảnh Qt Windows

- [Việt · tối](reviews/settings-vi-dark-expanded.png), [Việt · sáng](reviews/settings-vi-light-expanded.png).
- [Anh · tối](reviews/settings-en-dark-expanded.png), [Anh · sáng](reviews/settings-en-light-expanded.png).
- [Sidebar thu · Anh](reviews/settings-en-dark-compact.png), [cửa sổ nhỏ · Anh](reviews/settings-en-small.png).
- [Tạo số · Anh](reviews/suggestions-en-dark.png).

Dựng ảnh bằng `capture.py` tại folder này, DB/config tạm và transport mock khẳng định không gọi mạng. Mọi artifact riêng của trang được giữ trong `docs/redesign/settings/`.

Giới hạn: chưa có URL GitHub; phản hồi provider và JSON dữ liệu giữ ngôn ngữ gốc, hộp thoại hệ thống theo Windows. Chưa nghiệm thu nhiều màn hình/mixed-DPI hoặc provider thật. Hồ sơ chuẩn là root `implementation_handoff.md`, mục 13.

## Trạng thái lịch và lỗi — 2026-11-11

Dưới từng trò có ngày và trạng thái lần tự cập nhật gần nhất. Lỗi downloader đã xác định được (HTTP, kết nối, cấu trúc trang) hiển thị chi tiết an toàn; lỗi tùy ý chỉ ghi tên lớp để tránh lưu URL/token/key. Bản ghi của phiên bản cũ chỉ có ValueError được ghi rõ là chưa giữ chi tiết. Notice chỉ hiển thị kết quả của trò đang xem, không để thành công của trò khác che lỗi.

Một lịch đã thất bại vẫn được tính là đã thử trong ngày. Đổi giờ hoặc chạy lại task cùng ngày không tự thử lại; dùng nút Cập nhật lịch sử để thử thủ công. Không đổi cơ chế retry/catch-up hoặc gọi mạng khi mở Cài đặt.

Đợt chẩn đoán thực tế: Max12:00 ngày11/11 đã chạy và failed/ValueError, không phải thiếu đăng ký lịch. Lỗi gốc cụ thể không được log cũ giữ lại. Một lượt tải kiểm tra thủ công sau đó thành công100kỳ; đã backup DB và nạp batch hoàn chỉnh vào đúng Max đang trống, giữ nguyên bản ghi failed. Xem root handoff18. Regression `scripts/check_schedule_diagnostics.py` kiểm tra HTTP503 giả lập, secret redaction, active-game notice và live VI/EN; provider không được gọi trong test.
