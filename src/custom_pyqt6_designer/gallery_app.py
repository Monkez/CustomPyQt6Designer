from __future__ import annotations

import html
import sys
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QDate, QDateTime, Qt, QTime
from PyQt6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QTextBrowser,
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


THEME_HINT = "themeIndex: 0 Material | 1 iOS | 2 Fluent | 3 Bootstrap | 4 Minimal | 5 Dark"

WIDGET_DOCS: tuple[WidgetDoc, ...] = (
    WidgetDoc(
        "MonkezButton",
        "Action",
        "Button co theme, radius, padding nho, hover/pressed va shadow.",
        (
            THEME_HINT,
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
        (THEME_HINT, "text, placeholderText", "backgroundColor, borderColor, textColor, radius"),
        ("setPlaceholderText(text)", "text()", "textChanged.connect(slot)"),
        "name_input = MonkezTextInput(); name_input.setPlaceholderText('Customer name')",
    ),
    WidgetDoc(
        "MonkezComboBox",
        "Input",
        "ComboBox custom popup de tranh popup lech ngoai dialog/window.",
        (THEME_HINT, "borderColor, backgroundColor, hoverBackgroundColor", "textColor, hoverTextColor, borderRadius"),
        ("addItem(text)", "addItemWithIcon(path, text)", "currentText()", "currentIndexChanged.connect(slot)"),
        "combo = MonkezComboBox(); combo.addItems(['Auto', 'Manual'])",
    ),
    WidgetDoc(
        "MonkezCheckBox",
        "Action",
        "Checkbox theme-aware cho form cai dat.",
        (THEME_HINT, "checked", "textColor, indicatorColor, accentColor", "shadowEnabled"),
        ("setChecked(value)", "isChecked()", "toggled.connect(slot)"),
        "check = MonkezCheckBox(); check.setText('Enable cache')",
    ),
    WidgetDoc(
        "MonkezRadioButton",
        "Action",
        "Radio button voi nhieu style va mau tuy bien.",
        (THEME_HINT, "radioStyle, checked", "accentColor, textColor, ringColor", "shadowEnabled"),
        ("setChecked(value)", "isChecked()", "toggled.connect(slot)"),
        "radio = MonkezRadioButton(); radio.setText('Material')",
    ),
    WidgetDoc(
        "MonkezSwitch",
        "Action",
        "Switch bat/tat gon cho panel dieu khien.",
        (THEME_HINT, "checked", "trackOnColor, trackOffColor, thumbColor", "shadowEnabled"),
        ("setChecked(value)", "isChecked()", "toggled.connect(slot)"),
        "switch = MonkezSwitch(); switch.setChecked(True)",
    ),
    WidgetDoc(
        "MonkezSlider",
        "Value",
        "Slider ngang/doc co track, handle va theme rieng.",
        (THEME_HINT, "minimum, maximum, value", "trackColor, valueColor, handleColor"),
        ("setRange(min, max)", "setValue(value)", "valueChanged.connect(slot)"),
        "slider = MonkezSlider(); slider.setRange(0, 100); slider.setValue(42)",
    ),
    WidgetDoc(
        "MonkezProgressBar",
        "Value",
        "Progress bar co the dat thanh line mong bang barHeight.",
        (THEME_HINT, "value, textVisible", "barHeight, barColor, trackColor, textColor, radius"),
        ("setValue(value)", "setBarHeight(height)", "setTextVisible(value)"),
        "progress = MonkezProgressBar(); progress.setBarHeight(6); progress.setTextVisible(False)",
    ),
    WidgetDoc(
        "MonkezSpinBox",
        "Input",
        "SpinBox so nguyen cho thiet lap tham so.",
        (THEME_HINT, "minimum, maximum, value", "controlHeight, radius, accentColor"),
        ("setRange(min, max)", "setValue(value)", "valueChanged.connect(slot)"),
        "spin = MonkezSpinBox(); spin.setRange(0, 100)",
    ),
    WidgetDoc(
        "MonkezDoubleSpinBox",
        "Input",
        "SpinBox so thuc cho ty le, threshold va gia tri do luong.",
        (THEME_HINT, "minimum, maximum, value, decimals", "controlHeight, radius, accentColor"),
        ("setDecimals(count)", "setSingleStep(step)", "valueChanged.connect(slot)"),
        "spin = MonkezDoubleSpinBox(); spin.setDecimals(2); spin.setSingleStep(0.25)",
    ),
    WidgetDoc(
        "MonkezDial",
        "Value",
        "Dial dang ring, knob hoac needle cho dashboard.",
        (THEME_HINT, "dialStyle: 0 Ring | 1 Knob | 2 Needle", "trackWidth, handleSize, showValue, showTicks, tickCount"),
        ("setDialStyle(index)", "setValue(value)", "valueChanged.connect(slot)"),
        "dial = MonkezDial(); dial.setDialStyle(1); dial.setValue(64)",
    ),
    WidgetDoc(
        "MonkezDateEdit",
        "Date/time",
        "Date input co calendar popup va icon ve bang QPainter.",
        (THEME_HINT, "date, displayFormat, calendarPopup", "controlHeight, radius, accentColor"),
        ("setDate(QDate)", "date()", "dateChanged.connect(slot)"),
        "date_edit = MonkezDateEdit(); date_edit.setDisplayFormat('dd/MM/yyyy')",
    ),
    WidgetDoc(
        "MonkezTimeEdit",
        "Date/time",
        "Time input voi step arrows custom va style dong nhat.",
        (THEME_HINT, "time, displayFormat", "controlHeight, radius, accentColor"),
        ("setTime(QTime)", "time()", "timeChanged.connect(slot)"),
        "time_edit = MonkezTimeEdit(); time_edit.setDisplayFormat('HH:mm:ss')",
    ),
    WidgetDoc(
        "MonkezDateTimeEdit",
        "Date/time",
        "Date-time input ket hop calendar popup va time editor.",
        (THEME_HINT, "dateTime, displayFormat, calendarPopup", "controlHeight, radius, accentColor"),
        ("setDateTime(QDateTime)", "dateTime()", "dateTimeChanged.connect(slot)"),
        "date_time = MonkezDateTimeEdit(); date_time.setDisplayFormat('dd/MM/yyyy HH:mm')",
    ),
    WidgetDoc(
        "MonkezCalendarWidget",
        "Date/time",
        "Calendar custom paint cho ngay duoc chon, today va weekend.",
        (THEME_HINT, "selectedDate", "backgroundColor, textColor, accentColor", "weekendColor, todayColor, outsideMonthColor"),
        ("setSelectedDate(QDate)", "selectionChanged.connect(slot)", "setGridVisible(value)"),
        "calendar = MonkezCalendarWidget(); calendar.setSelectedDate(QDate.currentDate())",
    ),
    WidgetDoc(
        "MonkezLCDNumber",
        "Display",
        "LCD number cho counter, sensor value hoac status numeric.",
        (THEME_HINT, "value", "digitCount, segmentStyle, foreground/background colors"),
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
        (THEME_HINT, "backgroundColor, borderColor, radius, borderWidth, elevation"),
        ("setLayout(layout)", "layout().addWidget(widget)"),
        "frame = MonkezFrame(); frame.setElevation(2)",
    ),
    WidgetDoc(
        "MonkezGroupBox",
        "Container",
        "Group box co header custom, title/subtitle, indicator va auto header height.",
        (
            THEME_HINT,
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
        (THEME_HINT, "backgroundColor, borderColor", "scrollbarWidth, scrollbarColor, scrollbarTrackColor"),
        ("setWidget(widget)", "setWidgetResizable(value)"),
        "scroll = MonkezScrollArea(); scroll.setWidget(content)",
    ),
    WidgetDoc(
        "MonkezRadialGauge",
        "Gauge",
        "Gauge tron co ticks, needle, label va scale labels.",
        (THEME_HINT, "value, label, suffix", "majorTicks, minorTicks, showNeedle, showScaleLabels", "trackColor, valueColor"),
        ("setRange(min, max)", "setValue(value)", "setLabel(text)"),
        "gauge = MonkezRadialGauge(); gauge.setLabel('Pressure'); gauge.setValue(76)",
    ),
    WidgetDoc(
        "MonkezArcGauge",
        "Gauge",
        "Gauge nua vong cho KPI/status voi warning va danger thresholds.",
        (THEME_HINT, "value, label, suffix", "arcWidth, warningThreshold, dangerThreshold", "segmented, segmentCount"),
        ("setValue(value)", "setSegmented(value)", "setDangerThreshold(value)"),
        "gauge = MonkezArcGauge(); gauge.setSegmented(True)",
    ),
    WidgetDoc(
        "MonkezLinearGauge",
        "Gauge",
        "Gauge dang bar ngang/doc, co target marker.",
        (THEME_HINT, "value, label, suffix", "vertical, barThickness, targetValue, showTarget, rounded"),
        ("setValue(value)", "setVertical(value)", "setTargetValue(value)"),
        "gauge = MonkezLinearGauge(); gauge.setTargetValue(80)",
    ),
)


class GalleryWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Monkez PyQt6 Widgets Gallery")
        self.resize(1180, 780)
        icon = Path(__file__).resolve().parents[2] / "logo.ico"
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))

        tabs = QTabWidget()
        tabs.addTab(self._build_controls_tab(), "Controls")
        tabs.addTab(self._build_values_tab(), "Values")
        tabs.addTab(self._build_media_tab(), "Media & Containers")
        tabs.addTab(self._build_gauges_tab(), "Gauges")
        tabs.addTab(self._build_docs_tab(), "Docs")
        self.setCentralWidget(tabs)
        self.setStyleSheet(_APP_STYLE)

    def _tab_page(self) -> tuple[QWidget, QGridLayout]:
        page = QWidget()
        layout = QGridLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)
        return page, layout

    def _build_controls_tab(self) -> QWidget:
        page, grid = self._tab_page()

        primary = MonkezButton()
        primary.setText("Material filled")
        primary.setThemeIndex(0)

        outline = MonkezButton()
        outline.setText("iOS outline")
        outline.setThemeIndex(1)
        outline.setButtonTypeIndex(1)

        compact = MonkezButton()
        compact.setText("X")
        compact.setPaddingX(2)
        compact.setPaddingY(1)
        compact.setFixedSize(32, 28)

        text_input = MonkezTextInput()
        text_input.setPlaceholderText("Search product, customer, order...")

        combo = MonkezComboBox()
        combo.clear()
        combo.addItems(["Automatic", "Manual review", "Disabled"])
        combo.setCurrentIndex(1)

        check = MonkezCheckBox()
        check.setText("Enable notifications")
        check.setChecked(True)

        radio_a = MonkezRadioButton()
        radio_a.setText("Material")
        radio_a.setChecked(True)
        radio_b = MonkezRadioButton()
        radio_b.setText("iOS")
        radio_b.setThemeIndex(1)

        switch = MonkezSwitch()
        switch.setChecked(True)

        grid.addWidget(self._card("Buttons", [primary, outline, compact], "Filled, outline and compact action states."), 0, 0)
        grid.addWidget(self._card("Input", [text_input, combo], "Form controls with styled focus and popup."), 0, 1)
        grid.addWidget(self._card("Choices", [check, radio_a, radio_b, switch], "Checkbox, radio and switch variants."), 1, 0, 1, 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        return page

    def _build_values_tab(self) -> QWidget:
        page, grid = self._tab_page()

        slider = MonkezSlider()
        slider.setValue(58)
        progress = MonkezProgressBar()
        progress.setValue(58)
        slim_progress = MonkezProgressBar()
        slim_progress.setValue(72)
        slim_progress.setBarHeight(6)
        slim_progress.setTextVisible(False)

        spin = MonkezSpinBox()
        spin.setValue(42)
        double_spin = MonkezDoubleSpinBox()
        double_spin.setDecimals(2)
        double_spin.setValue(18.75)
        dial_ring = MonkezDial()
        dial_ring.setValue(64)
        dial_knob = MonkezDial()
        dial_knob.setDialStyle(1)
        dial_knob.setThemeIndex(1)
        dial_knob.setValue(38)
        lcd = MonkezLCDNumber()
        lcd.display(128)

        date_edit = MonkezDateEdit()
        date_edit.setDate(QDate.currentDate())
        time_edit = MonkezTimeEdit()
        time_edit.setTime(QTime.currentTime())
        dt_edit = MonkezDateTimeEdit()
        dt_edit.setDateTime(QDateTime.currentDateTime())
        calendar = MonkezCalendarWidget()
        calendar.setSelectedDate(QDate.currentDate())

        grid.addWidget(self._card("Progress", [slider, progress, slim_progress], "Sliders and progress bars can stay compact."), 0, 0)
        grid.addWidget(self._card("Number inputs", [spin, double_spin, lcd], "Numeric entry and display widgets."), 0, 1)
        grid.addWidget(self._card("Dial", [dial_ring, dial_knob], "Ring and knob dial styles."), 1, 0)
        grid.addWidget(self._card("Date and time", [date_edit, time_edit, dt_edit, calendar], "Calendar popup and custom calendar view."), 1, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        return page

    def _build_media_tab(self) -> QWidget:
        page, grid = self._tab_page()

        frame = MonkezFrame()
        frame.setMinimumHeight(96)

        group = MonkezGroupBox()
        group.setTitle("Production line")
        group.setSubtitle("Auto header height, subtitle can be hidden")
        group.setCheckable(True)
        group.setChecked(True)
        group_layout = QVBoxLayout(group)
        label = QLabel("Nested content keeps normal Qt layouts.")
        label.setObjectName("mutedLabel")
        group_layout.addWidget(label)

        scroll = MonkezScrollArea()
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        for index in range(1, 9):
            item = QLabel(f"Parameter row {index:02d}")
            item.setObjectName("rowLabel")
            scroll_layout.addWidget(item)
        scroll.setWidget(scroll_content)

        image = MonkezImage()
        image.set_image(_demo_pixmap())
        image.setMinimumHeight(190)

        camera = MonkezUSBCamera()
        camera.setMinimumHeight(190)
        camera.image_label.setText("Camera preview is off by default")

        grid.addWidget(self._card("Containers", [frame, group, scroll], "Frame, GroupBox and ScrollArea for real forms."), 0, 0)
        grid.addWidget(self._card("Media", [image, camera], "Image scales smoothly; camera starts only when requested."), 0, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        return page

    def _build_gauges_tab(self) -> QWidget:
        page, grid = self._tab_page()

        radial = MonkezRadialGauge()
        radial.setLabel("Pressure")
        radial.setValue(76)

        arc = MonkezArcGauge()
        arc.setLabel("Load")
        arc.setValue(84)
        arc.setSegmented(True)

        linear = MonkezLinearGauge()
        linear.setLabel("Throughput")
        linear.setValue(68)
        linear.setTargetValue(82)

        vertical = MonkezLinearGauge()
        vertical.setVertical(True)
        vertical.setLabel("Tank")
        vertical.setValue(56)
        vertical.setMinimumHeight(220)

        grid.addWidget(self._card("Radial gauge", [radial], "Full circular instrument style."), 0, 0)
        grid.addWidget(self._card("Arc gauge", [arc], "Compact KPI gauge with thresholds."), 0, 1)
        grid.addWidget(self._card("Linear gauges", [linear, vertical], "Horizontal and vertical gauge modes."), 1, 0, 1, 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        return page

    def _build_docs_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header = QLabel("Widget documentation")
        header.setObjectName("pageTitle")
        layout.addWidget(header)

        search = QLineEdit()
        search.setPlaceholderText("Search widget docs...")
        search.setObjectName("docsSearch")
        search.textChanged.connect(self._filter_docs)
        layout.addWidget(search)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._docs_list = QListWidget()
        self._docs_browser = QTextBrowser()
        self._docs_browser.setOpenExternalLinks(True)
        self._docs_list.setObjectName("docsList")
        self._docs_browser.setObjectName("docsBrowser")
        self._populate_docs(WIDGET_DOCS)
        self._docs_list.currentItemChanged.connect(self._show_doc)
        splitter.addWidget(self._docs_list)
        splitter.addWidget(self._docs_browser)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([300, 820])
        layout.addWidget(splitter, 1)
        self._docs_list.setCurrentRow(0)
        return page

    def _populate_docs(self, docs: tuple[WidgetDoc, ...]) -> None:
        self._docs_list.clear()
        for doc in docs:
            item = QListWidgetItem(doc.name)
            item.setData(Qt.ItemDataRole.UserRole, doc)
            self._docs_list.addItem(item)
        if docs:
            self._docs_list.setCurrentRow(0)

    def _filter_docs(self, text: str) -> None:
        needle = text.strip().lower()
        if not needle:
            self._populate_docs(WIDGET_DOCS)
            return
        filtered = tuple(
            doc
            for doc in WIDGET_DOCS
            if needle in doc.name.lower()
            or needle in doc.group.lower()
            or needle in doc.purpose.lower()
            or any(needle in prop.lower() for prop in doc.properties)
        )
        self._populate_docs(filtered)

    def _show_doc(self, current: QListWidgetItem | None, previous: QListWidgetItem | None = None) -> None:
        if current is None:
            self._docs_browser.clear()
            return
        doc: WidgetDoc = current.data(Qt.ItemDataRole.UserRole)
        props = "".join(f"<li>{html.escape(prop)}</li>" for prop in doc.properties)
        methods = "".join(f"<li>{html.escape(method)}</li>" for method in doc.methods)
        usage = html.escape(doc.usage)
        self._docs_browser.setHtml(
            f"""
            <h1>{html.escape(doc.name)}</h1>
            <p class="tag">{html.escape(doc.group)}</p>
            <p>{html.escape(doc.purpose)}</p>
            <h2>Properties</h2>
            <ul>{props}</ul>
            <h2>Methods / Signals</h2>
            <ul>{methods}</ul>
            <h2>Usage</h2>
            <pre>{usage}</pre>
            """
        )

    def _card(self, title: str, widgets: list[QWidget], description: str) -> QFrame:
        card = QFrame()
        card.setObjectName("demoCard")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(12)

        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setObjectName("mutedLabel")
        layout.addWidget(title_label)
        layout.addWidget(desc_label)

        for widget in widgets:
            wrapper = QWidget()
            wrapper_layout = QHBoxLayout(wrapper)
            wrapper_layout.setContentsMargins(0, 2, 0, 2)
            wrapper_layout.addWidget(widget)
            wrapper_layout.addStretch(1)
            layout.addWidget(wrapper)
        layout.addStretch(1)
        return card


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
QMainWindow, QWidget {
    background: #f6f8fb;
    color: #172033;
    font-family: "Segoe UI";
    font-size: 10.5pt;
}
QTabWidget::pane {
    border: 0;
}
QTabBar::tab {
    padding: 11px 18px;
    margin: 0 2px;
    color: #536176;
    background: transparent;
}
QTabBar::tab:selected {
    color: #0f172a;
    border-bottom: 3px solid #2563eb;
}
QFrame#demoCard {
    background: #ffffff;
    border: 1px solid #e3e8ef;
    border-radius: 8px;
}
QLabel#cardTitle, QLabel#pageTitle {
    color: #0f172a;
    font-weight: 700;
}
QLabel#cardTitle {
    font-size: 14pt;
}
QLabel#pageTitle {
    font-size: 18pt;
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
"""


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("MonkezDesigner Gallery")
    window = GalleryWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
