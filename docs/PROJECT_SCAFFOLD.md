# Tạo project PyQt6 mới

Tạo project bằng CLI:

```powershell
monkez-pyqt6 init --name my_app
```

Project mới có sẵn bộ nhận diện mặc định:

- `assets/images/logo.png`: logo PNG 512 x 512, được dùng trên splash screen.
- `assets/icons/app.ico`: icon Windows nhiều kích thước, được dùng làm application/window icon và được PyInstaller đóng gói cùng app.
- `assets/configs/config.json`: khai báo đường dẫn tương đối của cả `logo` và `icon`.

Có thể thay trực tiếp hai file ảnh nhưng nên giữ nguyên tên và đường dẫn để không phải sửa code. Nếu đổi vị trí, cập nhật `application.logo` và `application.icon` trong `config.json`.

Chạy `setup.bat` để chuẩn bị môi trường, `run.bat` để mở app và `build.bat` để tạo bản Windows executable.
