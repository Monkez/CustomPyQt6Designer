from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPixmap
from PyQt6.QtWidgets import QApplication, QDialog, QLabel, QVBoxLayout, QWidget

from custom_pyqt6_designer import monkez_widgets
from custom_pyqt6_designer.monkez_widgets import (
    MonkezButton,
    MonkezCalendarWidget,
    MonkezArcGauge,
    MonkezComboBox,
    MonkezDial,
    MonkezGroupBox,
    MonkezImage,
    MonkezLinearGauge,
    MonkezRadialGauge,
    MonkezRadioButton,
    MonkezUSBCamera,
)


class WidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_all_widgets_construct(self) -> None:
        self.assertEqual(len(monkez_widgets.__all__), len(set(monkez_widgets.__all__)))
        for name in monkez_widgets.__all__:
            widget = getattr(monkez_widgets, name)()
            self.assertEqual(type(widget).__name__, name)
            widget.deleteLater()

    def test_themed_widgets_expose_numeric_theme_property(self) -> None:
        excluded = {"MonkezImage", "MonkezUSBCamera"}
        for name in monkez_widgets.__all__:
            if name in excluded:
                continue
            widget = getattr(monkez_widgets, name)()
            self.assertGreaterEqual(widget.metaObject().indexOfProperty("themeIndex"), 0, name)
            widget.setProperty("themeIndex", 5)
            self.assertEqual(widget.property("themeIndex"), 5, name)
            widget.deleteLater()

    def test_fluent_api_methods_update_supported_widget_properties(self) -> None:
        button = MonkezButton()
        self.assertIs(button.setBackground("#123456"), button)
        self.assertEqual(button.activeColor, QColor("#123456"))
        button.setAccent("#654321").setForeground("#ffffff").setContentPadding(7, 3)
        self.assertEqual(button.activeColor, QColor("#654321"))
        self.assertEqual(button.textColor, QColor("#ffffff"))
        self.assertEqual(button.paddingX, 7)
        self.assertEqual(button.paddingY, 3)
        button.deleteLater()

        text_input = monkez_widgets.MonkezTextInput()
        text_input.setColors(background="#101010", text="#f8fafc", border="#334155")
        self.assertEqual(text_input.backgroundColor, QColor("#101010"))
        self.assertEqual(text_input.textColor, QColor("#f8fafc"))
        self.assertEqual(text_input.borderColor, QColor("#334155"))
        text_input.deleteLater()

        switch = monkez_widgets.MonkezSwitch()
        switch.setTrack("#222222").setThumb("#eeeeee").setAccent("#22c55e")
        self.assertEqual(switch.trackColor, QColor("#222222"))
        self.assertEqual(switch.thumbColor, QColor("#eeeeee"))
        self.assertEqual(switch.checkedColor, QColor("#22c55e"))
        switch.deleteLater()

        slider = monkez_widgets.MonkezSlider()
        slider.setTrack("#dbeafe").setAccent("#2563eb").setThumb((255, 255, 255))
        self.assertEqual(slider.grooveColor, QColor("#dbeafe"))
        self.assertEqual(slider.filledColor, QColor("#2563eb"))
        self.assertEqual(slider.handleColor, QColor(255, 255, 255))
        slider.deleteLater()

        radio = monkez_widgets.MonkezRadioButton()
        self.assertIs(radio.setBackground("#2563eb"), radio)
        self.assertEqual(radio.backgroundColor, QColor("#2563eb"))
        radio.deleteLater()

        group_box = monkez_widgets.MonkezGroupBox()
        self.assertIs(group_box.setContentPadding(15), group_box)
        self.assertEqual(group_box.contentPadding, 15)
        group_box.deleteLater()

    def test_button_does_not_force_preview_geometry_to_theme_size(self) -> None:
        button = MonkezButton()
        button.setText("X")
        button.resize(24, 24)
        button.setThemeIndex(0)
        button.show()
        self.app.processEvents()

        self.assertLessEqual(button.minimumSizeHint().width(), 24)
        self.assertLessEqual(button.minimumSizeHint().height(), 24)
        self.assertLessEqual(button.minimumWidth(), 24)
        self.assertLessEqual(button.minimumHeight(), 24)
        self.assertEqual(button.paddingX, 4)
        self.assertEqual(button.paddingY, 2)
        self.assertEqual(button.size().width(), 24)
        self.assertEqual(button.size().height(), 24)
        button.close()
        button.deleteLater()

    def test_widgets_do_not_set_large_hard_minimum_sizes(self) -> None:
        allowed_explicit_minimums = {"MonkezImage", "MonkezUSBCamera"}
        for name in monkez_widgets.__all__:
            widget = getattr(monkez_widgets, name)()
            if widget.metaObject().indexOfProperty("themeIndex") >= 0:
                widget.setProperty("themeIndex", 1)

            minimum = widget.minimumSize()
            self.assertLessEqual(minimum.width(), 48, name)
            self.assertLessEqual(minimum.height(), 36, name)
            if name not in allowed_explicit_minimums:
                self.assertEqual(minimum.width(), 0, name)
                self.assertEqual(minimum.height(), 0, name)
            widget.deleteLater()

    def test_progress_bar_height_does_not_lock_widget_geometry(self) -> None:
        progress = monkez_widgets.MonkezProgressBar()
        progress.barHeight = 4

        self.assertEqual(progress.minimumHeight(), 0)
        self.assertEqual(progress.maximumHeight(), 16777215)
        self.assertNotIn("min-height", progress.styleSheet())
        self.assertNotIn("max-height", progress.styleSheet())
        progress.deleteLater()

    def test_button_hover_brightens_current_background_color(self) -> None:
        button = MonkezButton()
        active = QColor("#c00000")
        hovered = active.lighter(112)
        button.activeColor = active
        button._hovered = True
        button._update_style()

        self.assertIn(
            f"rgba({hovered.red()}, {hovered.green()}, {hovered.blue()}, {hovered.alpha()})",
            button.styleSheet(),
        )
        button.deleteLater()

    def test_button_press_darkens_current_background_color(self) -> None:
        button = MonkezButton()
        active = QColor("#c00000")
        pressed = active.darker(108)
        button.activeColor = active
        button._pressed = True
        button._update_style()

        self.assertIn(
            f"rgba({pressed.red()}, {pressed.green()}, {pressed.blue()}, {pressed.alpha()})",
            button.styleSheet(),
        )
        button.deleteLater()

    def test_outlined_button_has_hover_and_press_highlight(self) -> None:
        button = MonkezButton()
        button.buttonTypeIndex = 1
        normal_style = button.styleSheet()

        button._hovered = True
        button._update_style()
        hover_style = button.styleSheet()

        button._pressed = True
        button._update_style()
        pressed_style = button.styleSheet()

        self.assertNotEqual(hover_style, normal_style)
        self.assertNotEqual(pressed_style, hover_style)
        self.assertIn("border:", pressed_style)
        self.assertIn("background-color: rgba", pressed_style)
        button.deleteLater()

    def test_image_reuses_scaled_pixmap_until_source_or_size_changes(self) -> None:
        widget = MonkezImage()
        widget.resize(320, 180)
        pixmap = QPixmap(640, 480)
        pixmap.fill(QColor("#1677d2"))
        widget.set_image(pixmap)
        widget.show()
        self.app.processEvents()

        widget._update_pixmap()
        first_key = widget._scaled_pixmap.cacheKey()
        widget._update_pixmap()
        self.assertEqual(widget._scaled_pixmap.cacheKey(), first_key)

        widget.resize(400, 220)
        self.app.processEvents()
        widget._update_pixmap()
        self.assertNotEqual(widget._scaled_pixmap.cacheKey(), first_key)
        widget.close()

    def test_image_scaling_does_not_lock_window_minimum_size(self) -> None:
        widget = MonkezImage()
        pixmap = QPixmap(1200, 800)
        pixmap.fill(QColor("#1976d2"))
        widget.set_image(pixmap)
        widget.resize(720, 480)
        widget.show()
        self.app.processEvents()
        widget._update_pixmap()

        self.assertGreater(widget.image_label.pixmap().width(), 300)
        self.assertLessEqual(widget.minimumSizeHint().width(), 24)
        self.assertLessEqual(widget.minimumSizeHint().height(), 24)
        self.assertLessEqual(widget.image_label.minimumSizeHint().width(), 0)
        self.assertLessEqual(widget.image_label.minimumSizeHint().height(), 0)

        widget.resize(80, 60)
        self.app.processEvents()
        widget._update_pixmap()

        self.assertEqual(widget.size().width(), 80)
        self.assertEqual(widget.size().height(), 60)
        self.assertLessEqual(widget.image_label.pixmap().width(), 80)
        widget.close()
        widget.deleteLater()

    def test_image_uses_physical_pixels_for_high_dpi_scaling(self) -> None:
        widget = MonkezImage()
        widget._device_pixel_ratio = lambda: 2.0
        pixmap = QPixmap(1200, 800)
        pixmap.fill(QColor("#1976d2"))
        widget.set_image(pixmap)
        widget.resize(300, 200)
        widget.show()
        self.app.processEvents()
        widget._update_pixmap()

        rendered = widget.image_label.pixmap()

        self.assertEqual(rendered.devicePixelRatio(), 2.0)
        self.assertGreaterEqual(rendered.width(), 550)
        self.assertLessEqual(rendered.deviceIndependentSize().width(), 300)
        self.assertLessEqual(rendered.deviceIndependentSize().height(), 200)
        widget.close()
        widget.deleteLater()

    def test_image_does_not_lock_parent_window_after_growing(self) -> None:
        window = QWidget()
        layout = QVBoxLayout(window)
        widget = MonkezImage()
        layout.addWidget(widget)
        pixmap = QPixmap(1600, 1000)
        pixmap.fill(QColor("#38bdf8"))
        widget.set_image(pixmap)

        window.resize(900, 600)
        window.show()
        self.app.processEvents()
        widget._update_pixmap()
        large_width = widget.image_label.pixmap().width()

        window.resize(180, 120)
        self.app.processEvents()
        widget._update_pixmap()

        self.assertGreater(large_width, 500)
        self.assertLessEqual(window.layout().totalMinimumSize().width(), 48)
        self.assertLessEqual(window.layout().totalMinimumSize().height(), 48)
        self.assertLessEqual(widget.image_label.pixmap().width(), 180)
        window.close()
        widget.deleteLater()
        window.deleteLater()

    def test_camera_display_fps_and_fast_scaling(self) -> None:
        camera = MonkezUSBCamera()
        self.assertFalse(camera.smoothScaling)
        camera.displayFps = 240
        self.assertEqual(camera.displayFps, 120)
        camera.fps = 0
        self.assertEqual(camera.fps, 1)
        camera.deleteLater()

    def test_group_box_exposes_polished_header_properties(self) -> None:
        group = MonkezGroupBox()
        group.title = "Account settings"
        group.subtitle = "Manage profile and preferences"
        group.subtitleVisible = False
        group.checkable = True
        group.checked = True
        group.themeIndex = 5

        self.assertEqual(group.subtitle, "Manage profile and preferences")
        self.assertFalse(group.subtitleVisible)
        self.assertEqual(group.title, "Account settings")
        title_property = group.metaObject().property(group.metaObject().indexOfProperty("title"))
        self.assertTrue(title_property.isDesignable())
        self.assertTrue(title_property.isWritable())
        self.assertGreaterEqual(group.metaObject().indexOfProperty("title"), group.metaObject().propertyOffset())
        self.assertGreaterEqual(group.metaObject().indexOfProperty("subtitleVisible"), group.metaObject().propertyOffset())
        self.assertEqual(group.themeIndex, 5)
        self.assertGreaterEqual(group.contentsMargins().top(), group.headerHeight)
        self.assertTrue(group.checked)
        group.deleteLater()

    def test_group_box_renders_with_title_property_and_child_layout(self) -> None:
        group = MonkezGroupBox()
        group.title = "Rendered title"
        group.subtitle = "Rendered subtitle"
        group.subtitleVisible = False
        layout = QVBoxLayout(group)
        layout.addWidget(QLabel("Child content"))
        group.resize(320, 220)
        group.show()
        self.app.processEvents()

        pixmap = group.grab()

        self.assertFalse(pixmap.isNull())
        self.assertEqual(group.title, "Rendered title")
        self.assertEqual(group.subtitle, "Rendered subtitle")
        self.assertFalse(group.subtitleVisible)
        group.close()
        group.deleteLater()

    def test_group_box_auto_header_height_tracks_subtitle_and_font(self) -> None:
        group = MonkezGroupBox()
        group.subtitle = "Secondary information"
        with_subtitle = group.headerHeight
        group.subtitleVisible = False
        title_only = group.headerHeight
        font = group.font()
        font.setPointSize(font.pointSize() + 8)
        group.setFont(font)
        large_title = group.headerHeight

        self.assertLess(title_only, with_subtitle)
        self.assertGreater(large_title, title_only)
        self.assertTrue(group.autoHeaderHeight)
        group.deleteLater()

    def test_radio_dial_and_gauges_expose_distinct_styles_and_shadow(self) -> None:
        radio = MonkezRadioButton()
        dial = MonkezDial()
        gauges = (MonkezRadialGauge(), MonkezArcGauge(), MonkezLinearGauge())

        radio.radioStyle = 2
        dial.dialStyle = 2
        radio.shadowEnabled = True
        dial.shadowEnabled = True
        self.assertEqual(int(radio.radioStyle), 2)
        self.assertEqual(int(dial.dialStyle), 2)
        self.assertIsNotNone(radio.graphicsEffect())
        self.assertIsNotNone(dial.graphicsEffect())

        for gauge in gauges:
            gauge.shadowEnabled = True
            gauge.resize(gauge.sizeHint())
            gauge.show()
            self.app.processEvents()
            self.assertFalse(gauge.grab().isNull())
            self.assertIsNotNone(gauge.graphicsEffect())
            gauge.close()
            gauge.deleteLater()
        radio.deleteLater()
        dial.deleteLater()

    def test_combo_popup_has_no_native_black_frame_or_shadow(self) -> None:
        combo = MonkezComboBox()
        popup = combo._popup

        self.assertTrue(popup.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))
        self.assertTrue(popup.windowFlags() & Qt.WindowType.NoDropShadowWindowHint)
        self.assertTrue(popup.windowFlags() & Qt.WindowType.FramelessWindowHint)
        self.assertTrue(popup.windowFlags() & Qt.WindowType.Popup)
        self.assertEqual(popup.contentsMargins().left(), 0)
        self.assertEqual(popup.contentsMargins().top(), 0)
        self.assertEqual(popup.contentsMargins().right(), 0)
        self.assertEqual(popup.contentsMargins().bottom(), 0)
        self.assertIs(popup.view.model(), combo.model())
        combo.deleteLater()

    def test_combo_popup_is_owned_by_dialog_window(self) -> None:
        dialog = QDialog()
        layout = QVBoxLayout(dialog)
        combo = MonkezComboBox(dialog)
        combo.addItems(["A", "B", "C"])
        layout.addWidget(combo)
        dialog.show()
        self.app.processEvents()

        combo.showPopup()
        self.app.processEvents()

        self.assertIs(combo._popup.parentWidget(), dialog)
        self.assertTrue(combo._popup.windowFlags() & Qt.WindowType.Popup)
        combo.hidePopup()
        dialog.close()
        dialog.deleteLater()

    def test_combo_can_use_compact_designer_height(self) -> None:
        combo = MonkezComboBox()
        combo.themeIndex = 1
        combo.setFixedHeight(24)
        combo.show()
        self.app.processEvents()

        self.assertEqual(combo.height(), 24)
        self.assertLessEqual(combo.minimumHeight(), 24)
        self.assertNotIn("min-height", combo.styleSheet())
        self.assertLessEqual(combo._popup.view.sizeHintForRow(0), 32)
        self.assertEqual(combo._popup.layout().contentsMargins().left(), 3)
        combo.close()
        combo.deleteLater()

    def test_stepper_and_date_button_hover_regions_do_not_cover_outer_border(self) -> None:
        for widget_cls in (
            monkez_widgets.MonkezDateEdit,
            monkez_widgets.MonkezDateTimeEdit,
            monkez_widgets.MonkezTimeEdit,
            monkez_widgets.MonkezSpinBox,
            monkez_widgets.MonkezDoubleSpinBox,
        ):
            widget = widget_cls()
            style = widget.styleSheet()

            self.assertIn("margin: 1px", style, widget_cls.__name__)
            self.assertIn("border-right: 1px solid transparent", style, widget_cls.__name__)
            self.assertIn("background-color: transparent", style, widget_cls.__name__)
            self.assertIn("border-left: 1px solid", style, widget_cls.__name__)
            self.assertNotRegex(style, r":hover \{[^}]*border", widget_cls.__name__)
            widget.deleteLater()

    def test_calendar_exposes_polished_date_colors_and_headers(self) -> None:
        calendar = MonkezCalendarWidget()
        style = calendar.styleSheet()

        self.assertEqual(
            calendar.verticalHeaderFormat(),
            calendar.VerticalHeaderFormat.NoVerticalHeader,
        )
        self.assertIn("MonkezCalendarWidget QSpinBox::up-button", style)
        self.assertIn("width: 0px", style)
        self.assertIn("selection-background-color", style)
        for property_name in ("weekendColor", "todayColor", "outsideMonthColor"):
            self.assertGreaterEqual(calendar.metaObject().indexOfProperty(property_name), 0)
        self.assertGreaterEqual(calendar.sizeHint().width(), 340)
        self.assertGreaterEqual(calendar.sizeHint().height(), 280)
        self.assertLessEqual(calendar.minimumSizeHint().width(), 120)
        self.assertLessEqual(calendar.minimumSizeHint().height(), 100)
        calendar.deleteLater()


if __name__ == "__main__":
    unittest.main()
