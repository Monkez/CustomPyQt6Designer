# Splash screen

## Mục tiêu

Splash screen được tối ưu để hiển thị ngay sau khi tạo `QApplication`. Đường import
không nạp Gallery, camera, OpenCV hoặc các widget không liên quan. Implementation
chỉ dùng PyQt6 nên không phát sinh tiến trình hay DLL native bổ sung.

Benchmark trên môi trường phát triển Python 3.11 cho thời gian từ đầu process đến
lần paint đầu khoảng 130–205 ms. Kết quả phụ thuộc máy và antivirus; có thể đo lại
bằng `benchmark_splash.bat`.

## Dùng nhanh nhất

```python
import sys

from PyQt6.QtWidgets import QApplication, QMainWindow
from custom_pyqt6_designer.splash import show_splash

app = QApplication(sys.argv)

splash = show_splash(
    app_name="Monkez Studio",
    app_version="Version 2.4",
    background_image="assets/splash.png",
    background_color="transparent",
    status="Starting...",
)

splash.set_progress(15, "Reading configuration...")
splash.set_progress(55, "Loading workspace...")

window = QMainWindow()
splash.set_progress(100, "Ready")
splash.finish(window)

sys.exit(app.exec())
```

Phải giữ reference `splash` cho đến khi gọi `finish()`.

## Cấu hình đầy đủ

```python
from custom_pyqt6_designer.splash import SplashConfig, SplashController

config = SplashConfig(
    app_name="Monkez Studio",
    app_version="Version 2.4",
    initial_status="Preparing...",
    background_image="assets/splash.png",
    background_color="transparent",
    text_color="#ffffff",
    accent_color="#38bdf8",
    image_mode=0,                 # 0 cover, 1 contain, 2 stretch
    size=(720, 420),
    initial_progress=0,
    minimum_visible_ms=600,
    fade_in_ms=160,
    fade_out_ms=220,
    progress_animation_ms=220,
    always_on_top=True,
    transparent_background=True,
    animation_enabled=True,
    show_progress=True,
    show_spinner=True,
    center_on_screen=True,
)

splash = SplashController.create(config).show()
```

## API cập nhật tiến trình

```python
splash.set_progress(35, "Loading plugins...")
splash.set_status("Connecting...")
splash.advance(10, "Loading next module...")
splash.set_stage(index=3, total=8, status="Stage 3 of 8")
splash.update(progress=80, status="Almost ready")
```

Các lệnh trên dùng Qt signal và có thể gọi từ worker thread:

```python
from threading import Thread


def load_data():
    splash.set_progress(20, "Opening database...")
    # Công việc nặng...
    splash.set_progress(80, "Preparing dashboard...")


Thread(target=load_data, daemon=True).start()
```

Không chạy tác vụ nặng trực tiếp trên GUI thread nếu muốn spinner và animation
tiếp tục mượt. Với chuỗi tác vụ nhỏ, có thể dùng `run_steps()`; controller sẽ
paint trước mỗi bước.

## Thiết kế bằng Monkez Designer

1. Mở [splash_screen.ui](../examples/splash_screen.ui) bằng `run.bat`.
2. Thay layout, label, màu, font, progress bar hoặc background tùy ý.
3. Giữ lại các `objectName` cần cập nhật:

| Object name | Vai trò |
|---|---|
| `splashAppNameLabel` | Tên ứng dụng |
| `splashVersionLabel` | Phiên bản |
| `splashStatusLabel` | Trạng thái khởi động |
| `splashProgressBar` | Tiến trình |

4. Load file thiết kế:

```python
splash = SplashController.from_ui(
    "ui/splash_screen.ui",
    SplashConfig(app_name="My App", app_version="Version 1.0"),
).show()
```

`MonkezSplashScreen` nằm trong nhóm `Monkez 06 Containers` và là container, vì
vậy có thể đặt thêm widget con. Property `defaultContentVisible` chọn giữa phần
giao diện mặc định được paint tối ưu và nội dung tùy biến bằng Designer.

## Ảnh PNG trong suốt

- Dùng PNG có alpha channel.
- Đặt `transparent_background=True`.
- Nếu chỉ muốn thấy nội dung PNG, đặt `background_color="transparent"`.
- `image_mode=0` crop ảnh theo kiểu cover; `1` giữ toàn bộ ảnh; `2` kéo giãn.
- Khi đóng gói, nên dùng Qt Resource hoặc copy ảnh bằng cấu hình PyInstaller.

## Khi nào cần C++ hoặc Rust

Không cần native binary cho đường hiện tại: phần tốn thời gian chủ yếu là khởi tạo
Qt và tạo native window, các bước này vẫn tồn tại nếu viết wrapper C++/Rust. Một
binary riêng còn cần IPC, đồng bộ lifetime và thêm artifact đóng gói.

Chỉ nên thêm native splash process khi benchmark trên máy mục tiêu chứng minh:

- thời gian paint đầu vượt SLA thực tế; hoặc
- ứng dụng phải hiển thị splash trước khi Python runtime được nạp.

Nếu cần bước đó, giao thức phù hợp là process nhận background/config qua command
line và nhận bản tin progress dạng JSON Lines qua stdin hoặc named pipe.
