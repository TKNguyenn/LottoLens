# Hướng dẫn sử dụng LottoLens

Thiết kế đã duyệt nằm trong `lottolens-onboarding.html`. Bản Qt native nằm ở `app/onboarding.py`, mở sau policy lần đầu và qua Trợ giúp / Help trên thanh trên. Receipt cục bộ riêng `onboarding-v1.txt`, không thêm trường vào AI config hoặc UI preferences.

`assets/guide.json` giữ nội dung Việt/Anh và tọa độ chú thích cho 32 ảnh theo theme/ngôn ngữ. Ảnh WebP lossless được chụp ở DPR 3 từ Qt Windows bằng DB và config tạm. Không có API key hoặc dữ liệu người dùng trong ảnh. Bước AI bao gồm nhập URL/key, fetch, chọn model và Test model.

Công cụ tạo ảnh dành cho môi trường phát triển có Pillow và Node. Không thêm dependency chạy app.

```powershell
# Với Windows đang đặt scale 125%, QT_SCALE_FACTOR 2.4 cho DPR 3.
$env:QT_QPA_PLATFORM = 'windows'
$env:QT_SCALE_FACTOR = '2.4'
python docs/redesign/onboarding/capture.py
node docs/redesign/onboarding/build_assets.cjs
```

Script capture xác nhận DPR thực tế và kích thước pixmap, dùng dữ liệu giả, không gọi mạng hoặc đăng ký lịch. Nếu máy dùng scale khác, điều chỉnh QT_SCALE_FACTOR để DPR cuối cùng bằng 3.

```powershell
python scripts/check_onboarding.py
python scripts/check_model_catalog.py
```

Hai script kiểm tra dùng DB/config/receipt tạm. Đặt `QT_QPA_PLATFORM=windows` để kiểm tra native, mặc định offscreen. Toàn bộ folder assets cần đi cùng app khi đóng gói, giống thư mục icon và POLICY.md hiện có.
