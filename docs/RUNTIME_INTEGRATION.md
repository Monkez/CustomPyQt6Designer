# Tích hợp vào ứng dụng PyQt6

## Nguyên tắc

Qt Designer chỉ tạo và chỉnh sửa file `.ui`. Khi chạy ứng dụng, Python cần import được class custom widget được ghi trong phần `<customwidgets>` của file `.ui`.

Package này cung cấp toàn bộ class qua:

```python
custom_pyqt6_designer.monkez_widgets
```

Máy chạy ứng dụng không cần Designer portable.

## Cài đặt

```powershell
python -m pip install "custom-pyqt6-designer @ git+https://github.com/Monkez/CustomPyQt6Designer.git"
```

Nếu dùng camera:

```powershell
python -m pip install opencv-python
```

## Load file UI

```python
from PyQt6 import uic
from PyQt6.QtWidgets import QApplication

from custom_pyqt6_designer import monkez_widgets

app = QApplication([])
window = uic.loadUi("ui/main_window.ui")
window.show()
app.exec()
```

Có thể dùng class đích:

```python
from PyQt6 import uic
from PyQt6.QtWidgets import QMainWindow


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("ui/main_window.ui", self)
        self.applyButton.clicked.connect(self.apply_settings)

    def apply_settings(self):
        self.progressBar.setValue(75)
```

## Sinh Python bằng pyuic6

```powershell
pyuic6 ui\main_window.ui -o generated\ui_main_window.py
```

File sinh ra sẽ import custom widgets theo header:

```python
from custom_pyqt6_designer.monkez_widgets import MonkezButton
```

Không chỉnh sửa thủ công file generated; chỉnh `.ui` và chạy lại `pyuic6`.

## Đóng gói ứng dụng

Với PyInstaller, thêm import collection nếu công cụ không tự phát hiện class chỉ xuất hiện trong `.ui`:

```powershell
pyinstaller --collect-all custom_pyqt6_designer app.py
```

Nếu dùng camera, đảm bảo OpenCV được cài trong đúng virtualenv trước khi build.
