# Cài đặt và sử dụng

## Chọn đúng thành phần

Custom PyQt6 Designer có hai thành phần độc lập:

- Dùng `MonkezDesigner.exe` để thiết kế file `.ui` bằng kéo-thả.
- Cài Python package vào ứng dụng để chạy file `.ui`.

Máy thiết kế không cần Python khi dùng bản portable. Máy chạy ứng dụng không
cần mang theo Designer.

## Người thiết kế giao diện

1. Tải file `MonkezDesigner-<version>-windows-x64.zip` từ GitHub Releases.
2. Giải nén toàn bộ file ZIP.
3. Giữ nguyên `MonkezDesigner.exe` và thư mục `_internal` cạnh nhau.
4. Chạy `MonkezDesigner.exe`.
5. Tìm widget trong các nhóm `Monkez 01 Controls` đến `Monkez 07 Media`.
6. Thiết kế và lưu file `.ui`.

Property `themeIndex` và menu chuột phải `Monkez Theme` đều hỗ trợ:
Material, iOS, Fluent, Bootstrap, Minimal và Dark.

## Lập trình viên tích hợp runtime

Tạo môi trường riêng và cài package:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install "custom-pyqt6-designer @ git+https://github.com/Monkez/CustomPyQt6Designer.git"
```

Nếu dùng camera:

```powershell
.\.venv\Scripts\python.exe -m pip install "custom-pyqt6-designer[camera] @ git+https://github.com/Monkez/CustomPyQt6Designer.git"
```

Nạp giao diện:

```python
from PyQt6 import uic
from PyQt6.QtWidgets import QApplication

from custom_pyqt6_designer import monkez_widgets

app = QApplication([])
window = uic.loadUi("ui/main_window.ui")
window.show()
app.exec()
```

Trong file `.ui`, custom widget phải dùng header:

```xml
<header>custom_pyqt6_designer.monkez_widgets</header>
```

## Phát triển repository

Yêu cầu Windows và Python 3.11. Các thao tác thường dùng chỉ cần chạy:

```powershell
setup.bat
run.bat
gallery.bat
demo.bat
test.bat
build.bat
```

`run.bat`, `gallery.bat`, `demo.bat`, `test.bat` và `build.bat` sẽ tự gọi
`setup.bat` nếu môi trường chưa được tạo.

## Xử lý lỗi thường gặp

### Designer không có Monkez widget

Chạy `run.bat` từ repository thay vì mở một bản Qt Designer khác. Có thể kiểm tra
đường dẫn plugin bằng:

```powershell
.\.venv311\Scripts\custom-pyqt6-plugin-info.exe
```

### Ứng dụng không nạp được custom widget

Kiểm tra package đã được cài trong đúng virtual environment, module
`custom_pyqt6_designer.monkez_widgets` đã được import và header trong `.ui`
không bị thay đổi.

### Camera không hoạt động

Cài extra `camera`, kiểm tra `cameraSource`, và thử backend `dshow` hoặc `auto`
trên Windows.
