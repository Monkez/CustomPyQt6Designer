# Monkez Custom Widget API

This document describes the Python runtime API for Monkez custom widgets. The same widgets can be configured in Qt Designer through the Property Editor, but application code should prefer the typed methods below instead of raw `setStyleSheet()` strings.

All examples assume:

```python
from PyQt6.QtGui import QColor
from monkez_pyqt6.monkez_widgets import (
    MonkezButton,
    MonkezTextInput,
    MonkezComboBox,
    MonkezSwitch,
    MonkezProgressBar,
    MonkezRadialGauge,
)
```

## Color Values

Most color methods accept any of these forms:

| Form | Example |
|---|---|
| CSS color name | `"white"` |
| Hex string | `"#2563eb"` |
| `QColor` | `QColor(37, 99, 235)` |
| RGB tuple/list | `(37, 99, 235)` |
| RGBA tuple/list | `(37, 99, 235, 180)` |

Invalid color strings raise `ValueError`.

## Theme Indexes

| Index | Theme |
|---:|---|
| `0` | Material |
| `1` | iOS |
| `2` | Fluent |
| `3` | Bootstrap |
| `4` | Minimal |
| `5` | Dark |

```python
button = MonkezButton()
button.setThemeIndex(1)      # iOS
button.setThemeName("dark")  # also supported by most widgets
```

## Fluent Styling Methods

Every Monkez widget class receives a small fluent API at import time. The methods return `self`, so you can chain them. The table below is the common reference; a method is only valid for a widget when that widget exposes the matching property role. If a widget does not support a role, the method raises `AttributeError` with a clear message. In the Gallery app, the Docs tab shows a per-widget **Supported runtime methods** table generated from the current implementation.

| Method | Purpose | Typical target properties |
|---|---|---|
| `setBackground(color)` | Set the main surface/background color. | `backgroundColor`, `activeColor`, `boxColor`, `trackColor`, `grooveColor` |
| `setForeground(color)` | Set text, digit, or foreground value color. | `textColor`, `digitColor`, `valueColor` |
| `setBorder(color)` | Set border color. | `borderColor` |
| `setAccent(color)` | Set the primary/accent/value color. | `accentColor`, `checkedColor`, `filledColor`, `valueColor`, `barColor`, `activeColor` |
| `setTrack(color)` | Set track/groove color. | `trackColor`, `grooveColor` |
| `setThumb(color)` | Set thumb/handle color. | `thumbColor`, `handleColor` |
| `setContentPadding(x, y=None)` | Set padding for widgets that expose padding. | `paddingX/paddingY`, `padding`, `contentPadding` |
| `setSizeTokens(radius=None, border_width=None, control_height=None)` | Set shape/size tokens in one call. | `radius`, `borderWidth`, `controlHeight`, `barHeight`, `grooveHeight` |
| `setShadow(enabled=True, blur=None, offset_x=None, offset_y=None, color=None)` | Configure shadow-capable widgets. | `shadowEnabled`, `shadowBlur`, `shadowOffsetX/Y`, `shadowColor` |
| `setColors(**roles)` | Set several color roles in one call. | See role table below |

Supported `setColors()` roles:

| Role | Calls |
|---|---|
| `background`, `surface` | `setBackground()` |
| `foreground`, `text` | `setForeground()` |
| `border` | `setBorder()` |
| `accent`, `primary` | `setAccent()` |
| `track` | `setTrack()` |
| `thumb`, `handle` | `setThumb()` |

Example:

```python
button = (
    MonkezButton()
    .setBackground("#2563eb")
    .setForeground("#ffffff")
    .setContentPadding(10, 6)
    .setSizeTokens(radius=8)
    .setShadow(True, blur=18, offset_y=4, color=(15, 23, 42, 80))
)
button.setText("Save")
```

## Widget Properties

Designer properties are also available from Python through normal getter/setter pairs. For example,
`radius` maps to `getRadius()` / `setRadius(value)`, `themeIndex` maps to
`getThemeIndex()` / `setThemeIndex(value)`, and `buttonTypeIndex` maps to
`getButtonTypeIndex()` / `setButtonTypeIndex(value)`. The fluent methods below are convenience
wrappers for the most common styling roles; use the specific setters when you need a widget-specific
property.

### MonkezButton

| Property | Type | Description |
|---|---|---|
| `themeIndex` | `int` | Numeric theme preset. |
| `buttonTypeIndex` | `int` | `0 Filled`, `1 Outlined`, `2 Text`. |
| `active` | `bool` | Switches between active and deactive color. |
| `activeColor` | `QColor` | Filled background; Outlined border/accent color. |
| `deactiveColor` | `QColor` | Disabled-like custom inactive color. |
| `textColor` | `QColor` | Normal text color, including Outlined mode. |
| `hoverTextColor` | `QColor` | Text color while hover/pressed. |
| `paddingX`, `paddingY` | `int` | Internal button padding. |
| `radius` | `int` | Corner radius. |
| `shadowEnabled`, `shadowBlur`, `shadowOffsetX/Y`, `shadowColor` | mixed | Shadow controls. |

| Method | Description |
|---|---|
| `setBackground(color)` | Sets `activeColor`. |
| `setAccent(color)` | Sets `activeColor`. |
| `setForeground(color)` | Sets `textColor`. |
| `setContentPadding(x, y)` | Sets `paddingX` and `paddingY`. |
| `setButtonTypeIndex(index)` | Changes filled/outlined/text style. |
| `setShadow(...)` | Configures drop shadow. |

```python
button = MonkezButton()
button.setText("Delete")
button.setButtonTypeIndex(1)  # outlined
button.setAccent("#ef4444").setForeground("#ef4444")
button.setContentPadding(8, 4).setSizeTokens(radius=10)
```

Ở chế độ `Outlined`, viền luôn lấy từ `activeColor` khi `active=True`
(`deactiveColor` khi `active=False`), còn chữ lấy từ `textColor`.
Khi hover/pressed, chữ dùng `hoverTextColor` và viền vẫn được dẫn xuất từ
`activeColor`.

### MonkezTextInput

| Property | Type | Description |
|---|---|---|
| `themeIndex` | `int` | Numeric theme preset. |
| `backgroundColor` | `QColor` | Input surface color. |
| `borderColor` | `QColor` | Input border color. |
| `textColor` | `QColor` | Text color. |
| `padding` | `int` | Base padding. |
| `leadingIcon`, `trailingIcon` | `str` | Asset icon file names. |
| `leadingIconSize`, `trailingIconSize` | `int` | Icon size in px. |
| `shadowEnabled`, `shadowBlur`, `shadowOffsetX/Y`, `shadowColor` | mixed | Shadow controls. |

| Method | Description |
|---|---|
| `setBackground(color)` | Sets `backgroundColor`. |
| `setForeground(color)` | Sets `textColor`. |
| `setBorder(color)` | Sets `borderColor`. |
| `setColors(background=..., text=..., border=...)` | Updates multiple roles. |
| `setLeadingIcon(name)`, `setTrailingIcon(name)` | Sets icon assets. |
| `trailingIconClicked` | Signal emitted when the trailing icon is clicked. |

```python
search = MonkezTextInput()
search.setPlaceholderText("Search customer...")
search.setLeadingIcon("search.png")
search.setTrailingIcon("clear.png")
search.setColors(background="#ffffff", text="#0f172a", border="#cbd5e1")
search.trailingIconClicked.connect(search.clear)
```

### MonkezComboBox

`MonkezComboBox` mặc định không có item. Thêm item trong Designer bằng editor
`items` hoặc gọi `addItem()`/`addItems()` ở runtime.

| Property | Type | Description |
|---|---|---|
| `themeIndex` | `int` | Numeric theme preset. |
| `backgroundColor` | `QColor` | Control and popup background. |
| `borderColor` | `QColor` | Control border color. |
| `hoverBackgroundColor` | `QColor` | Popup item hover/selected background. |
| `textColor` | `QColor` | Text color. |
| `hoverTextColor` | `QColor` | Hover/selected text color. |
| `borderRadius` | `int` | Control and popup radius. |
| `font` | `QFont` | Font family, point size, weight and style for both the control and popup items. |

Trong Designer, mở property `font` rồi chỉnh `Point Size`; preview của control
và danh sách popup sẽ cùng dùng giá trị này.

| Method | Description |
|---|---|
| `setBackground(color)` | Sets `backgroundColor`. |
| `setBorder(color)` | Sets `borderColor`. |
| `setForeground(color)` | Sets `textColor`. |
| `addItemWithIcon(path, text, data=None)` | Adds icon item. |
| `addItemWithPixmap(pixmap, text, data=None)` | Adds pixmap item. |

```python
combo = MonkezComboBox()
combo.clear()
combo.addItems(["Auto", "Manual", "Disabled"])
font = combo.font()
font.setPointSize(14)
combo.setFont(font)
combo.setColors(background="#f8fafc", text="#111827", border="#94a3b8")
```

### MonkezCheckBox and MonkezRadioButton

| Property | Widget | Description |
|---|---|---|
| `boxColor` | CheckBox | Unchecked box fill color. |
| `backgroundColor` | RadioButton | Indicator/card/pill background color. |
| `checkedColor` | Both | Checked/accent color. |
| `borderColor` | Both | Indicator/card border. |
| `textColor` | Both | Label text color. |
| `indicatorSize` | Both | Indicator size. |
| `radioStyle` | RadioButton | `0 Classic`, `1 Card`, `2 Pill`. |
| `shadowEnabled` | RadioButton | Enables shadow on radio card/pill styles. |

| Method | Description |
|---|---|
| `setBackground(color)` | CheckBox: sets `boxColor`; RadioButton: sets `backgroundColor`. |
| `setAccent(color)` | Sets checked/accent color. |
| `setBorder(color)` | Sets border color. |
| `setForeground(color)` | Sets label text color. |
| `setShadow(...)` | RadioButton only. |

```python
radio = MonkezRadioButton()
radio.setRadioStyle(2)
radio.setText("iOS")
radio.setAccent("#0ea5e9").setBorder("#7dd3fc").setForeground("#0f172a")
```

### MonkezSwitch

| Property | Type | Description |
|---|---|---|
| `trackColor` | `QColor` | Off-state track color. |
| `checkedColor` | `QColor` | On-state track/accent color. |
| `thumbColor` | `QColor` | Thumb color. |
| `textColor` | `QColor` | Optional text color. |
| `showText` | `bool` | Shows `onText` or `offText` next to the switch. |
| `onText`, `offText` | `str` | Text labels. |

| Method | Description |
|---|---|
| `setTrack(color)` | Sets `trackColor`. |
| `setThumb(color)` | Sets `thumbColor`. |
| `setAccent(color)` | Sets `checkedColor`. |
| `setForeground(color)` | Sets `textColor`. |

```python
switch = MonkezSwitch()
switch.setShowText(True)
switch.setOnText("Live")
switch.setOffText("Paused")
switch.setTrack("#e2e8f0").setAccent("#22c55e").setThumb("#ffffff")
```

### Sliders, Progress Bars, Dials, LCD and Gauges

| Widget | Important Properties |
|---|---|
| `MonkezSlider` | `grooveColor`, `filledColor`, `handleColor`, `grooveHeight`, `handleSize` |
| `MonkezProgressBar` | `barColor`, `trackColor`, `textColor`, `barHeight`, `radius` |
| `MonkezDial` | `trackColor`, `valueColor`, `handleColor`, `trackWidth`, `handleSize`, `dialStyle` |
| `MonkezLCDNumber` | `backgroundColor`, `digitColor`, `borderColor`, `radius` |
| `MonkezRadialGauge` | `trackColor`, `valueColor`, `textColor`, `warningColor`, `dangerColor` |
| `MonkezArcGauge` | `arcWidth`, `warningThreshold`, `dangerThreshold`, `segmented`, `segmentCount` |
| `MonkezLinearGauge` | `vertical`, `barThickness`, `targetValue`, `showTarget`, `rounded` |

| Method | Description |
|---|---|
| `setTrack(color)` | Sets track/groove color when available. |
| `setAccent(color)` | Sets filled/bar/value color. |
| `setThumb(color)` | Sets slider/dial handle color. |
| `setForeground(color)` | Sets text/digit/value color when available. |
| `setSizeTokens(control_height=...)` | Sets bar/groove height on supported widgets. |
| `setShadow(...)` | Available on `MonkezDial` and gauges. |

```python
progress = MonkezProgressBar()
progress.setValue(72)
progress.setTrack("#e0f2fe").setAccent("#0284c7").setForeground("#0f172a")
progress.setSizeTokens(radius=4, control_height=8)
progress.setTextVisible(False)

gauge = MonkezRadialGauge()
gauge.setRange(0, 100)
gauge.setValue(64)
gauge.setLabel("Pressure")
gauge.setAccent("#16a34a").setTrack("#dcfce7").setForeground("#052e16")
```

### Date and Time Widgets

| Widget | Important Properties |
|---|---|
| `MonkezDateEdit` | `backgroundColor`, `borderColor`, `textColor`, `accentColor`, `controlHeight`, `radius` |
| `MonkezTimeEdit` | `backgroundColor`, `borderColor`, `textColor`, `accentColor`, `controlHeight`, `radius` |
| `MonkezDateTimeEdit` | `backgroundColor`, `borderColor`, `textColor`, `accentColor`, `controlHeight`, `radius` |
| `MonkezCalendarWidget` | `backgroundColor`, `textColor`, `accentColor`, `weekendColor`, `todayColor`, `outsideMonthColor`, `radius` |

| Method | Description |
|---|---|
| `setBackground(color)` | Sets input/calendar background. |
| `setBorder(color)` | Sets input border where available. |
| `setForeground(color)` | Sets text color. |
| `setAccent(color)` | Sets calendar icon/selection/accent color. |
| `setSizeTokens(control_height=...)` | Sets control height for date/time edits. |

```python
date_edit = MonkezDateEdit()
date_edit.setDisplayFormat("dd/MM/yyyy")
date_edit.setColors(background="#ffffff", text="#0f172a", border="#94a3b8", accent="#2563eb")
date_edit.setSizeTokens(control_height=34, radius=8)
```

### Containers

| Widget | Important Properties |
|---|---|
| `MonkezFrame` | `backgroundColor`, `borderColor`, `radius`, `borderWidth`, `elevation` |
| `MonkezGroupBox` | `title`, `subtitle`, `subtitleVisible`, `backgroundColor`, `headerColor`, `borderColor`, `titleColor`, `subtitleColor`, `accentColor`, `contentPadding`, `autoHeaderHeight` |
| `MonkezScrollArea` | `backgroundColor`, `borderColor`, `scrollbarColor`, `scrollbarTrackColor`, `scrollbarWidth`, `radius` |

| Method | Description |
|---|---|
| `setBackground(color)` | Sets container background. |
| `setBorder(color)` | Sets border color. |
| `setAccent(color)` | Sets group-box accent color. |
| `setForeground(color)` | GroupBox: sets title color where supported. |
| `setContentPadding(value)` | GroupBox: sets content padding. |
| `setSizeTokens(radius=..., border_width=...)` | Sets radius/border width. |

```python
box = MonkezGroupBox()
box.setTitle("Camera")
box.setSubtitle("USB source configuration")
box.setColors(background="#ffffff", border="#cbd5e1", accent="#2563eb")
box.setContentPadding(14)
box.setSubtitleVisible(False)
```

`MonkezScrollArea` giữ nguyên cơ chế của `QScrollArea`; thư viện chỉ bổ sung theme
và các property giao diện trong bảng trên. Khi tạo trực tiếp bằng Python, widget
khởi đầu chưa có trang nội dung và giữ mặc định `widgetResizable` của Qt. Hãy tạo
`QWidget`, gọi `scroll.setWidget(content)` và bật `setWidgetResizable(True)` khi
ứng dụng cần.

Khi kéo mới trong Designer, plugin tạo cấu trúc chuẩn của Qt gồm trang
`scrollAreaWidgetContents` và bật `widgetResizable`. Kéo widget con vào trang này,
áp dụng layout như với `QScrollArea` mặc định; Designer và runtime đều truy cập
trang bằng `scroll.widget()`.

### Media

| Widget | Important Properties |
|---|---|
| `MonkezImage` | `imageFile`, `backgroundColor`, `scaleModeIndex`, `smoothScaling` |
| `MonkezUSBCamera` | `backend`, `cameraIndex`, `cameraSource`, `cameraName`, `resolutionWidth`, `resolutionHeight`, `fps`, `displayFps`, `fourcc`, `bufferSize`, `mirror`, `autoStart`, `previewAutoStart`, `reconnect`, `stopOnHide` |

| Method | Description |
|---|---|
| `setBackground(color)` | Sets image/camera frame background. |
| `setImageFile(path)` | Loads an image from `str`, `bytes` or `pathlib.Path`. |
| `set_image(source, color_order="bgr")` | Loads `QPixmap`, `QImage`, NumPy frame or file path. |
| `setImage(source, color_order="bgr")` | Qt-style alias of `set_image`. |
| `setFrame(frame, color_order="bgr")` | Displays a NumPy/OpenCV frame directly. |
| `setScaleMode(mode)` | Sets `Fit`, `Fill`, `Stretch` or `Original` scaling. |
| `startCamera()` / `stopCamera()` / `restartCamera()` | Camera lifecycle. |

Trong Designer, nhấp chuột phải vào `MonkezImage` và chọn `Image Scale: Fit`,
`Fill`, `Stretch` hoặc `Original`. Property `scaleModeIndex` lưu lựa chọn trong
file `.ui` theo bảng sau:

| Mode | Behavior |
|---|---|
| `Fit` | Giữ đúng tỉ lệ, thu/phóng để thấy toàn bộ ảnh trong container. |
| `Fill` | Giữ đúng tỉ lệ, phủ kín container và cắt phần ảnh dư. |
| `Stretch` | Kéo ảnh phủ kín container, có thể thay đổi tỉ lệ. |
| `Original` | Giữ kích thước gốc và căn giữa, phần dư bị cắt. |

`styleSheet` của `MonkezImage` được áp dụng trực tiếp lên vùng hiển thị ngoài
cùng, không còn một `QFrame` con có style cố định che lên. Trong Designer có
thể nhập trực tiếp các khai báo hoặc dùng selector `MonkezImage` để đặt border,
nền và bo góc, ví dụ:

```css
MonkezImage {
    background-color: #020617;
    border: 2px solid #38bdf8;
    border-radius: 16px;
}
```

```python
from pathlib import Path

image = MonkezImage()
image.setBackground("#020617")
image.setScaleMode(MonkezImage.ScaleMode.Fit)
image.setSmoothScaling(True)
image.setImageFile("assets/splash.png")

# File path trực tiếp, bao gồm pathlib.Path
image.set_image(Path("assets/photo.png"))

# OpenCV trả về uint8 BGR/BGRA nên không cần cvtColor
ok, frame = camera_capture.read()
if ok:
    image.setFrame(frame)

# Frame từ PIL hoặc nguồn RGB/RGBA
image.set_image(rgb_frame, color_order="rgb")

# Có thể truyền source ngay khi khởi tạo
preview = MonkezImage(source=frame)

camera = MonkezUSBCamera()
camera.setBackend("dshow")
camera.setCameraIndex(0)
camera.setResolutionWidth(1280)
camera.setResolutionHeight(720)
camera.setDisplayFps(20)
camera.setMirror(True)
```

Frame NumPy phải có `dtype=uint8` và một trong các shape `H×W`, `H×W×1`,
`H×W×3` hoặc `H×W×4`. Mặc định `color_order="bgr"` phù hợp với OpenCV;
dùng `"rgb"`/`"rgba"` cho nguồn RGB. Widget sao chép frame sang bộ nhớ Qt,
vì vậy caller có thể tái sử dụng hoặc thay đổi buffer NumPy ngay sau lời gọi.
NumPy chỉ được import khi truyền `ndarray`, nên tải ảnh từ file hoặc Qt image
không làm chậm thời gian import thư viện.

`MonkezImage` dùng size policy `Ignored` theo cả hai chiều và minimum size hint
`0×0`. Vì vậy kích thước nguồn ảnh và scale mode không được phép làm thay đổi
geometry của widget: layout/container bên ngoài cấp kích thước trước, sau đó
`Fit`, `Fill`, `Stretch` hoặc `Original` chỉ scale pixmap bên trong vùng đó.

Để widget tự co giãn khi cửa sổ/container đổi kích thước trong Designer, hãy đặt
`MonkezImage` vào layout của container (Vertical, Horizontal, Grid hoặc Form).
Một child widget không nằm trong layout sẽ giữ geometry cố định theo cơ chế chuẩn
của Qt và không thể tự bám theo parent.

### MonkezSplashScreen

`MonkezSplashScreen` là container splash nhẹ, hỗ trợ nội dung mặc định được paint
trực tiếp hoặc child widgets thiết kế bằng Qt Designer.

Đây là widget gốc của một form splash độc lập nên không xuất hiện trong Widget
Box. Tạo form bằng `new_splash.bat` hoặc tùy chọn `--new-splash`; plugin Designer
chỉ dùng để mở và chỉnh sửa template đó.

| Property | Mô tả |
|---|---|
| `appName`, `appVersion`, `statusText` | Thông tin ứng dụng và trạng thái |
| `progress`, `showProgress` | Giá trị và hiển thị tiến trình |
| `backgroundImage`, `imageMode` | PNG background; cover/contain/stretch |
| `transparentBackground` | Cho phép alpha của cửa sổ |
| `showSpinner`, `spinnerInterval` | Spinner và tốc độ animation |
| `animationEnabled`, `animationDuration` | Animation progress mặc định |
| `defaultContentVisible` | Dùng UI paint sẵn hoặc child widgets tùy biến |
| `backgroundColor`, `textColor`, `accentColor`, `trackColor` | Màu giao diện |

```python
from monkez_pyqt6.splash import SplashConfig, SplashController

splash = SplashController.create(
    SplashConfig(
        app_name="Monkez Studio",
        app_version="Version 0.4",
        background_image="assets/splash.png",
    )
).show()
splash.set_progress(60, "Loading workspace...")
```

Xem `docs/SPLASHSCREEN.md` để dùng worker thread và file `.ui` tùy biến.

## Full Example

```python
from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget
from monkez_pyqt6.monkez_widgets import MonkezButton, MonkezTextInput, MonkezProgressBar

app = QApplication([])
window = QWidget()
layout = QVBoxLayout(window)

name = MonkezTextInput()
name.setPlaceholderText("Operator name")
name.setLeadingIcon("search.png")
name.setColors(background="#ffffff", text="#111827", border="#cbd5e1")

submit = (
    MonkezButton()
    .setBackground("#2563eb")
    .setForeground("#ffffff")
    .setContentPadding(12, 7)
    .setSizeTokens(radius=10)
    .setShadow(True, blur=18, offset_y=5, color=(15, 23, 42, 70))
)
submit.setText("Start")

progress = MonkezProgressBar()
progress.setValue(38)
progress.setTrack("#dbeafe").setAccent("#2563eb").setForeground("#1e3a8a")

layout.addWidget(name)
layout.addWidget(submit)
layout.addWidget(progress)
window.show()
app.exec()
```
