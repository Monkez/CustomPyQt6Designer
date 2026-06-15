# Custom PyQt6 Designer

Bộ custom widgets cho PyQt6, plugin cho Qt Designer và bản Designer portable đã cấu hình sẵn.

Repository được thiết kế theo hai phần độc lập:

- **Thiết kế giao diện:** tải Designer portable từ [GitHub Releases](https://github.com/Monkez/CustomPyQt6Designer/releases).
- **Chạy ứng dụng:** chỉ cài Python package. Không cần mang theo Designer `.exe`.

## Cài package cho ứng dụng

Cài trực tiếp từ GitHub:

```powershell
python -m pip install "custom-pyqt6-designer @ git+https://github.com/Monkez/CustomPyQt6Designer.git"
```

Sau đó ứng dụng có thể load file `.ui` chứa Monkez widgets:

```python
from pathlib import Path

from PyQt6 import uic
from PyQt6.QtWidgets import QApplication

from custom_pyqt6_designer import monkez_widgets  # đăng ký custom widget imports

app = QApplication([])
window = uic.loadUi(Path("ui/main_window.ui"))
window.show()
app.exec()
```

Header của custom widget trong file `.ui` phải là:

```xml
<header>custom_pyqt6_designer.monkez_widgets</header>
```

Xem project chạy hoàn chỉnh tại [demo_project](demo_project).

## Dùng Designer portable

1. Tải `MonkezPyQt6DesignerFull-*.zip` trong [Releases](https://github.com/Monkez/CustomPyQt6Designer/releases).
2. Giải nén toàn bộ thư mục.
3. Chạy `MonkezPyQt6DesignerFull.exe`.
4. Các widget nằm trong nhóm **Monkez Widgets** của Widget Box.

Bản portable đã chứa Qt Designer, PyQt6 Designer bridge, plugin Python và các runtime cần thiết.
Máy thiết kế không cần cài Python.

## Dependency tùy chọn

Package mặc định chỉ cài PyQt6. Camera và môi trường phát triển Designer được tách riêng:

```powershell
# Dùng MonkezUSBCamera
python -m pip install -e ".[camera]"

# Phát triển plugin bằng Python 3.11
python -m pip install -e ".[designer]"

# Cài đầy đủ
python -m pip install -e ".[all]"
```

`MonkezUSBCamera` import OpenCV theo nhu cầu, vì vậy các ứng dụng không dùng camera không phải cài OpenCV/Numpy.

## Chạy demo

```powershell
git clone https://github.com/Monkez/CustomPyQt6Designer.git
cd CustomPyQt6Designer
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe demo_project\main.py
```

Demo dùng `PyQt6.uic.loadUi()` và kết nối các widget bằng signal/slot thông thường.

## Danh sách widgets

| Nhóm | Widgets |
|---|---|
| Input | `MonkezTextInput`, `MonkezComboBox`, `MonkezSpinBox`, `MonkezDoubleSpinBox` |
| Action | `MonkezButton`, `MonkezSwitch`, `MonkezCheckBox`, `MonkezRadioButton` |
| Value | `MonkezSlider`, `MonkezDial`, `MonkezProgressBar`, `MonkezLCDNumber` |
| Date/time | `MonkezDateEdit`, `MonkezTimeEdit`, `MonkezDateTimeEdit`, `MonkezCalendarWidget` |
| Media | `MonkezImage`, `MonkezUSBCamera` |
| Container | `MonkezFrame`, `MonkezGroupBox`, `MonkezScrollArea` |

Các widget giao diện hỗ trợ:

- `themeIndex`: `0 Material`, `1 iOS`, `2 Fluent`, `3 Bootstrap`, `4 Minimal`, `5 Dark`.
- Context menu `Monkez Theme` trong Designer.
- Tùy chỉnh màu, radius, border, kích thước và các thuộc tính chuyên sâu.

`MonkezGroupBox` có header riêng, subtitle, accent, indicator, elevation và padding tùy chỉnh.

## MonkezImage và camera

`MonkezImage` cache pixmap đã scale theo source/kích thước và gộp repaint trong cùng event loop.

`MonkezUSBCamera` hỗ trợ:

- Backend: `auto`, `dshow`, `msmf`, `v4l2`, `avfoundation`, `gstreamer`, `ffmpeg`.
- Camera index/name/source, resolution, capture FPS, display FPS, FourCC và buffer size.
- Mirror, reconnect, auto start và preview bằng `Ctrl+R`.
- `displayFps` tách khỏi capture `fps` để giới hạn tải GUI.

## Phát triển

Khuyến nghị Python 3.11 khi chạy Designer bridge:

```powershell
py -3.11 -m venv .venv311
.\.venv311\Scripts\python.exe -m pip install --upgrade pip
.\.venv311\Scripts\python.exe -m pip install -e ".[all]"
.\.venv311\Scripts\custom-pyqt6-designer.exe
```

Chạy kiểm thử:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m unittest discover -s tests -v
```

Build package:

```powershell
python -m build
```

Build Designer portable:

```powershell
.\scripts\build_full_designer.ps1
```

## Tài liệu

- [Tích hợp package vào ứng dụng](docs/RUNTIME_INTEGRATION.md)
- [Designer portable và phát triển plugin](docs/DESIGNER_PORTABLE.md)
- [Project demo](demo_project/README.md)

## License

[MIT](LICENSE)
