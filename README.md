# Custom PyQt6 Designer

Custom PyQt6 Designer cung cấp hai phần tách biệt:

- **MonkezDesigner.exe**: bản Qt Designer portable đã cấu hình sẵn để load Monkez custom widgets.
- **Python package**: runtime để ứng dụng PyQt6 load file `.ui` có custom widgets mà không cần mang theo Designer.

Repo hiện có đủ plugin Designer, widget runtime, Gallery app, demo project và script build release.

## Cài đặt dễ nhất

Chọn đúng một trong ba cách:

| Nhu cầu | Cách thực hiện |
|---|---|
| Chỉ thiết kế UI, không muốn cài Python | Tải `MonkezDesigner-<version>-windows-x64.zip`, giải nén và mở `Open Monkez Designer.bat`. |
| Cài Designer vào Windows hiện tại | Tải source ZIP, giải nén và double-click `install_designer.bat`. Không cần quyền admin. |
| Chỉ chạy Monkez widget trong app Python | Cài runtime package bằng `pip`; không cần cài Designer. |

Bộ cài theo user tự tạo môi trường Python cô lập trong
`%LOCALAPPDATA%\MonkezDesigner`, kiểm tra dependency và tạo shortcut cho
Designer, Docs Lab và Uninstall. Sau khi cài package, có thể kiểm tra bất kỳ lúc
nào:

```powershell
python -m custom_pyqt6_designer --doctor
python -m custom_pyqt6_designer
```

Xem [hướng dẫn cài đặt đầy đủ](docs/INSTALLATION.md).

## Splash screen khởi động nhanh

Phiên bản 0.4 bổ sung `MonkezSplashScreen` và controller tối ưu startup:

- Hiển thị tên/phiên bản ứng dụng và trạng thái khởi động.
- PNG trong suốt, background cover/contain/stretch.
- Progress animation, spinner, fade in/out và minimum display time.
- Cập nhật thuận tiện, an toàn từ worker thread.
- Thiết kế lại bằng Monkez Designer và nạp file `.ui`.
- Lazy-loading, không nạp camera/OpenCV/Gallery trên đường khởi động splash.

```python
from PyQt6.QtWidgets import QApplication
from custom_pyqt6_designer.splash import show_splash

app = QApplication([])
splash = show_splash(
    app_name="Monkez Studio",
    app_version="Version 0.4",
    background_image="assets/splash.png",
)
splash.set_progress(40, "Loading plugins...")
```

Tạo một form splash độc lập bằng `new_splash.bat` hoặc:

```powershell
python -m custom_pyqt6_designer --new-splash ui/splash_screen.ui
```

Splash không xuất hiện trong bảng widget kéo-thả vì nó là một cửa sổ độc lập.
Plugin vẫn được nạp để Designer có thể hiển thị và chỉnh sửa template đúng như
lúc chạy. Xem [hướng dẫn splash screen](docs/SPLASHSCREEN.md).

Demo tải nền nặng có sẵn dưới dạng Windows executable. Chạy
`run_splash_exe_demo.bat`, hoặc tự build lại bằng `build_splash_demo.bat`.
Ứng dụng xử lý dữ liệu và CPU trên worker thread trong khi splash vẫn nhận
tiến trình và animation mượt. Khóa khởi động liên tiến trình ngăn double-click
mở trùng trong lúc đang tải, nhưng tự nhả khi app sẵn sàng để cho phép mở thêm
instance có chủ đích. Xem
[hướng dẫn Heavy Splash Demo](docs/HEAVY_SPLASH_DEMO.md).

## Bắt đầu nhanh trên Windows

Nếu phát triển trực tiếp từ repository, cài Python 3.11 rồi chạy:

```powershell
setup.bat
run.bat
```

Các script tiện dụng:

| Script | Chức năng |
|---|---|
| `setup.bat` | Tạo `.venv311` và cài đầy đủ dependency đã kiểm soát phiên bản. |
| `install_designer.bat` | Cài Designer theo user, kiểm tra và tạo shortcut; không cần quyền admin. |
| `uninstall_designer.bat` | Gỡ bản Designer đã cài theo user. |
| `run.bat` | Mở Qt Designer cùng Monkez plugins. |
| `new_splash.bat` | Tạo và mở một form splash độc lập, không lồng trong container khác. |
| `gallery.bat` | Mở Docs Lab. |
| `demo.bat` | Chạy project mẫu. |
| `splash_demo.bat` | Chạy demo splash screen thiết kế bằng Designer. |
| `benchmark_splash.bat` | Đo thời gian import và paint đầu. |
| `build_splash_demo.bat` | Build và xác minh app EXE demo tải nền nặng. |
| `run_splash_exe_demo.bat` | Mở app EXE demo tải nền nặng. |
| `test.bat` | Chạy toàn bộ test ở chế độ không cần màn hình. |
| `build.bat` | Build package, Designer portable, kiểm tra plugin và tạo ZIP. |

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
4. Trong Widget Box, tìm các nhóm đánh số từ **Monkez 01 Controls** đến **Monkez 07 Media**.

Bản portable đã chứa Qt Designer, PyQt6 Designer bridge, plugin Python và runtime cần thiết. Máy thiết kế giao diện không cần cài Python.

## Docs Lab app

Sau khi cài package, chạy Docs Lab để xem docs thuộc tính/phương thức, live preview của từng widget và thử trực tiếp các runtime method:

```powershell
monkez-gallery
```

Docs Lab chỉ tập trung vào tài liệu tương tác:

- Danh sách custom widgets.
- Bảng properties và supported runtime methods được kiểm tra từ implementation hiện tại.
- Live preview riêng cho widget đang chọn.
- Ô nhập method như `setThemeIndex(1)`, `setBackground("#2563eb")`, `setColors(accent="#22c55e")`.
- Bảng màu nhanh, format màu và color picker để copy mã màu tiện dùng.
- Nút Reset để đưa preview về trạng thái mặc định.

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
| Startup | `MonkezSplashScreen` |

Các widget giao diện hỗ trợ:

- `themeIndex`: `0 Material`, `1 iOS`, `2 Fluent`, `3 Bootstrap`, `4 Minimal`, `5 Dark`.
- Context menu `Monkez Theme` trong Designer có đủ sáu theme.
- Tùy chỉnh màu, radius, border, padding, shadow và các thuộc tính chuyên sâu tùy widget.

## Ghi chú runtime

`MonkezImage` cache pixmap theo kích thước widget và device pixel ratio để hiển
thị tốt trên màn hình high DPI. Menu chuột phải của widget trong Designer có
bốn lựa chọn scale `Fit`, `Fill`, `Stretch` và `Original`; lựa chọn được lưu
bằng property `scaleModeIndex`.

Widget nhận trực tiếp `QPixmap`, `QImage`, đường dẫn `str`/`pathlib.Path` và
NumPy `uint8` frame qua `set_image()`. Frame OpenCV BGR/BGRA dùng
`setFrame(frame)` mà không cần `cv2.cvtColor`; với nguồn RGB dùng
`set_image(frame, color_order="rgb")`. NumPy được nạp theo nhu cầu nên không
ảnh hưởng tốc độ khởi động khi chỉ dùng file ảnh.

Khi nằm trong layout, `MonkezImage` luôn nhận toàn bộ kích thước do container
ngoài cấp; kích thước ảnh nguồn không chi phối geometry của widget. Các mode
`Fit`, `Fill`, `Stretch`, `Original` chỉ thay đổi pixmap hiển thị bên trong.

`MonkezScrollArea` dùng nguyên cơ chế container của `QScrollArea`, chỉ bổ sung
theme và các property màu, border, radius, scrollbar. Trong Designer, kéo widget
con vào `scrollAreaWidgetContents` như Scroll Area mặc định. Khi tạo bằng Python,
hãy dùng `setWidget()` và `setWidgetResizable()` theo API chuẩn của Qt.

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
build.bat
```

Output chính:

- `dist\custom_pyqt6_designer-<version>-py3-none-any.whl`
- `dist\custom_pyqt6_designer-<version>.tar.gz`
- `dist\MonkezDesigner\MonkezDesigner.exe`
- `dist\MonkezDesigner-<version>-windows-x64.zip`

## Tài liệu

- [Tích hợp runtime vào ứng dụng](docs/RUNTIME_INTEGRATION.md)
- [Designer portable và phát triển plugin](docs/DESIGNER_PORTABLE.md)
- [Monkez custom widget Python API](docs/WIDGET_API.md)
- [Project demo](demo_project/README.md)
- [Hướng dẫn cài đặt và sử dụng](docs/INSTALLATION.md)
- [Splash screen khởi động nhanh](docs/SPLASHSCREEN.md)

## License

[MIT](LICENSE)
