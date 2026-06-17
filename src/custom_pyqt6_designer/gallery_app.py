from __future__ import annotations

import html
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, unquote

from PyQt6.QtCore import QDate, QDateTime, Qt, QTime, QTimer, QUrl
from PyQt6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QColorDialog,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .monkez_widgets import (
    MonkezArcGauge,
    MonkezButton,
    MonkezCalendarWidget,
    MonkezCheckBox,
    MonkezComboBox,
    MonkezDateEdit,
    MonkezDateTimeEdit,
    MonkezDial,
    MonkezDoubleSpinBox,
    MonkezFrame,
    MonkezGroupBox,
    MonkezImage,
    MonkezLCDNumber,
    MonkezLinearGauge,
    MonkezProgressBar,
    MonkezRadioButton,
    MonkezRadialGauge,
    MonkezScrollArea,
    MonkezSlider,
    MonkezSpinBox,
    MonkezSwitch,
    MonkezTextInput,
    MonkezTimeEdit,
    MonkezUSBCamera,
)


@dataclass(frozen=True)
class WidgetDoc:
    name: str
    group: str
    purpose: str
    properties: tuple[str, ...]
    methods: tuple[str, ...]
    usage: str


THEME_NAMES = ("Material", "iOS", "Fluent", "Bootstrap", "Minimal", "Dark")
GALLERY_TABS = ("Docs",)
COLOR_VALUE_DOCS = (
    ("CSS name", '"white"'),
    ("Hex string", '"#2563eb"'),
    ("QColor", "QColor(37, 99, 235)"),
    ("RGB tuple/list", "(37, 99, 235)"),
    ("RGBA tuple/list", "(37, 99, 235, 180)"),
)
COLOR_SWATCHES = (
    ("Blue", "#2563eb"),
    ("Sky", "#0ea5e9"),
    ("Cyan", "#06b6d4"),
    ("Emerald", "#10b981"),
    ("Green", "#22c55e"),
    ("Lime", "#84cc16"),
    ("Amber", "#f59e0b"),
    ("Orange", "#f97316"),
    ("Red", "#ef4444"),
    ("Rose", "#f43f5e"),
    ("Pink", "#ec4899"),
    ("Purple", "#8b5cf6"),
    ("Indigo", "#6366f1"),
    ("Slate", "#475569"),
    ("Dark", "#111827"),
    ("White", "#ffffff"),
)
COLOR_FORMATS = ("Hex", "RGB tuple", "RGBA tuple", "QColor")
FLUENT_METHOD_DOCS = (
    ("setThemeIndex(index)", "Apply a numeric theme preset: 0 Material, 1 iOS, 2 Fluent, 3 Bootstrap, 4 Minimal, 5 Dark."),
    ("setThemeName(name)", "Apply a theme by name, for example 'material', 'ios', 'fluent', 'bootstrap', 'minimal' or 'dark'."),
    ("setBackground(color)", "Main surface/background color such as backgroundColor, activeColor, boxColor, trackColor or grooveColor."),
    ("setForeground(color)", "Text, digit or value label color such as textColor, digitColor or valueColor."),
    ("setBorder(color)", "Border color for widgets exposing borderColor."),
    ("setAccent(color)", "Primary/action color such as accentColor, checkedColor, filledColor, valueColor, barColor or activeColor."),
    ("setTrack(color)", "Track/groove color for sliders, progress bars, switches, dials and gauges."),
    ("setThumb(color)", "Thumb/handle color for switches, sliders and dials."),
    ("setContentPadding(x, y=None)", "Internal content padding. Uses paddingX/paddingY, padding or contentPadding when available."),
    ("setSizeTokens(radius=None, border_width=None, control_height=None)", "Shape and sizing shortcut for radius, borderWidth, controlHeight, barHeight or grooveHeight."),
    ("setShadow(enabled=True, blur=None, offset_x=None, offset_y=None, color=None)", "Shadow shortcut for widgets exposing shadowEnabled, shadowBlur, shadowOffsetX/Y and shadowColor."),
    ("setColors(**roles)", "Batch color update. Roles: background/surface, foreground/text, border, accent/primary, track, thumb/handle."),
)
FLUENT_METHOD_PROBES: tuple[tuple[str, str, str, Callable[[QWidget], object]], ...] = (
    (FLUENT_METHOD_DOCS[0][0], FLUENT_METHOD_DOCS[0][1], "setThemeIndex(1)", lambda widget: widget.setThemeIndex(1)),
    (FLUENT_METHOD_DOCS[1][0], FLUENT_METHOD_DOCS[1][1], 'setThemeName("ios")', lambda widget: widget.setThemeName("ios")),
    (FLUENT_METHOD_DOCS[2][0], FLUENT_METHOD_DOCS[2][1], 'setBackground("#2563eb")', lambda widget: widget.setBackground("#2563eb")),
    (FLUENT_METHOD_DOCS[3][0], FLUENT_METHOD_DOCS[3][1], 'setForeground("#111827")', lambda widget: widget.setForeground("#111827")),
    (FLUENT_METHOD_DOCS[4][0], FLUENT_METHOD_DOCS[4][1], 'setBorder("#94a3b8")', lambda widget: widget.setBorder("#94a3b8")),
    (FLUENT_METHOD_DOCS[5][0], FLUENT_METHOD_DOCS[5][1], 'setAccent("#22c55e")', lambda widget: widget.setAccent("#22c55e")),
    (FLUENT_METHOD_DOCS[6][0], FLUENT_METHOD_DOCS[6][1], 'setTrack("#dbeafe")', lambda widget: widget.setTrack("#dbeafe")),
    (FLUENT_METHOD_DOCS[7][0], FLUENT_METHOD_DOCS[7][1], 'setThumb("#ffffff")', lambda widget: widget.setThumb("#ffffff")),
    (FLUENT_METHOD_DOCS[8][0], FLUENT_METHOD_DOCS[8][1], "setContentPadding(8)", lambda widget: widget.setContentPadding(8)),
    (FLUENT_METHOD_DOCS[9][0], FLUENT_METHOD_DOCS[9][1], "setSizeTokens(radius=8)", lambda widget: widget.setSizeTokens(radius=8)),
    (FLUENT_METHOD_DOCS[10][0], FLUENT_METHOD_DOCS[10][1], "setShadow(True, blur=8)", lambda widget: widget.setShadow(True, blur=8)),
    (FLUENT_METHOD_DOCS[11][0], FLUENT_METHOD_DOCS[11][1], 'setColors(accent="#22c55e")', lambda widget: widget.setColors(accent="#22c55e")),
)

WIDGET_DOCS: tuple[WidgetDoc, ...] = (
    WidgetDoc(
        "MonkezButton",
        "Action",
        "Button co theme, radius, padding nho, hover/pressed va shadow.",
        (
            "buttonTypeIndex: 0 Filled | 1 Outlined | 2 Text",
            "active, activeColor, deactiveColor, textColor, hoverTextColor",
            "paddingX, paddingY, radius, shadowEnabled, shadowBlur, shadowOffsetX/Y",
        ),
        ("setThemeIndex(index)", "setButtonTypeIndex(index)", "clicked.connect(slot)"),
        "button = MonkezButton(); button.setText('Save'); button.setThemeIndex(0)",
    ),
    WidgetDoc(
        "MonkezTextInput",
        "Input",
        "Text input mot dong dung cho form, search box va setting panel.",
        ("text, placeholderText", "backgroundColor, borderColor, textColor, radius"),
        ("setPlaceholderText(text)", "text()", "textChanged.connect(slot)"),
        "name_input = MonkezTextInput(); name_input.setPlaceholderText('Customer name')",
    ),
    WidgetDoc(
        "MonkezComboBox",
        "Input",
        "ComboBox custom popup de tranh popup lech ngoai dialog/window.",
        ("borderColor, backgroundColor, hoverBackgroundColor", "textColor, hoverTextColor, borderRadius"),
        ("addItem(text)", "addItemWithIcon(path, text)", "currentText()", "currentIndexChanged.connect(slot)"),
        "combo = MonkezComboBox(); combo.addItems(['Auto', 'Manual'])",
    ),
    WidgetDoc(
        "MonkezCheckBox",
        "Action",
        "Checkbox theme-aware cho form cai dat.",
        ("checked", "textColor, indicatorColor, accentColor", "shadowEnabled"),
        ("setChecked(value)", "isChecked()", "toggled.connect(slot)"),
        "check = MonkezCheckBox(); check.setText('Enable cache')",
    ),
    WidgetDoc(
        "MonkezRadioButton",
        "Action",
        "Radio button voi nhieu style va mau tuy bien.",
        ("radioStyle, checked", "backgroundColor, checkedColor, borderColor, textColor", "indicatorSize, shadowEnabled"),
        ("setBackground(color)", "setAccent(color)", "setBorder(color)", "setForeground(color)", "setChecked(value)", "toggled.connect(slot)"),
        "radio = MonkezRadioButton(); radio.setRadioStyle(2); radio.setBackground('#dbeafe').setAccent('#2563eb')",
    ),
    WidgetDoc(
        "MonkezSwitch",
        "Action",
        "Switch bat/tat gon cho panel dieu khien.",
        ("checked", "trackOnColor, trackOffColor, thumbColor", "shadowEnabled"),
        ("setChecked(value)", "isChecked()", "toggled.connect(slot)"),
        "switch = MonkezSwitch(); switch.setChecked(True)",
    ),
    WidgetDoc(
        "MonkezSlider",
        "Value",
        "Slider ngang/doc co track, handle va theme rieng.",
        ("minimum, maximum, value", "trackColor, valueColor, handleColor"),
        ("setRange(min, max)", "setValue(value)", "valueChanged.connect(slot)"),
        "slider = MonkezSlider(); slider.setRange(0, 100); slider.setValue(42)",
    ),
    WidgetDoc(
        "MonkezProgressBar",
        "Value",
        "Progress bar co the dat thanh line mong bang barHeight.",
        ("value, textVisible", "barHeight, barColor, trackColor, textColor, radius"),
        ("setValue(value)", "setBarHeight(height)", "setTextVisible(value)"),
        "progress = MonkezProgressBar(); progress.setBarHeight(6); progress.setTextVisible(False)",
    ),
    WidgetDoc(
        "MonkezSpinBox",
        "Input",
        "SpinBox so nguyen cho thiet lap tham so.",
        ("minimum, maximum, value", "controlHeight, radius, accentColor"),
        ("setRange(min, max)", "setValue(value)", "valueChanged.connect(slot)"),
        "spin = MonkezSpinBox(); spin.setRange(0, 100)",
    ),
    WidgetDoc(
        "MonkezDoubleSpinBox",
        "Input",
        "SpinBox so thuc cho ty le, threshold va gia tri do luong.",
        ("minimum, maximum, value, decimals", "controlHeight, radius, accentColor"),
        ("setDecimals(count)", "setSingleStep(step)", "valueChanged.connect(slot)"),
        "spin = MonkezDoubleSpinBox(); spin.setDecimals(2); spin.setSingleStep(0.25)",
    ),
    WidgetDoc(
        "MonkezDial",
        "Value",
        "Dial dang ring, knob hoac needle cho dashboard.",
        ("dialStyle: 0 Ring | 1 Knob | 2 Needle", "trackWidth, handleSize, showValue, showTicks, tickCount"),
        ("setDialStyle(index)", "setValue(value)", "valueChanged.connect(slot)"),
        "dial = MonkezDial(); dial.setDialStyle(1); dial.setValue(64)",
    ),
    WidgetDoc(
        "MonkezDateEdit",
        "Date/time",
        "Date input co calendar popup va icon ve bang QPainter.",
        ("date, displayFormat, calendarPopup", "controlHeight, radius, accentColor"),
        ("setDate(QDate)", "date()", "dateChanged.connect(slot)"),
        "date_edit = MonkezDateEdit(); date_edit.setDisplayFormat('dd/MM/yyyy')",
    ),
    WidgetDoc(
        "MonkezTimeEdit",
        "Date/time",
        "Time input voi step arrows custom va style dong nhat.",
        ("time, displayFormat", "controlHeight, radius, accentColor"),
        ("setTime(QTime)", "time()", "timeChanged.connect(slot)"),
        "time_edit = MonkezTimeEdit(); time_edit.setDisplayFormat('HH:mm:ss')",
    ),
    WidgetDoc(
        "MonkezDateTimeEdit",
        "Date/time",
        "Date-time input ket hop calendar popup va time editor.",
        ("dateTime, displayFormat, calendarPopup", "controlHeight, radius, accentColor"),
        ("setDateTime(QDateTime)", "dateTime()", "dateTimeChanged.connect(slot)"),
        "date_time = MonkezDateTimeEdit(); date_time.setDisplayFormat('dd/MM/yyyy HH:mm')",
    ),
    WidgetDoc(
        "MonkezCalendarWidget",
        "Date/time",
        "Calendar custom paint cho ngay duoc chon, today va weekend.",
        ("selectedDate", "backgroundColor, textColor, accentColor", "weekendColor, todayColor, outsideMonthColor"),
        ("setSelectedDate(QDate)", "selectionChanged.connect(slot)", "setGridVisible(value)"),
        "calendar = MonkezCalendarWidget(); calendar.setSelectedDate(QDate.currentDate())",
    ),
    WidgetDoc(
        "MonkezLCDNumber",
        "Display",
        "LCD number cho counter, sensor value hoac status numeric.",
        ("value", "digitCount, segmentStyle, foreground/background colors"),
        ("display(value)", "setDigitCount(count)"),
        "lcd = MonkezLCDNumber(); lcd.display(128)",
    ),
    WidgetDoc(
        "MonkezImage",
        "Media",
        "Image viewer auto-scale, cache pixmap va high-DPI aware.",
        ("imageFile", "backgroundColor", "smoothScaling"),
        ("setImageFile(path)", "set_image(QPixmap | QImage | str)"),
        "image = MonkezImage(); image.setImageFile('assets/photo.png')",
    ),
    WidgetDoc(
        "MonkezUSBCamera",
        "Media",
        "Camera widget dung OpenCV theo tuy chon, autoStart mac dinh tat.",
        (
            "backend, cameraIndex, cameraSource, cameraName",
            "resolutionWidth, resolutionHeight, fps, displayFps, fourcc, bufferSize",
            "mirror, autoStart, previewAutoStart, reconnect, stopOnHide",
        ),
        ("startCamera()", "stopCamera()", "restartCamera()", "statusChanged.connect(slot)"),
        "camera = MonkezUSBCamera(); camera.setCameraIndex(0); camera.startCamera()",
    ),
    WidgetDoc(
        "MonkezFrame",
        "Container",
        "Frame theme-aware dung lam panel, card noi dung hoac wrapper.",
        ("backgroundColor, borderColor, radius, borderWidth, elevation"),
        ("setLayout(layout)", "layout().addWidget(widget)"),
        "frame = MonkezFrame(); frame.setElevation(2)",
    ),
    WidgetDoc(
        "MonkezGroupBox",
        "Container",
        "Group box co header custom, title/subtitle, indicator va auto header height.",
        (
            "title, subtitle, subtitleVisible, autoHeaderHeight",
            "backgroundColor, headerColor, borderColor, accentColor",
            "radius, borderWidth, accentWidth, elevation, contentPadding",
        ),
        ("setTitle(text)", "setSubtitle(text)", "setSubtitleVisible(value)", "layout().addWidget(widget)"),
        "box = MonkezGroupBox(); box.setTitle('Settings'); box.setSubtitleVisible(False)",
    ),
    WidgetDoc(
        "MonkezScrollArea",
        "Container",
        "Scroll area co border, radius va scrollbar theme-aware.",
        ("backgroundColor, borderColor", "scrollbarWidth, scrollbarColor, scrollbarTrackColor"),
        ("setWidget(widget)", "setWidgetResizable(value)"),
        "scroll = MonkezScrollArea(); scroll.setWidget(content)",
    ),
    WidgetDoc(
        "MonkezRadialGauge",
        "Gauge",
        "Gauge tron co ticks, needle, label va scale labels.",
        ("value, label, suffix", "majorTicks, minorTicks, showNeedle, showScaleLabels", "trackColor, valueColor"),
        ("setRange(min, max)", "setValue(value)", "setLabel(text)"),
        "gauge = MonkezRadialGauge(); gauge.setLabel('Pressure'); gauge.setValue(76)",
    ),
    WidgetDoc(
        "MonkezArcGauge",
        "Gauge",
        "Gauge nua vong cho KPI/status voi warning va danger thresholds.",
        ("value, label, suffix", "arcWidth, warningThreshold, dangerThreshold", "segmented, segmentCount"),
        ("setValue(value)", "setSegmented(value)", "setDangerThreshold(value)"),
        "gauge = MonkezArcGauge(); gauge.setSegmented(True)",
    ),
    WidgetDoc(
        "MonkezLinearGauge",
        "Gauge",
        "Gauge dang bar ngang/doc, co target marker.",
        ("value, label, suffix", "vertical, barThickness, targetValue, showTarget, rounded"),
        ("setValue(value)", "setVertical(value)", "setTargetValue(value)"),
        "gauge = MonkezLinearGauge(); gauge.setTargetValue(80)",
    ),
)

WidgetMethodProbe = tuple[str, str, str, Callable[[QWidget], object]]

WIDGET_METHOD_PROBES: dict[str, tuple[WidgetMethodProbe, ...]] = {
    "MonkezButton": (
        ("setButtonTypeIndex(index)", "Switch button style: 0 Filled, 1 Outlined, 2 Text.", "setButtonTypeIndex(1)", lambda widget: widget.setButtonTypeIndex(1)),
        ("setText(text)", "Set button label text.", 'setText("Save")', lambda widget: widget.setText("Save")),
        ("setActive(value)", "Toggle active/deactive visual state.", "setActive(False)", lambda widget: widget.setActive(False)),
    ),
    "MonkezTextInput": (
        ("setPlaceholderText(text)", "Set placeholder text.", 'setPlaceholderText("Customer name")', lambda widget: widget.setPlaceholderText("Customer name")),
        ("setText(text)", "Set input text.", 'setText("Monkez")', lambda widget: widget.setText("Monkez")),
        ("setLeadingIconSize(size)", "Set leading icon size.", "setLeadingIconSize(18)", lambda widget: widget.setLeadingIconSize(18)),
        ("setTrailingIconSize(size)", "Set trailing icon size.", "setTrailingIconSize(18)", lambda widget: widget.setTrailingIconSize(18)),
    ),
    "MonkezComboBox": (
        ("addItem(text)", "Append an item.", 'addItem("New option")', lambda widget: widget.addItem("New option")),
        ("addItems(items)", "Replace/add a small option list.", 'addItems(["Auto", "Manual", "Off"])', lambda widget: widget.addItems(["Auto", "Manual", "Off"])),
        ("setCurrentIndex(index)", "Select an item by index.", "setCurrentIndex(1)", lambda widget: widget.setCurrentIndex(1)),
        ("clear()", "Remove all items.", "clear()", lambda widget: widget.clear()),
    ),
    "MonkezCheckBox": (
        ("setChecked(value)", "Set checked state.", "setChecked(True)", lambda widget: widget.setChecked(True)),
        ("setText(text)", "Set label text.", 'setText("Enable cache")', lambda widget: widget.setText("Enable cache")),
        ("setIndicatorSize(size)", "Set indicator size.", "setIndicatorSize(20)", lambda widget: widget.setIndicatorSize(20)),
        ("setRadius(radius)", "Set indicator corner radius.", "setRadius(6)", lambda widget: widget.setRadius(6)),
    ),
    "MonkezRadioButton": (
        ("setRadioStyle(index)", "Switch style: 0 Classic, 1 Card, 2 Pill.", "setRadioStyle(2)", lambda widget: widget.setRadioStyle(2)),
        ("setChecked(value)", "Set checked state.", "setChecked(True)", lambda widget: widget.setChecked(True)),
        ("setText(text)", "Set label text.", 'setText("Material")', lambda widget: widget.setText("Material")),
        ("setIndicatorSize(size)", "Set indicator size.", "setIndicatorSize(20)", lambda widget: widget.setIndicatorSize(20)),
    ),
    "MonkezSwitch": (
        ("setChecked(value)", "Set switch state.", "setChecked(True)", lambda widget: widget.setChecked(True)),
        ("setShowText(value)", "Show or hide ON/OFF text.", "setShowText(True)", lambda widget: widget.setShowText(True)),
        ("setOnText(text)", "Set ON label.", 'setOnText("YES")', lambda widget: widget.setOnText("YES")),
        ("setOffText(text)", "Set OFF label.", 'setOffText("NO")', lambda widget: widget.setOffText("NO")),
        ("setThumbMargin(value)", "Adjust thumb margin.", "setThumbMargin(3)", lambda widget: widget.setThumbMargin(3)),
    ),
    "MonkezSlider": (
        ("setRange(min, max)", "Set numeric range.", "setRange(0, 100)", lambda widget: widget.setRange(0, 100)),
        ("setValue(value)", "Set current value.", "setValue(72)", lambda widget: widget.setValue(72)),
    ),
    "MonkezProgressBar": (
        ("setValue(value)", "Set progress value.", "setValue(72)", lambda widget: widget.setValue(72)),
        ("setBarHeight(height)", "Set bar thickness.", "setBarHeight(6)", lambda widget: widget.setBarHeight(6)),
        ("setTextVisible(value)", "Show or hide progress text.", "setTextVisible(False)", lambda widget: widget.setTextVisible(False)),
    ),
    "MonkezSpinBox": (
        ("setRange(min, max)", "Set integer range.", "setRange(0, 100)", lambda widget: widget.setRange(0, 100)),
        ("setValue(value)", "Set current value.", "setValue(42)", lambda widget: widget.setValue(42)),
        ("setSingleStep(step)", "Set step amount.", "setSingleStep(5)", lambda widget: widget.setSingleStep(5)),
    ),
    "MonkezDoubleSpinBox": (
        ("setRange(min, max)", "Set floating-point range.", "setRange(0.0, 100.0)", lambda widget: widget.setRange(0.0, 100.0)),
        ("setValue(value)", "Set current value.", "setValue(12.5)", lambda widget: widget.setValue(12.5)),
        ("setDecimals(count)", "Set decimal places.", "setDecimals(2)", lambda widget: widget.setDecimals(2)),
        ("setSingleStep(step)", "Set step amount.", "setSingleStep(0.25)", lambda widget: widget.setSingleStep(0.25)),
    ),
    "MonkezDial": (
        ("setDialStyle(index)", "Switch dial style: 0 Ring, 1 Knob, 2 Needle.", "setDialStyle(1)", lambda widget: widget.setDialStyle(1)),
        ("setValue(value)", "Set current value.", "setValue(64)", lambda widget: widget.setValue(64)),
        ("setShowTicks(value)", "Show or hide ticks.", "setShowTicks(True)", lambda widget: widget.setShowTicks(True)),
        ("setTickCount(count)", "Set tick count.", "setTickCount(12)", lambda widget: widget.setTickCount(12)),
        ("setSuffix(text)", "Set value suffix.", 'setSuffix("%")', lambda widget: widget.setSuffix("%")),
    ),
    "MonkezDateEdit": (
        ("setDate(QDate)", "Set selected date.", "setDate(QDate.currentDate())", lambda widget: widget.setDate(QDate.currentDate())),
        ("setDisplayFormat(format)", "Set date display format.", 'setDisplayFormat("dd/MM/yyyy")', lambda widget: widget.setDisplayFormat("dd/MM/yyyy")),
        ("setCalendarPopup(value)", "Enable calendar popup.", "setCalendarPopup(True)", lambda widget: widget.setCalendarPopup(True)),
    ),
    "MonkezTimeEdit": (
        ("setTime(QTime)", "Set selected time.", "setTime(QTime.currentTime())", lambda widget: widget.setTime(QTime.currentTime())),
        ("setDisplayFormat(format)", "Set time display format.", 'setDisplayFormat("HH:mm:ss")', lambda widget: widget.setDisplayFormat("HH:mm:ss")),
    ),
    "MonkezDateTimeEdit": (
        ("setDateTime(QDateTime)", "Set date and time.", "setDateTime(QDateTime.currentDateTime())", lambda widget: widget.setDateTime(QDateTime.currentDateTime())),
        ("setDisplayFormat(format)", "Set date-time display format.", 'setDisplayFormat("dd/MM/yyyy HH:mm")', lambda widget: widget.setDisplayFormat("dd/MM/yyyy HH:mm")),
        ("setCalendarPopup(value)", "Enable calendar popup.", "setCalendarPopup(True)", lambda widget: widget.setCalendarPopup(True)),
    ),
    "MonkezCalendarWidget": (
        ("setSelectedDate(QDate)", "Set selected date.", "setSelectedDate(QDate.currentDate())", lambda widget: widget.setSelectedDate(QDate.currentDate())),
        ("setGridVisible(value)", "Show or hide date grid.", "setGridVisible(False)", lambda widget: widget.setGridVisible(False)),
    ),
    "MonkezLCDNumber": (
        ("display(value)", "Display a number.", "display(128)", lambda widget: widget.display(128)),
        ("setDigitCount(count)", "Set digit count.", "setDigitCount(4)", lambda widget: widget.setDigitCount(4)),
    ),
    "MonkezImage": (
        ("setSmoothScaling(value)", "Enable or disable smooth scaling.", "setSmoothScaling(True)", lambda widget: widget.setSmoothScaling(True)),
        ("set_image(QPixmap)", "Set image from a pixmap.", "set_image(_demo_pixmap())", lambda widget: widget.set_image(_demo_pixmap())),
    ),
    "MonkezUSBCamera": (
        ("setBackend(name)", "Set OpenCV backend name.", 'setBackend("dshow")', lambda widget: widget.setBackend("dshow")),
        ("setCameraIndex(index)", "Set camera index.", "setCameraIndex(0)", lambda widget: widget.setCameraIndex(0)),
        ("setResolutionWidth(width)", "Set capture width.", "setResolutionWidth(1280)", lambda widget: widget.setResolutionWidth(1280)),
        ("setResolutionHeight(height)", "Set capture height.", "setResolutionHeight(720)", lambda widget: widget.setResolutionHeight(720)),
        ("setDisplayFps(fps)", "Set preview display FPS.", "setDisplayFps(20)", lambda widget: widget.setDisplayFps(20)),
        ("setMirror(value)", "Mirror the preview.", "setMirror(True)", lambda widget: widget.setMirror(True)),
    ),
    "MonkezFrame": (
        ("setElevation(value)", "Set frame elevation/shadow depth.", "setElevation(2)", lambda widget: widget.setElevation(2)),
        ("setRadius(radius)", "Set corner radius.", "setRadius(12)", lambda widget: widget.setRadius(12)),
        ("setBorderWidth(width)", "Set border width.", "setBorderWidth(1)", lambda widget: widget.setBorderWidth(1)),
    ),
    "MonkezGroupBox": (
        ("setTitle(text)", "Set group title.", 'setTitle("Settings")', lambda widget: widget.setTitle("Settings")),
        ("setSubtitle(text)", "Set subtitle text.", 'setSubtitle("Runtime configurable")', lambda widget: widget.setSubtitle("Runtime configurable")),
        ("setSubtitleVisible(value)", "Show or hide subtitle.", "setSubtitleVisible(False)", lambda widget: widget.setSubtitleVisible(False)),
        ("setContentPadding(value)", "Set content padding.", "setContentPadding(14)", lambda widget: widget.setContentPadding(14)),
        ("setAutoHeaderHeight(value)", "Auto-size header height.", "setAutoHeaderHeight(True)", lambda widget: widget.setAutoHeaderHeight(True)),
    ),
    "MonkezScrollArea": (
        ("setWidgetResizable(value)", "Resize child widget with the viewport.", "setWidgetResizable(True)", lambda widget: widget.setWidgetResizable(True)),
        ("setScrollbarWidth(width)", "Set scrollbar width.", "setScrollbarWidth(9)", lambda widget: widget.setScrollbarWidth(9)),
    ),
    "MonkezRadialGauge": (
        ("setRange(min, max)", "Set gauge range.", "setRange(0, 100)", lambda widget: widget.setRange(0, 100)),
        ("setValue(value)", "Set gauge value.", "setValue(76)", lambda widget: widget.setValue(76)),
        ("setLabel(text)", "Set gauge label.", 'setLabel("Pressure")', lambda widget: widget.setLabel("Pressure")),
        ("setSuffix(text)", "Set value suffix.", 'setSuffix("%")', lambda widget: widget.setSuffix("%")),
    ),
    "MonkezArcGauge": (
        ("setValue(value)", "Set gauge value.", "setValue(68)", lambda widget: widget.setValue(68)),
        ("setLabel(text)", "Set gauge label.", 'setLabel("Load")', lambda widget: widget.setLabel("Load")),
        ("setSegmented(value)", "Enable segmented arc.", "setSegmented(True)", lambda widget: widget.setSegmented(True)),
        ("setDangerThreshold(value)", "Set danger threshold.", "setDangerThreshold(85)", lambda widget: widget.setDangerThreshold(85)),
    ),
    "MonkezLinearGauge": (
        ("setValue(value)", "Set gauge value.", "setValue(64)", lambda widget: widget.setValue(64)),
        ("setLabel(text)", "Set gauge label.", 'setLabel("Throughput")', lambda widget: widget.setLabel("Throughput")),
        ("setVertical(value)", "Switch orientation.", "setVertical(True)", lambda widget: widget.setVertical(True)),
        ("setTargetValue(value)", "Set target marker.", "setTargetValue(80)", lambda widget: widget.setTargetValue(80)),
    ),
}


class GalleryWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Monkez Widget Docs Lab")
        self.resize(1320, 860)
        icon = Path(__file__).resolve().parents[2] / "logo.ico"
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))

        self._themed_widgets: list[QWidget] = []
        self._tab_theme_groups: dict[int, QButtonGroup] = {}
        self._building_tab_index: int | None = None
        self._compact_widgets: list[QWidget] = []
        self._value_widgets: list[QWidget] = []
        self._live_value = 64

        root = QFrame()
        root.setObjectName("appRoot")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(18, 16, 18, 18)
        root_layout.setSpacing(12)

        header = QFrame()
        header.setObjectName("topHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Monkez Widget Docs Lab")
        title.setObjectName("heroTitle")
        subtitle = QLabel("Search widgets, inspect supported runtime methods, and apply methods directly to a live preview.")
        subtitle.setObjectName("heroSubtitle")
        subtitle.setWordWrap(True)
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        root_layout.addWidget(header)
        root_layout.addWidget(self._build_docs_tab(), 1)

        self.setCentralWidget(root)
        self.setStyleSheet(_APP_STYLE)

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(248)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 20, 18, 18)
        layout.setSpacing(12)

        brand = QLabel("Monkez\nGallery")
        brand.setObjectName("brand")
        layout.addWidget(brand)

        caption = QLabel("Interactive widget lab")
        caption.setObjectName("sidebarCaption")
        layout.addWidget(caption)

        layout.addWidget(self._sidebar_label("Tabs"))
        nav_group = QButtonGroup(self)
        nav_group.setExclusive(True)
        for index, name in enumerate(GALLERY_TABS):
            button = QToolButton()
            button.setText(name)
            button.setCheckable(True)
            button.setObjectName("navButton")
            button.clicked.connect(lambda checked=False, tab_index=index: self._switch_tab(tab_index))
            nav_group.addButton(button, index)
            layout.addWidget(button)
            if index == 0:
                button.setChecked(True)
        self._nav_group = nav_group

        layout.addSpacing(6)
        layout.addWidget(self._sidebar_label("Live value"))
        self._master_slider = MonkezSlider()
        self._master_slider.setRange(0, 100)
        self._master_slider.setValue(self._live_value)
        self._master_slider.valueChanged.connect(self._update_live_value)
        self._track_theme(self._master_slider)
        layout.addWidget(self._master_slider)

        self._live_value_label = QLabel("64%")
        self._live_value_label.setObjectName("largeValue")
        layout.addWidget(self._live_value_label)

        self._animate_switch = MonkezSwitch()
        self._animate_switch.setChecked(True)
        self._track_theme(self._animate_switch)
        layout.addWidget(self._switch_row("Animate", self._animate_switch))

        self._compact_switch = MonkezSwitch()
        self._compact_switch.setChecked(False)
        self._compact_switch.toggled.connect(self._set_compact_mode)
        self._track_theme(self._compact_switch)
        layout.addWidget(self._switch_row("Compact controls", self._compact_switch))

        launch_docs = MonkezButton()
        launch_docs.setText("Open docs")
        launch_docs.setButtonTypeIndex(1)
        launch_docs.clicked.connect(lambda: self._switch_tab(0))
        self._track_theme(launch_docs)
        layout.addWidget(launch_docs)

        layout.addStretch(1)
        version = QLabel("custom-pyqt6-designer")
        version.setObjectName("sidebarCaption")
        layout.addWidget(version)
        return sidebar

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("topHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        title_box = QVBoxLayout()
        title = QLabel("Monkez Custom Widgets")
        title.setObjectName("heroTitle")
        subtitle = QLabel("Live PyQt6 preview, runtime docs and Designer-ready widget behavior.")
        subtitle.setObjectName("heroSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box, 1)

        for label, value in (("Widgets", "24"), ("Docs", str(len(WIDGET_DOCS))), ("Themes", "6")):
            layout.addWidget(self._metric(label, value))
        return header

    def _build_overview_tab(self) -> QWidget:
        page, grid = self._page_grid()
        preview = MonkezImage()
        preview.set_image(_demo_pixmap())
        preview.setMinimumHeight(260)
        self._track_theme(preview)

        primary = MonkezButton()
        primary.setText("Run action")
        secondary = MonkezButton()
        secondary.setText("Preview")
        secondary.setButtonTypeIndex(1)
        combo = MonkezComboBox()
        combo.clear()
        combo.addItems(["Production", "Maintenance", "Diagnostics"])
        status = MonkezProgressBar()
        status.setValue(self._live_value)
        self._track_value(status)

        radial = MonkezRadialGauge()
        radial.setLabel("Yield")
        radial.setValue(self._live_value)
        self._track_value(radial)

        group = MonkezGroupBox()
        group.setTitle("Line A summary")
        group.setSubtitle("Theme and live value update all controls")
        group_layout = QGridLayout(group)
        group_layout.addWidget(QLabel("Mode"), 0, 0)
        group_layout.addWidget(combo, 0, 1)
        group_layout.addWidget(QLabel("Throughput"), 1, 0)
        group_layout.addWidget(status, 1, 1)
        group_layout.addWidget(primary, 2, 0)
        group_layout.addWidget(secondary, 2, 1)

        grid.addWidget(self._showcase("Hero preview", "Image, action controls and dashboard composition.", [preview]), 0, 0, 2, 1)
        grid.addWidget(self._showcase("Live form", "A compact production form using real Monkez widgets.", [group]), 0, 1)
        grid.addWidget(self._showcase("Primary metric", "Gauge follows the sidebar live value.", [radial]), 1, 1)
        self._track_many(primary, secondary, combo, status, radial, group)
        return page

    def _build_controls_tab(self) -> QWidget:
        page, grid = self._page_grid()

        filled = MonkezButton()
        filled.setText("Filled")
        outline = MonkezButton()
        outline.setText("Outlined")
        outline.setButtonTypeIndex(1)
        text_button = MonkezButton()
        text_button.setText("Text")
        text_button.setButtonTypeIndex(2)
        danger = MonkezButton()
        danger.setText("Inactive")
        danger.setActive(False)
        close = MonkezButton()
        close.setText("X")
        close.setFixedSize(32, 28)
        close.setPaddingX(1)
        close.setPaddingY(1)

        check_a = MonkezCheckBox()
        check_a.setText("Enable logging")
        check_a.setChecked(True)
        check_b = MonkezCheckBox()
        check_b.setText("Require confirmation")
        radio_a = MonkezRadioButton()
        radio_a.setText("Material radio")
        radio_a.setChecked(True)
        radio_b = MonkezRadioButton()
        radio_b.setText("Alternative")
        switch_a = MonkezSwitch()
        switch_a.setChecked(True)
        switch_b = MonkezSwitch()

        grid.addWidget(self._showcase("Button states", "Hover and press states are intentionally visible but calm.", [filled, outline, text_button, danger, close]), 0, 0)
        grid.addWidget(self._showcase("Binary choices", "CheckBox, RadioButton and Switch share theme updates.", [check_a, check_b, radio_a, radio_b, self._switch_row("Enabled", switch_a), self._switch_row("Readonly", switch_b)]), 0, 1)
        self._track_many(filled, outline, text_button, danger, close, check_a, check_b, radio_a, radio_b, switch_a, switch_b)
        return page

    def _build_inputs_tab(self) -> QWidget:
        page, grid = self._page_grid()

        text_input = MonkezTextInput()
        text_input.setPlaceholderText("Type filter text...")
        combo = MonkezComboBox()
        combo.clear()
        combo.addItems(["Auto backend", "DirectShow", "MSMF", "GStreamer"])
        spin = MonkezSpinBox()
        spin.setRange(0, 240)
        spin.setValue(60)
        double_spin = MonkezDoubleSpinBox()
        double_spin.setDecimals(2)
        double_spin.setValue(12.5)

        date_edit = MonkezDateEdit()
        date_edit.setDate(QDate.currentDate())
        time_edit = MonkezTimeEdit()
        time_edit.setTime(QTime.currentTime())
        dt_edit = MonkezDateTimeEdit()
        dt_edit.setDateTime(QDateTime.currentDateTime())
        calendar = MonkezCalendarWidget()
        calendar.setSelectedDate(QDate.currentDate())

        dial_ring = MonkezDial()
        dial_ring.setValue(self._live_value)
        dial_knob = MonkezDial()
        dial_knob.setDialStyle(1)
        dial_knob.setValue(42)
        dial_needle = MonkezDial()
        dial_needle.setDialStyle(2)
        dial_needle.setValue(76)
        self._track_value(dial_ring)

        grid.addWidget(self._showcase("Form inputs", "Text, combobox and spinboxes with compact-friendly sizing.", [text_input, combo, spin, double_spin]), 0, 0)
        grid.addWidget(self._showcase("Date and time", "Hover regions stay inside the outer rounded border.", [date_edit, time_edit, dt_edit, calendar]), 0, 1)
        grid.addWidget(self._showcase("Dial styles", "Ring, knob and needle variants for machine dashboards.", [dial_ring, dial_knob, dial_needle]), 1, 0, 1, 2)
        self._track_many(text_input, combo, spin, double_spin, date_edit, time_edit, dt_edit, calendar, dial_ring, dial_knob, dial_needle)
        self._compact_widgets.extend([text_input, combo, spin, double_spin, date_edit, time_edit, dt_edit])
        return page

    def _build_visual_tab(self) -> QWidget:
        page, grid = self._page_grid()

        image = MonkezImage()
        image.set_image(_demo_pixmap())
        image.setMinimumHeight(260)

        camera = MonkezUSBCamera()
        camera.setMinimumHeight(220)
        camera.image_label.setText("Camera preview is off by default")

        frame = MonkezFrame()
        frame.setMinimumHeight(120)
        frame_layout = QVBoxLayout(frame)
        frame_layout.addWidget(QLabel("Frame content region"))
        frame_layout.addWidget(QLabel("Useful as a section shell in generated UIs."))

        group = MonkezGroupBox()
        group.setTitle("Quality gate")
        group.setSubtitle("Auto header height + optional subtitle")
        group.setCheckable(True)
        group.setChecked(True)
        group_layout = QVBoxLayout(group)
        group_layout.addWidget(QLabel("Part ID: MBT03-A2"))
        group_layout.addWidget(QLabel("Status: Ready"))

        scroll = MonkezScrollArea()
        scroll.setMinimumHeight(220)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        for index in range(1, 13):
            row = QLabel(f"Parameter {index:02d}    tolerance: +/- {index % 4 + 1}%")
            row.setObjectName("rowLabel")
            scroll_layout.addWidget(row)
        scroll.setWidget(scroll_content)

        grid.addWidget(self._showcase("Media surfaces", "Image scaling and camera placeholder behavior.", [image, camera]), 0, 0)
        grid.addWidget(self._showcase("Containers", "Frame, GroupBox and ScrollArea in one realistic layout.", [frame, group, scroll]), 0, 1)
        self._track_many(image, camera, frame, group, scroll)
        return page

    def _build_gauges_tab(self) -> QWidget:
        page, grid = self._page_grid()

        radial = MonkezRadialGauge()
        radial.setLabel("Pressure")
        radial.setValue(self._live_value)
        arc = MonkezArcGauge()
        arc.setLabel("Load")
        arc.setSegmented(True)
        arc.setValue(self._live_value)
        linear = MonkezLinearGauge()
        linear.setLabel("Throughput")
        linear.setTargetValue(82)
        linear.setValue(self._live_value)
        vertical = MonkezLinearGauge()
        vertical.setVertical(True)
        vertical.setLabel("Tank")
        vertical.setMinimumHeight(250)
        vertical.setValue(self._live_value)
        progress = MonkezProgressBar()
        progress.setValue(self._live_value)
        slim = MonkezProgressBar()
        slim.setBarHeight(5)
        slim.setTextVisible(False)
        slim.setValue(self._live_value)
        lcd = MonkezLCDNumber()
        lcd.display(self._live_value)

        for widget in (radial, arc, linear, vertical, progress, slim):
            self._track_value(widget)
        self._track_value(lcd)

        grid.addWidget(self._showcase("Round instruments", "Radial and arc gauges follow the live sidebar value.", [radial, arc]), 0, 0)
        grid.addWidget(self._showcase("Linear indicators", "Horizontal, vertical and thin progress variants.", [linear, vertical, progress, slim, lcd]), 0, 1)
        self._track_many(radial, arc, linear, vertical, progress, slim, lcd)
        return page

    def _build_docs_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 12, 4, 4)
        layout.setSpacing(10)

        tools = QHBoxLayout()
        search = QLineEdit()
        search.setPlaceholderText("Search widget, property or method...")
        search.setObjectName("docsSearch")
        search.textChanged.connect(self._filter_docs)
        tools.addWidget(search, 1)

        import_button = MonkezButton()
        import_button.setText("Copy import")
        import_button.setButtonTypeIndex(1)
        import_button.clicked.connect(self._copy_import_snippet)
        self._track_theme(import_button)
        tools.addWidget(import_button)
        layout.addLayout(tools)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._docs_list = QListWidget()
        self._docs_browser = QTextBrowser()
        self._docs_browser.setOpenExternalLinks(False)
        self._docs_browser.setOpenLinks(False)
        self._docs_browser.anchorClicked.connect(self._handle_doc_link)
        self._docs_list.setObjectName("docsList")
        self._docs_browser.setObjectName("docsBrowser")
        self._docs_list.currentItemChanged.connect(self._show_doc)
        splitter.addWidget(self._docs_list)
        splitter.addWidget(self._docs_browser)
        splitter.addWidget(self._build_doc_preview_panel())
        self._populate_docs(WIDGET_DOCS)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([260, 660, 360])
        layout.addWidget(splitter, 1)
        if self._docs_list.currentItem() is not None:
            self._show_doc(self._docs_list.currentItem())
        return page

    def _build_doc_preview_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("docsPreviewPanel")
        panel.setMinimumWidth(320)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)

        title = QLabel("Live preview")
        title.setObjectName("cardTitle")
        layout.addWidget(title)

        subtitle = QLabel("Type a runtime method and press Enter.")
        subtitle.setObjectName("mutedLabel")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self._docs_preview_slot = QFrame()
        self._docs_preview_slot.setObjectName("docsPreviewSlot")
        self._docs_preview_slot_layout = QVBoxLayout(self._docs_preview_slot)
        self._docs_preview_slot_layout.setContentsMargins(14, 14, 14, 14)
        self._docs_preview_slot_layout.setSpacing(8)
        self._docs_preview_slot_layout.addStretch(1)
        layout.addWidget(self._docs_preview_slot, 1)

        self._docs_method_input = QLineEdit()
        self._docs_method_input.setObjectName("docsMethodInput")
        self._docs_method_input.setPlaceholderText('widget.setBackground("#2563eb")')
        self._docs_method_input.returnPressed.connect(self._run_doc_method)
        layout.addWidget(self._docs_method_input)

        layout.addWidget(self._build_color_tools())

        actions = QHBoxLayout()
        reset = MonkezButton()
        reset.setText("Reset")
        reset.setButtonTypeIndex(1)
        reset.clicked.connect(self._reset_doc_preview)
        self._track_theme(reset)
        actions.addWidget(reset)

        apply_button = MonkezButton()
        apply_button.setText("Apply")
        apply_button.clicked.connect(self._run_doc_method)
        self._track_theme(apply_button)
        actions.addWidget(apply_button)
        layout.addLayout(actions)

        self._docs_method_status = QLabel("Examples: setAccent(\"#22c55e\"), setThemeIndex(1)")
        self._docs_method_status.setObjectName("docsMethodStatus")
        self._docs_method_status.setWordWrap(True)
        layout.addWidget(self._docs_method_status)
        self._docs_preview_doc: WidgetDoc | None = None
        self._docs_preview_widget: QWidget | None = None
        self._set_selected_color("#2563eb", copy=False)
        return panel

    def _build_color_tools(self) -> QFrame:
        tools = QFrame()
        tools.setObjectName("colorTools")
        layout = QVBoxLayout(tools)
        layout.setContentsMargins(10, 9, 10, 10)
        layout.setSpacing(8)

        header = QHBoxLayout()
        label = QLabel("Color tools")
        label.setObjectName("tabThemeLabel")
        header.addWidget(label)
        header.addStretch(1)
        self._color_format_combo = QComboBox()
        self._color_format_combo.setObjectName("colorFormatCombo")
        self._color_format_combo.addItems(COLOR_FORMATS)
        self._color_format_combo.currentTextChanged.connect(lambda _text: self._copy_selected_color())
        header.addWidget(self._color_format_combo)
        self._selected_color_label = QLabel("#2563eb")
        self._selected_color_label.setObjectName("selectedColorLabel")
        header.addWidget(self._selected_color_label)
        layout.addLayout(header)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(6)
        for index, (name, color) in enumerate(COLOR_SWATCHES):
            button = QToolButton()
            button.setObjectName("colorSwatch")
            button.setToolTip(f"{name} {color}")
            button.setFixedSize(26, 22)
            border = "#94a3b8" if color.lower() == "#ffffff" else color
            button.setStyleSheet(
                "QToolButton#colorSwatch {"
                f"background: {color};"
                f"border: 1px solid {border};"
                "border-radius: 5px;"
                "}"
                "QToolButton#colorSwatch:hover { border: 2px solid #0f172a; }"
            )
            button.clicked.connect(lambda checked=False, value=color: self._set_selected_color(value))
            grid.addWidget(button, index // 8, index % 8)
        layout.addLayout(grid)

        picker_row = QHBoxLayout()
        picker_row.setContentsMargins(0, 0, 0, 0)
        picker = MonkezButton()
        picker.setText("Pick")
        picker.setButtonTypeIndex(1)
        picker.setPaddingX(3)
        picker.setPaddingY(1)
        picker.setFixedWidth(84)
        picker.clicked.connect(self._pick_color)
        self._track_theme(picker)
        picker_row.addStretch(1)
        picker_row.addWidget(picker)
        layout.addLayout(picker_row)
        return tools

    def _page_grid(self) -> tuple[QScrollArea, QGridLayout]:
        content = QWidget()
        content.setObjectName("pageContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(4, 10, 4, 4)
        content_layout.setSpacing(12)
        content_layout.addWidget(self._tab_theme_bar(self._building_tab_index or 0))

        grid_holder = QWidget()
        grid_holder.setObjectName("gridHolder")
        grid = QGridLayout(grid_holder)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(18)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        content_layout.addWidget(grid_holder, 1)

        scroll = QScrollArea()
        scroll.setObjectName("pageScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(content)
        return scroll, grid

    def _tab_theme_bar(self, tab_index: int) -> QFrame:
        bar = QFrame()
        bar.setObjectName("tabThemeBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        label = QLabel("Theme")
        label.setObjectName("tabThemeLabel")
        layout.addWidget(label)

        group = QButtonGroup(self)
        group.setExclusive(True)
        self._tab_theme_groups[tab_index] = group
        for index, name in enumerate(THEME_NAMES):
            button = QToolButton()
            button.setText(name)
            button.setCheckable(True)
            button.setObjectName("tabThemeButton")
            button.clicked.connect(lambda checked=False, tab=tab_index, theme=index: self._apply_tab_theme(tab, theme))
            group.addButton(button, index)
            layout.addWidget(button)
            if index == self._tab_theme_indices[tab_index]:
                button.setChecked(True)
        layout.addStretch(1)
        return bar

    def _showcase(self, title: str, subtitle: str, widgets: list[QWidget]) -> QFrame:
        card = QFrame()
        card.setObjectName("showcaseCard")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("mutedLabel")
        subtitle_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)

        for widget in widgets:
            wrapper = QWidget()
            wrapper.setObjectName("demoSlot")
            wrapper_layout = QHBoxLayout(wrapper)
            wrapper_layout.setContentsMargins(0, 3, 0, 3)
            wrapper_layout.setSpacing(10)
            wrapper_layout.addWidget(widget, 1)
            layout.addWidget(wrapper)
        layout.addStretch(1)
        return card

    def _metric(self, label: str, value: str) -> QFrame:
        metric = QFrame()
        metric.setObjectName("metric")
        layout = QVBoxLayout(metric)
        layout.setContentsMargins(16, 10, 16, 10)
        number = QLabel(value)
        number.setObjectName("metricValue")
        text = QLabel(label)
        text.setObjectName("metricLabel")
        layout.addWidget(number)
        layout.addWidget(text)
        return metric

    def _sidebar_label(self, text: str) -> QLabel:
        label = QLabel(text.upper())
        label.setObjectName("sidebarLabel")
        return label

    def _switch_row(self, label: str, switch: MonkezSwitch) -> QWidget:
        row = QWidget()
        row.setObjectName("switchRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        text = QLabel(label)
        text.setObjectName("switchLabel")
        layout.addWidget(text, 1)
        layout.addWidget(switch)
        return row

    def _track_many(self, *widgets: QWidget) -> None:
        for widget in widgets:
            self._track_theme(widget)

    def _track_theme(self, widget: QWidget) -> QWidget:
        if hasattr(widget, "setThemeIndex") and widget not in self._themed_widgets:
            self._themed_widgets.append(widget)
            self._apply_theme_to_widget(widget, 0)
        return widget

    def _track_value(self, widget: QWidget) -> QWidget:
        if widget not in self._value_widgets:
            self._value_widgets.append(widget)
        return self._track_theme(widget)

    def _apply_theme(self, index: int) -> None:
        self._apply_tab_theme(self._active_tab_index, int(index))

    def _apply_tab_theme(self, tab_index: int, theme_index: int) -> None:
        tab_index = int(tab_index)
        theme_index = int(theme_index)
        self._tab_theme_indices[tab_index] = theme_index
        self._sync_theme_buttons(tab_index, theme_index)
        for widget in self._tab_widgets.get(tab_index, []):
            self._apply_theme_to_widget(widget, theme_index)
        if tab_index == self._active_tab_index:
            for widget in self._global_themed_widgets:
                self._apply_theme_to_widget(widget, theme_index)

    def _switch_tab(self, index: int) -> None:
        self._active_tab_index = int(index)
        self._tabs.setCurrentIndex(self._active_tab_index)
        if hasattr(self, "_nav_group"):
            button = self._nav_group.button(self._active_tab_index)
            if button is not None:
                button.setChecked(True)
        theme_index = self._tab_theme_indices[self._active_tab_index]
        self._sync_theme_buttons(self._active_tab_index, theme_index)
        for widget in self._tab_widgets.get(self._active_tab_index, []):
            self._apply_theme_to_widget(widget, theme_index)
        for widget in self._global_themed_widgets:
            self._apply_theme_to_widget(widget, theme_index)

    def _sync_theme_buttons(self, tab_index: int, theme_index: int) -> None:
        group = self._tab_theme_groups.get(int(tab_index))
        if group is None:
            return
        button = group.button(int(theme_index))
        if button is not None:
            button.setChecked(True)

    def _apply_theme_to_widget(self, widget: QWidget, theme_index: int) -> None:
        setter = getattr(widget, "setThemeIndex", None)
        if setter is not None:
            setter(int(theme_index))

    def _update_live_value(self, value: int) -> None:
        self._live_value = int(value)
        if hasattr(self, "_live_value_label"):
            self._live_value_label.setText(f"{self._live_value}%")
        if hasattr(self, "_master_slider") and self._master_slider.value() != self._live_value:
            self._master_slider.blockSignals(True)
            self._master_slider.setValue(self._live_value)
            self._master_slider.blockSignals(False)
        for widget in self._value_widgets:
            if isinstance(widget, MonkezLCDNumber):
                widget.display(self._live_value)
            elif hasattr(widget, "setValue"):
                widget.setValue(self._live_value)

    def _set_compact_mode(self, enabled: bool) -> None:
        height = 30 if enabled else 40
        for widget in self._compact_widgets:
            if hasattr(widget, "setControlHeight"):
                widget.setControlHeight(height)
            elif isinstance(widget, MonkezComboBox):
                widget.setFixedHeight(height)
            elif isinstance(widget, MonkezTextInput):
                widget.setFixedHeight(height)
        for widget in self._themed_widgets:
            if isinstance(widget, MonkezButton):
                widget.setPaddingX(2 if enabled else 4)
                widget.setPaddingY(1 if enabled else 2)

    def _tick(self) -> None:
        if getattr(self, "_animate_switch", None) is not None and self._animate_switch.isChecked():
            self._update_live_value((self._live_value + 7) % 101)

    def _populate_docs(self, docs: tuple[WidgetDoc, ...]) -> None:
        self._docs_list.clear()
        for doc in docs:
            item = QListWidgetItem(doc.name)
            item.setData(Qt.ItemDataRole.UserRole, doc)
            self._docs_list.addItem(item)
        if docs:
            self._docs_list.setCurrentRow(0)
        else:
            self._docs_browser.setHtml("<h1>No match</h1><p>Try another keyword.</p>")

    def _filter_docs(self, text: str) -> None:
        needle = text.strip().lower()
        if not needle:
            self._populate_docs(WIDGET_DOCS)
            return
        fluent_text = " ".join(method + " " + description for method, description in FLUENT_METHOD_DOCS).lower()
        widget_method_text = {
            name: " ".join(label + " " + description + " " + command for label, description, command, _probe in probes).lower()
            for name, probes in WIDGET_METHOD_PROBES.items()
        }
        filtered = tuple(
            doc
            for doc in WIDGET_DOCS
            if needle in doc.name.lower()
            or needle in doc.group.lower()
            or needle in doc.purpose.lower()
            or any(needle in prop.lower() for prop in doc.properties)
            or any(needle in method.lower() for method in doc.methods)
            or needle in fluent_text
            or needle in widget_method_text.get(doc.name, "")
        )
        self._populate_docs(filtered)

    def _show_doc(self, current: QListWidgetItem | None, previous: QListWidgetItem | None = None) -> None:
        if current is None:
            self._docs_browser.clear()
            return
        doc: WidgetDoc = current.data(Qt.ItemDataRole.UserRole)
        colors = _table_rows(("Accepted color value", "Example"), COLOR_VALUE_DOCS)
        supported_fluent = _method_table_rows(("Supported method", "What it configures"), _supported_fluent_method_docs(doc.name))
        usage = html.escape(doc.usage)
        self._set_doc_preview(doc)
        self._docs_browser.setHtml(
            f"""
            <style>
            body {{ color: #0f172a; font-family: "Segoe UI"; }}
            h1 {{ margin-bottom: 4px; }}
            h2 {{ margin-top: 12px; margin-bottom: 6px; }}
            p {{ line-height: 1.45; }}
            .tag {{
                display: inline-block;
                color: #1d4ed8;
                background: #dbeafe;
                border-radius: 6px;
                padding: 4px 8px;
                font-weight: 700;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 6px 0 12px 0;
            }}
            th {{
                background: #f1f5f9;
                color: #334155;
                text-align: left;
                font-weight: 700;
            }}
            th, td {{
                border: 1px solid #e2e8f0;
                padding: 6px 8px;
                vertical-align: top;
            }}
            a {{
                color: #1d4ed8;
                font-weight: 700;
                text-decoration: none;
            }}
            .method-command {{
                color: #475569;
                background: #f1f5f9;
                border-radius: 4px;
                padding: 2px 4px;
                font-family: "Cascadia Code", "Consolas";
                font-size: 9pt;
            }}
            .layout td {{
                border: 0;
                padding: 0 8px 0 0;
            }}
            code {{
                color: #0f172a;
                background: #eef2ff;
                border-radius: 4px;
                padding: 1px 4px;
            }}
            pre {{
                color: #dbeafe;
                background: #0f172a;
                border-radius: 8px;
                padding: 14px;
                line-height: 1.45;
            }}
            </style>
            <h1>{html.escape(doc.name)}</h1>
            <p class="tag">{html.escape(doc.group)}</p>
            <p>{html.escape(doc.purpose)}</p>
            <h2>Accepted color values</h2>
            <table>{colors}</table>
            <h2>Supported runtime methods</h2>
            <p>This table is generated from the current widget implementation. Each listed method is tested against a fresh <code>{html.escape(doc.name)}</code> instance, so these are the methods you can type in the live method box.</p>
            <table>{supported_fluent}</table>
            <h2>Usage</h2>
            <pre>{usage}</pre>
            """
        )

    def _handle_doc_link(self, url: QUrl) -> None:
        if url.scheme() != "method":
            return
        label = unquote(url.toString()[len("method:"):])
        current = self._docs_list.currentItem()
        if current is None:
            return
        doc: WidgetDoc = current.data(Qt.ItemDataRole.UserRole)
        commands = {method_label: command for method_label, _description, command in _supported_fluent_method_docs(doc.name)}
        command = commands.get(label)
        if command is None:
            return
        self._docs_method_input.setText(command)
        self._docs_method_input.setFocus()
        self._docs_method_input.selectAll()
        self._docs_method_status.setText("Command inserted. Press Enter or Apply to run it.")

    def _set_doc_preview(self, doc: WidgetDoc) -> None:
        if getattr(self, "_docs_preview_doc", None) == doc and self._docs_preview_widget is not None:
            return
        self._docs_preview_doc = doc
        self._docs_method_input.clear()
        self._docs_method_status.setText("Examples: setAccent(\"#22c55e\"), setThemeIndex(1)")
        self._replace_doc_preview_widget(_create_doc_preview_widget(doc.name))

    def _replace_doc_preview_widget(self, widget: QWidget) -> None:
        layout = self._docs_preview_slot_layout
        while layout.count():
            item = layout.takeAt(0)
            child = item.widget()
            if child is not None:
                child.deleteLater()
        widget.setObjectName("docsLiveWidget")
        if hasattr(widget, "setThemeIndex"):
            widget.setThemeIndex(0)
        layout.addStretch(1)
        layout.addWidget(widget, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(1)
        self._docs_preview_widget = widget

    def _reset_doc_preview(self) -> None:
        doc = self._docs_preview_doc
        if doc is None:
            return
        self._docs_method_input.clear()
        self._docs_method_status.setText("Reset to default preview state.")
        self._replace_doc_preview_widget(_create_doc_preview_widget(doc.name))

    def _run_doc_method(self) -> None:
        widget = self._docs_preview_widget
        if widget is None:
            return
        command = self._docs_method_input.text().strip()
        if not command:
            return
        code = _normalize_doc_command(command)
        namespace = {
            "widget": widget,
            "QColor": QColor,
            "QDate": QDate,
            "QDateTime": QDateTime,
            "QTime": QTime,
            "Qt": Qt,
            "_demo_pixmap": _demo_pixmap,
            "setColor": lambda color: _apply_preview_color(widget, color),
        }
        try:
            try:
                result = eval(code, {"__builtins__": {}}, namespace)
            except SyntaxError:
                exec(code, {"__builtins__": {}}, namespace)
                result = None
        except Exception as exc:  # noqa: BLE001 - shown inside the docs lab panel.
            self._docs_method_status.setText(f"Error: {type(exc).__name__}: {exc}")
            return
        self._docs_method_status.setText("Applied." if result is None else f"Applied: {type(result).__name__}")

    def _set_selected_color(self, color: str, *, copy: bool = True) -> None:
        qcolor = QColor(color)
        if not qcolor.isValid():
            self._docs_method_status.setText(f"Invalid color: {color}")
            return
        self._selected_color = qcolor.name()
        if hasattr(self, "_selected_color_label"):
            text_color = "#ffffff" if qcolor.lightness() < 140 else "#0f172a"
            self._selected_color_label.setText(self._selected_color)
            self._selected_color_label.setStyleSheet(
                "QLabel#selectedColorLabel {"
                f"background: {self._selected_color};"
                f"color: {text_color};"
                "border: 1px solid #cbd5e1;"
                "border-radius: 6px;"
                "padding: 4px 8px;"
                "font-family: \"Cascadia Code\", \"Consolas\";"
                "font-weight: 700;"
                "}"
            )
        if copy:
            self._copy_selected_color()

    def _format_selected_color(self) -> str:
        color = QColor(self._selected_color)
        fmt = self._color_format_combo.currentText() if hasattr(self, "_color_format_combo") else "Hex"
        if fmt == "RGB tuple":
            return f"({color.red()}, {color.green()}, {color.blue()})"
        if fmt == "RGBA tuple":
            return f"({color.red()}, {color.green()}, {color.blue()}, {color.alpha()})"
        if fmt == "QColor":
            return f'QColor("{color.name()}")'
        return color.name()

    def _copy_selected_color(self) -> None:
        value = self._format_selected_color()
        QApplication.clipboard().setText(value)
        if hasattr(self, "_selected_color_label"):
            self._selected_color_label.setText(value)
        if hasattr(self, "_docs_method_status"):
            self._docs_method_status.setText(f"Copied color: {value}")

    def _pick_color(self) -> None:
        color = QColorDialog.getColor(QColor(self._selected_color), self, "Pick Monkez color")
        if color.isValid():
            self._set_selected_color(color.name())

    def _copy_import_snippet(self) -> None:
        current = self._docs_list.currentItem()
        name = current.text() if current is not None else "MonkezButton"
        if "/" in name:
            name = name.split("/", 1)[0].strip()
        QApplication.clipboard().setText(f"from custom_pyqt6_designer.monkez_widgets import {name}")


def _table_rows(headers: tuple[str, str], rows) -> str:
    header_html = "".join(f"<th>{html.escape(header)}</th>" for header in headers)
    body_html = "".join(
        "<tr>"
        + "".join(f"<td>{html.escape(str(cell))}</td>" for cell in row)
        + "</tr>"
        for row in rows
    )
    return f"<tr>{header_html}</tr>{body_html}"


def _method_table_rows(headers: tuple[str, str], rows: tuple[tuple[str, str, str], ...]) -> str:
    header_html = "".join(f"<th>{html.escape(header)}</th>" for header in headers)
    body_html = ""
    for label, description, command in rows:
        link = f'<a href="method:{quote(label)}">{html.escape(label)}</a>'
        demo = f'<br/><span class="method-command">{html.escape(command)}</span>'
        body_html += (
            "<tr>"
            f"<td>{link}{demo}</td>"
            f"<td>{html.escape(description)}</td>"
            "</tr>"
        )
    return f"<tr>{header_html}</tr>{body_html}"


def _normalize_doc_command(command: str) -> str:
    command = command.strip()
    if command.startswith("."):
        return f"widget{command}"
    if command.startswith("widget.setColor("):
        return "setColor(" + command[len("widget.setColor("):]
    if command.startswith("widget.") or command.startswith("setColor("):
        return command
    return f"widget.{command}"


def _apply_preview_color(widget: QWidget, color) -> QWidget:
    for method_name in ("setAccent", "setBackground", "setForeground", "setBorder"):
        method = getattr(widget, method_name, None)
        if callable(method):
            try:
                method(color)
                return widget
            except AttributeError:
                continue
    raise AttributeError(f"{type(widget).__name__} does not support setColor().")


def _supported_fluent_method_docs(name: str) -> tuple[tuple[str, str, str], ...]:
    supported: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    probes = WIDGET_METHOD_PROBES.get(name, ()) + FLUENT_METHOD_PROBES
    for label, description, command, probe in probes:
        if label in seen:
            continue
        widget = _create_doc_preview_widget(name)
        try:
            probe(widget)
        except Exception:
            pass
        else:
            supported.append((label, description, command))
            seen.add(label)
        finally:
            widget.deleteLater()
    return tuple(supported)


def _create_doc_preview_widget(name: str) -> QWidget:
    factory = _DOC_PREVIEW_FACTORIES.get(name)
    if factory is None:
        label = QLabel(name)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label
    return factory()


def _button_preview() -> QWidget:
    widget = MonkezButton()
    widget.setText("Save")
    widget.setMinimumWidth(160)
    return widget


def _text_input_preview() -> QWidget:
    widget = MonkezTextInput()
    widget.setPlaceholderText("Customer name")
    widget.setText("Monkez")
    widget.setMinimumWidth(220)
    return widget


def _combo_preview() -> QWidget:
    widget = MonkezComboBox()
    widget.addItems(["Option 1", "Option 2", "Option 3"])
    widget.setMinimumWidth(220)
    return widget


def _checkbox_preview() -> QWidget:
    widget = MonkezCheckBox()
    widget.setText("Enable feature")
    widget.setChecked(True)
    return widget


def _radio_preview() -> QWidget:
    widget = MonkezRadioButton()
    widget.setText("Material")
    widget.setRadioStyle(2)
    widget.setChecked(True)
    return widget


def _switch_preview() -> QWidget:
    widget = MonkezSwitch()
    widget.setChecked(True)
    return widget


def _slider_preview() -> QWidget:
    widget = MonkezSlider()
    widget.setRange(0, 100)
    widget.setValue(64)
    widget.setMinimumWidth(220)
    return widget


def _progress_preview() -> QWidget:
    widget = MonkezProgressBar()
    widget.setValue(64)
    widget.setMinimumWidth(220)
    return widget


def _spin_preview() -> QWidget:
    widget = MonkezSpinBox()
    widget.setRange(0, 100)
    widget.setValue(42)
    widget.setMinimumWidth(180)
    return widget


def _double_spin_preview() -> QWidget:
    widget = MonkezDoubleSpinBox()
    widget.setDecimals(2)
    widget.setSingleStep(0.25)
    widget.setValue(12.5)
    widget.setMinimumWidth(180)
    return widget


def _dial_preview() -> QWidget:
    widget = MonkezDial()
    widget.setValue(64)
    widget.setDialStyle(1)
    widget.setMinimumSize(170, 170)
    return widget


def _date_preview() -> QWidget:
    widget = MonkezDateEdit()
    widget.setDate(QDate.currentDate())
    widget.setDisplayFormat("dd/MM/yyyy")
    widget.setMinimumWidth(190)
    return widget


def _time_preview() -> QWidget:
    widget = MonkezTimeEdit()
    widget.setTime(QTime.currentTime())
    widget.setDisplayFormat("HH:mm:ss")
    widget.setMinimumWidth(170)
    return widget


def _date_time_preview() -> QWidget:
    widget = MonkezDateTimeEdit()
    widget.setDateTime(QDateTime.currentDateTime())
    widget.setDisplayFormat("dd/MM/yyyy HH:mm")
    widget.setMinimumWidth(230)
    return widget


def _calendar_preview() -> QWidget:
    widget = MonkezCalendarWidget()
    widget.setSelectedDate(QDate.currentDate())
    widget.setMinimumSize(280, 240)
    return widget


def _lcd_preview() -> QWidget:
    widget = MonkezLCDNumber()
    widget.setDigitCount(4)
    widget.display(128)
    widget.setMinimumSize(180, 80)
    return widget


def _image_preview() -> QWidget:
    widget = MonkezImage()
    widget.set_image(_demo_pixmap())
    widget.setMinimumSize(240, 160)
    return widget


def _camera_preview() -> QWidget:
    widget = MonkezUSBCamera()
    widget.setMinimumSize(240, 160)
    return widget


def _frame_preview() -> QWidget:
    widget = MonkezFrame()
    layout = QVBoxLayout(widget)
    title = QLabel("Frame content")
    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(title)
    widget.setMinimumSize(220, 120)
    return widget


def _group_preview() -> QWidget:
    widget = MonkezGroupBox()
    widget.setTitle("Settings")
    widget.setSubtitle("Runtime configurable")
    layout = QVBoxLayout(widget)
    layout.addWidget(QLabel("Camera source"))
    combo = MonkezComboBox()
    combo.addItems(["Auto", "USB 0"])
    layout.addWidget(combo)
    widget.setMinimumSize(260, 180)
    return widget


def _scroll_preview() -> QWidget:
    widget = MonkezScrollArea()
    content = QWidget()
    layout = QVBoxLayout(content)
    for index in range(4):
        layout.addWidget(QLabel(f"Scrollable row {index + 1}"))
    widget.setWidget(content)
    widget.setWidgetResizable(True)
    widget.setMinimumSize(240, 160)
    return widget


def _radial_gauge_preview() -> QWidget:
    widget = MonkezRadialGauge()
    widget.setLabel("Pressure")
    widget.setSuffix("%")
    widget.setValue(76)
    widget.setMinimumSize(190, 190)
    return widget


def _arc_gauge_preview() -> QWidget:
    widget = MonkezArcGauge()
    widget.setLabel("Load")
    widget.setSegmented(True)
    widget.setValue(68)
    widget.setMinimumSize(210, 150)
    return widget


def _linear_gauge_preview() -> QWidget:
    widget = MonkezLinearGauge()
    widget.setLabel("Throughput")
    widget.setTargetValue(82)
    widget.setValue(64)
    widget.setMinimumSize(240, 110)
    return widget


_DOC_PREVIEW_FACTORIES: dict[str, Callable[[], QWidget]] = {
    "MonkezButton": _button_preview,
    "MonkezTextInput": _text_input_preview,
    "MonkezComboBox": _combo_preview,
    "MonkezCheckBox": _checkbox_preview,
    "MonkezRadioButton": _radio_preview,
    "MonkezSwitch": _switch_preview,
    "MonkezSlider": _slider_preview,
    "MonkezProgressBar": _progress_preview,
    "MonkezSpinBox": _spin_preview,
    "MonkezDoubleSpinBox": _double_spin_preview,
    "MonkezDial": _dial_preview,
    "MonkezDateEdit": _date_preview,
    "MonkezTimeEdit": _time_preview,
    "MonkezDateTimeEdit": _date_time_preview,
    "MonkezCalendarWidget": _calendar_preview,
    "MonkezLCDNumber": _lcd_preview,
    "MonkezImage": _image_preview,
    "MonkezUSBCamera": _camera_preview,
    "MonkezFrame": _frame_preview,
    "MonkezGroupBox": _group_preview,
    "MonkezScrollArea": _scroll_preview,
    "MonkezRadialGauge": _radial_gauge_preview,
    "MonkezArcGauge": _arc_gauge_preview,
    "MonkezLinearGauge": _linear_gauge_preview,
}


def _demo_pixmap() -> QPixmap:
    pixmap = QPixmap(560, 320)
    pixmap.setDevicePixelRatio(1.0)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    gradient = QLinearGradient(0, 0, pixmap.width(), pixmap.height())
    gradient.setColorAt(0.0, QColor("#e0f2fe"))
    gradient.setColorAt(0.46, QColor("#f8fafc"))
    gradient.setColorAt(1.0, QColor("#fee2e2"))
    painter.fillRect(pixmap.rect(), gradient)
    painter.setPen(Qt.PenStyle.NoPen)
    for color, x, y, size in (
        ("#2563eb", 76, 62, 132),
        ("#06b6d4", 168, 126, 98),
        ("#f97316", 274, 66, 116),
        ("#db2777", 352, 152, 88),
    ):
        c = QColor(color)
        c.setAlpha(205)
        painter.setBrush(c)
        painter.drawRoundedRect(x, y, size, size, 24, 24)
    painter.setPen(QColor("#0f172a"))
    font = QFont("Segoe UI", 28)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(52, 282, "Monkez Image")
    painter.end()
    return pixmap


_APP_STYLE = """
QMainWindow {
    background: #eef2f6;
}
QFrame#appRoot {
    background: #eef2f6;
}
QWidget {
    font-family: "Segoe UI";
    font-size: 10.5pt;
    color: #18202f;
}
QFrame#sidebar {
    background: #18202f;
    border-right: 1px solid #273346;
}
QLabel#brand {
    color: #ffffff;
    font-size: 25pt;
    font-weight: 800;
    line-height: 108%;
}
QLabel#sidebarCaption {
    color: #9aa8bb;
}
QLabel#sidebarLabel {
    color: #a7b6ca;
    font-size: 8.5pt;
    font-weight: 700;
    padding-top: 8px;
}
QLabel#switchLabel {
    color: #e8eef8;
}
QLabel#largeValue {
    color: #ffffff;
    font-size: 30pt;
    font-weight: 800;
}
QToolButton#themeButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 7px;
    color: #d8e0ec;
    text-align: left;
    padding: 9px 11px;
}
QToolButton#themeButton:hover {
    background: #243044;
}
QToolButton#themeButton:checked {
    background: #ffffff;
    color: #172033;
    border-color: #ffffff;
}
QToolButton#navButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 7px;
    color: #d8e0ec;
    text-align: left;
    padding: 10px 12px;
    font-weight: 650;
}
QToolButton#navButton:hover {
    background: #243044;
}
QToolButton#navButton:checked {
    background: #2563eb;
    color: #ffffff;
    border-color: #3b82f6;
}
QFrame#workspace {
    background: #f6f8fb;
}
QFrame#topHeader {
    background: transparent;
}
QLabel#heroTitle {
    color: #111827;
    font-size: 23pt;
    font-weight: 800;
}
QLabel#heroSubtitle {
    color: #637083;
}
QStackedWidget#galleryStack {
    background: transparent;
    border: 0;
}
QScrollArea#pageScroll {
    background: transparent;
    border: 0;
}
QScrollArea#pageScroll > QWidget > QWidget#pageContent {
    background: transparent;
}
QFrame#tabThemeBar {
    background: #ffffff;
    border: 1px solid #dde5ee;
    border-radius: 8px;
}
QLabel#tabThemeLabel {
    color: #64748b;
    font-size: 9pt;
    font-weight: 700;
    padding-right: 4px;
}
QToolButton#tabThemeButton {
    background: #f1f5f9;
    border: 1px solid #d8e0ea;
    border-radius: 6px;
    color: #475569;
    padding: 6px 10px;
}
QToolButton#tabThemeButton:hover {
    background: #e8eef6;
}
QToolButton#tabThemeButton:checked {
    background: #2563eb;
    border-color: #2563eb;
    color: #ffffff;
}
QFrame#showcaseCard {
    background: #ffffff;
    border: 1px solid #dde5ee;
    border-radius: 8px;
}
QFrame#showcaseCard:hover {
    border-color: #c7d3e1;
}
QWidget#demoSlot {
    background: transparent;
}
QLabel#cardTitle {
    color: #0f172a;
    font-weight: 700;
    font-size: 14pt;
}
QLabel#mutedLabel {
    color: #64748b;
}
QLabel#rowLabel {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 8px 10px;
}
QFrame#metric {
    background: #ffffff;
    border: 1px solid #dde5ee;
    border-radius: 8px;
    min-width: 88px;
}
QLabel#metricValue {
    color: #111827;
    font-size: 18pt;
    font-weight: 800;
}
QLabel#metricLabel {
    color: #657386;
    font-size: 9pt;
}
QWidget#switchRow {
    background: transparent;
}
QListWidget#docsList {
    background: #ffffff;
    border: 1px solid #e3e8ef;
    border-radius: 8px;
    padding: 8px;
}
QListWidget#docsList::item {
    padding: 9px 10px;
    border-radius: 6px;
}
QListWidget#docsList::item:selected {
    background: #dbeafe;
    color: #1d4ed8;
}
QLineEdit#docsSearch {
    background: #ffffff;
    border: 1px solid #d8e0ea;
    border-radius: 8px;
    padding: 10px 12px;
}
QLineEdit#docsSearch:focus {
    border: 2px solid #2563eb;
}
QTextBrowser#docsBrowser {
    background: #ffffff;
    border: 1px solid #e3e8ef;
    border-radius: 8px;
    padding: 18px;
}
QTextBrowser#docsBrowser h1 {
    color: #111827;
}
QTextBrowser#docsBrowser h2 {
    color: #1f2937;
}
QFrame#docsPreviewPanel {
    background: #ffffff;
    border: 1px solid #e3e8ef;
    border-radius: 8px;
}
QFrame#docsPreviewSlot {
    background: #f8fafc;
    border: 1px dashed #cbd5e1;
    border-radius: 8px;
}
QLineEdit#docsMethodInput {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 8px;
    color: #e2e8f0;
    padding: 10px 12px;
    font-family: "Cascadia Code", "Consolas";
}
QLineEdit#docsMethodInput:focus {
    border: 2px solid #2563eb;
}
QLabel#docsMethodStatus {
    color: #64748b;
    font-size: 9pt;
}
QComboBox#colorFormatCombo {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 4px 8px;
    min-height: 24px;
}
"""


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Monkez Widget Docs Lab")
    window = GalleryWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
