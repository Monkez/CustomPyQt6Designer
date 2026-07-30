# Cài đặt và sử dụng

## Chọn cách nhanh nhất

### Cách 1 — Portable, không cần Python

1. Tải `MonkezDesigner-<version>-windows-x64.zip`.
2. Giải nén toàn bộ ZIP.
3. Double-click `Open Monkez Designer.bat`.

Đây là cách phù hợp nhất cho người chỉ cần thiết kế `.ui`. File
`START_HERE.txt` trong thư mục portable chứa hướng dẫn ngắn. Không di chuyển
riêng `MonkezDesigner.exe` ra khỏi thư mục `_internal`.

### Cách 2 — Cài vào tài khoản Windows

Yêu cầu Python 3.11. Tải source ZIP hoặc clone repository, sau đó double-click:

```text
install_designer.bat
```

Script sẽ tự động:

1. kiểm tra Python 3.11;
2. tạo môi trường cô lập trong `%LOCALAPPDATA%\MonkezDesigner`;
3. cài package cùng Designer bridge;
4. chạy kiểm tra môi trường;
5. tạo shortcut Desktop và Start Menu cho Designer, Docs Lab và Uninstall;
6. mở Designer.

Không cần quyền Administrator và không làm thay đổi virtual environment của
project. Có thể nâng cấp bằng cách chạy lại cùng file. Gỡ bằng shortcut
`Uninstall Monkez Designer` hoặc `uninstall_designer.bat`.

### Cách 3 — Cài package vào project Python

Nếu app chỉ cần chạy file `.ui`, cài runtime:

```powershell
python -m pip install --upgrade "custom-pyqt6-designer @ git+https://github.com/Monkez/CustomPyQt6Designer.git"
```

Nếu muốn mở Designer từ cùng virtual environment, dùng Python 3.11 và extra
`designer`:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade "custom-pyqt6-designer[designer] @ git+https://github.com/Monkez/CustomPyQt6Designer.git"
.\.venv\Scripts\python.exe -m custom_pyqt6_designer --doctor
.\.venv\Scripts\python.exe -m custom_pyqt6_designer
```

Lệnh module hoạt động ngay cả khi thư mục `Scripts` chưa có trong `PATH`.

## Tự kiểm tra cài đặt

```powershell
python -m custom_pyqt6_designer --doctor
```

Doctor kiểm tra phiên bản package/Python, đủ 25 plugin, vị trí Qt Designer và
Python plugin bridge. Mỗi lỗi đều kèm hướng khắc phục. Xem phiên bản nhanh:

```powershell
python -m custom_pyqt6_designer --version
```

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

Chạy demo và benchmark splash screen:

```powershell
splash_demo.bat
benchmark_splash.bat
```

Chi tiết API và cách thiết kế lại splash nằm trong [SPLASHSCREEN.md](SPLASHSCREEN.md).

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
