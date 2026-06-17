# Custom PyQt6 Designer

Custom PyQt6 Designer cung cấp hai phần tách biệt:

- **MonkezDesigner.exe**: bản Qt Designer portable đã cấu hình sẵn để load Monkez custom widgets.
- **Python package**: runtime để ứng dụng PyQt6 load file `.ui` có custom widgets mà không cần mang theo Designer.

Repo hiện có đủ plugin Designer, widget runtime, Gallery app, demo project và script build release.

## Cài package cho ứng dụng

Cài trực tiếp từ GitHub:

```powershell
python -m pip install --upgrade "custom-pyqt6-designer @ git+https://github.com/Monkez/CustomPyQt6Designer.git"
```

Nếu dùng camera:

```powershell
python -m pip install --upgrade "custom-pyqt6-designer[camera] @ git+https://github.com/Monkez/CustomPyQt6Designer.git"
```

Ứng dụng PyQt6 có thể load `.ui` như bình thường:

```python
from pathlib import Path

from PyQt6 import uic
from PyQt6.QtWidgets import QApplication

from custom_pyqt6_designer import monkez_widgets  # giúp uic tìm custom widget classes

app = QApplication([])
window = uic.loadUi(Path("ui/main_window.ui"))
window.show()
app.exec()
```

Header của custom widget trong file `.ui` phải là:

```xml
<header>custom_pyqt6_designer.monkez_widgets</header>
```

## Dùng Designer portable

1. Tải thư mục release `MonkezDesigner` từ [GitHub Releases](https://github.com/Monkez/CustomPyQt6Designer/releases).
2. Giữ nguyên toàn bộ cấu trúc thư mục sau khi giải nén.
3. Chạy `MonkezDesigner.exe`.
4. Các widget nằm trong nhóm **Monkez Widgets** của Widget Box.

Bản portable đã chứa Qt Designer, PyQt6 Designer bridge, plugin Python và runtime cần thiết. Máy thiết kế giao diện không cần cài Python.

## Gallery app

Sau khi cài package, chạy Gallery app để xem demo widget và docs thuộc tính/phương thức:

```powershell
monkez-gallery
```

Gallery chia thành các tab:

- **Controls**: button, input, combobox, checkbox, radio, switch.
- **Values**: slider, progress bar, spinbox, dial, LCD, date/time, calendar.
- **Media & Containers**: image, camera placeholder, frame, group box, scroll area.
- **Gauges**: radial, arc và linear gauge.
- **Docs**: danh sách widget, thuộc tính quan trọng, phương thức/signal và ví dụ dùng nhanh.

## Demo project

Project mẫu ở [demo_project](demo_project) dùng `PyQt6.uic.loadUi()` để chạy `.ui` có Monkez widgets:

```powershell
git clone https://github.com/Monkez/CustomPyQt6Designer.git
cd CustomPyQt6Designer
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe demo_project\main.py
```

## Danh sách widgets

| Nhóm | Widgets |
|---|---|
| Action | `MonkezButton`, `MonkezSwitch`, `MonkezCheckBox`, `MonkezRadioButton` |
| Input | `MonkezTextInput`, `MonkezComboBox`, `MonkezSpinBox`, `MonkezDoubleSpinBox` |
| Value | `MonkezSlider`, `MonkezDial`, `MonkezProgressBar`, `MonkezLCDNumber` |
| Date/time | `MonkezDateEdit`, `MonkezTimeEdit`, `MonkezDateTimeEdit`, `MonkezCalendarWidget` |
| Media | `MonkezImage`, `MonkezUSBCamera` |
| Container | `MonkezFrame`, `MonkezGroupBox`, `MonkezScrollArea` |
| Gauge | `MonkezRadialGauge`, `MonkezArcGauge`, `MonkezLinearGauge` |

Các widget giao diện hỗ trợ:

- `themeIndex`: `0 Material`, `1 iOS`, `2 Fluent`, `3 Bootstrap`, `4 Minimal`, `5 Dark`.
- Context menu `Monkez Theme` trong Designer.
- Tùy chỉnh màu, radius, border, padding, shadow và các thuộc tính chuyên sâu tùy widget.

## Ghi chú runtime

`MonkezImage` cache pixmap đã scale theo kích thước widget và device pixel ratio để hiển thị tốt trên màn hình high DPI.

`MonkezUSBCamera` import OpenCV theo nhu cầu, hỗ trợ backend, camera index/source/name, resolution, capture FPS, display FPS, FourCC, buffer size, mirror, reconnect, auto start và preview trong Designer khi bật `previewAutoStart`.

## Phát triển

Khuyến nghị Python 3.11 khi chạy Designer bridge:

```powershell
py -3.11 -m venv .venv311
.\.venv311\Scripts\python.exe -m pip install --upgrade pip
.\.venv311\Scripts\python.exe -m pip install -e ".[all]"
.\.venv311\Scripts\custom-pyqt6-designer.exe
```

Chạy test:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv311\Scripts\python.exe -m unittest discover -s tests -v
```

Build package:

```powershell
.\.venv311\Scripts\python.exe -m build
```

Build Designer portable:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_full_designer.ps1
```

Output chính:

- `dist\custom_pyqt6_designer-<version>-py3-none-any.whl`
- `dist\custom_pyqt6_designer-<version>.tar.gz`
- `dist\MonkezDesigner\MonkezDesigner.exe`

## Tài liệu

- [Tích hợp runtime vào ứng dụng](docs/RUNTIME_INTEGRATION.md)
- [Designer portable và phát triển plugin](docs/DESIGNER_PORTABLE.md)
- [Project demo](demo_project/README.md)

## License

[MIT](LICENSE)
