# Tích hợp vào ứng dụng PyQt6

## Nguyên tắc

Qt Designer chỉ tạo và chỉnh sửa file `.ui`. Khi chạy ứng dụng, Python cần import được class custom widget được ghi trong phần `<customwidgets>` của file `.ui`.

Package này cung cấp toàn bộ class qua:

```python
monkez_pyqt6.monkez_widgets
```

Máy chạy ứng dụng không cần Designer portable.

## Cài đặt

```powershell
python -m pip install "monkez-pyqt6 @ git+https://github.com/Monkez/CustomPyQt6Designer.git"
```

Nếu dùng camera:

```powershell
python -m pip install "monkez-pyqt6[camera] @ git+https://github.com/Monkez/CustomPyQt6Designer.git"
```

## Load file UI

### Cách ngắn gọn

```python
from PyQt6.QtWidgets import QApplication

from monkez_pyqt6 import load_ui

app = QApplication([])
window = load_ui("ui/main_window.ui")
window.show()
app.exec()
```

`load_ui()` tự đăng ký Monkez custom widgets, nhận `str` hoặc `pathlib.Path`,
kiểm tra file tồn tại và trả về đúng top-level widget khai báo trong Designer.

### Nạp vào `QMainWindow` hoặc `QWidget` có sẵn

```python
from PyQt6.QtWidgets import QMainWindow

from monkez_pyqt6 import load_ui


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        load_ui("ui/main_window.ui", self)
        self.applyButton.clicked.connect(self.apply_settings)

    def apply_settings(self):
        self.progressBar.setValue(75)
```

Có thể viết tương đương bằng `load_ui_into(self, "ui/main_window.ui")`, hoặc
dùng mixin:

```python
from PyQt6.QtWidgets import QWidget
from monkez_pyqt6 import UiLoaderMixin


class SettingsPanel(UiLoaderMixin, QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.load_ui("ui/settings_panel.ui")
```

Để tạo một form con và gắn Qt parent ngay:

```python
panel = load_ui("ui/settings_panel.ui", parent=main_window)
main_window.contentLayout.addWidget(panel)
```

Không truyền đồng thời `base_instance` và `parent`: `base_instance` dùng khi
file `.ui` mô tả chính object hiện tại, còn `parent` dùng khi tạo object mới.

## Chuyển từ tên package cũ

Tên distribution chuẩn từ 0.5 là `monkez-pyqt6`; namespace import chuẩn là
`monkez_pyqt6`. Namespace `custom_pyqt6_designer` và launcher cũ vẫn được đóng
gói để form/project hiện tại tiếp tục chạy, nhưng không nên dùng cho code mới.

## Sinh Python bằng pyuic6

```powershell
pyuic6 ui\main_window.ui -o generated\ui_main_window.py
```

File sinh ra sẽ import custom widgets theo header:

```python
from monkez_pyqt6.monkez_widgets import MonkezButton
```

Không chỉnh sửa thủ công file generated; chỉnh `.ui` và chạy lại `pyuic6`.

## Đóng gói ứng dụng

Với PyInstaller, thêm import collection nếu công cụ không tự phát hiện class chỉ xuất hiện trong `.ui`:

```powershell
pyinstaller --collect-all monkez_pyqt6 app.py
```

Nếu dùng camera, đảm bảo OpenCV được cài trong đúng virtualenv trước khi build.
