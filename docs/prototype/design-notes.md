# Hướng giao diện để review

Ngày 2026-11-09. Đây là prototype desktop độc lập, chưa phải GUI production T09.

- Nền ứng dụng `#F3F6FA`, mặt nội dung `#FFFFFF`, chữ `#173247`, nhấn `#C8253F`, đường phân cách `#DCE4ED`, nhãn minh họa `#FFF1D3`.
- Segoe UI cho tiếng Việt; tiêu đề 24–28 px, nội dung 14 px, số kết quả 22 px. Không thêm font tải mạng.
- Sidebar cố định cho các vùng chức năng; vùng chính căn trái, bảng dữ liệu được ưu tiên diện tích. Dãy bóng số là điểm nhấn duy nhất, không dùng hoạt cảnh mang ý nghĩa “may mắn”.
- Tên trò và trạng thái dữ liệu luôn nhìn thấy. Xác suất lý thuyết, tỷ lệ lịch sử và bộ số gợi ý có nhãn riêng.
- So với bố cục dashboard nhiều ô KPI giống nhau, bản này ưu tiên một kết quả quay, một bảng nguồn và một vùng thao tác; ít trang trí để dễ đọc số.

```text
Tên ứng dụng    | Chọn trò                     Dữ liệu minh họa
               | Tên vùng chức năng
Điều hướng     | Kết quả / bảng / cách tính
               | Thao tác chính
Trạng thái     | Giải thích hoặc nguồn dữ liệu
```

Review cần chốt bố cục, cỡ chữ, màu, mức hiển thị công thức và vùng cấu hình AI. Nút trong prototype chỉ đổi trạng thái minh họa; không cập nhật database, không ghi API key và không gọi Vilao.
