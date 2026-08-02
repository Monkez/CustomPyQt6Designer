"""Public custom widget exports with startup-friendly lazy imports."""

from __future__ import annotations

from importlib import import_module

from .app_branding import apply_designer_branding
from .fluent_api import install_fluent_api


_WIDGET_MODULES = {
    "MonkezButton": ".monkez_button",
    "MonkezCheckBox": ".monkez_checkbox",
    "MonkezComboBox": ".monkez_combobox",
    "MonkezFrame": ".monkez_containers",
    "MonkezGroupBox": ".monkez_containers",
    "MonkezScrollArea": ".monkez_containers",
    "MonkezCalendarWidget": ".monkez_datetime_widgets",
    "MonkezDateEdit": ".monkez_datetime_widgets",
    "MonkezDateTimeEdit": ".monkez_datetime_widgets",
    "MonkezTimeEdit": ".monkez_datetime_widgets",
    "MonkezLCDNumber": ".monkez_display_widgets",
    "MonkezStatusBadge": ".monkez_feedback_widgets",
    "MonkezLoadingIndicator": ".monkez_feedback_widgets",
    "MonkezLoadingOverlay": ".monkez_feedback_widgets",
    "MonkezToast": ".monkez_feedback_widgets",
    "MonkezArcGauge": ".monkez_gauges",
    "MonkezLinearGauge": ".monkez_gauges",
    "MonkezRadialGauge": ".monkez_gauges",
    "MonkezImage": ".monkez_image",
    "MonkezProgressBar": ".monkez_progress_bar",
    "MonkezPagination": ".monkez_pagination",
    "MonkezTable": ".monkez_table",
    "MonkezRangeSlider": ".monkez_range_slider",
    "MonkezSegmentedControl": ".monkez_navigation_widgets",
    "MonkezBreadcrumb": ".monkez_navigation_widgets",
    "MonkezRadioButton": ".monkez_radio_button",
    "MonkezSlider": ".monkez_slider",
    "MonkezSplashScreen": ".monkez_splash_screen",
    "MonkezSwitch": ".monkez_switch",
    "MonkezTextInput": ".monkez_text_input",
    "MonkezFilePicker": ".monkez_file_picker",
    "MonkezUSBCamera": ".monkez_usb_camera",
    "MonkezDial": ".monkez_value_widgets",
    "MonkezDoubleSpinBox": ".monkez_value_widgets",
    "MonkezSpinBox": ".monkez_value_widgets",
}

__all__ = list(_WIDGET_MODULES)


def __getattr__(name: str):
    module_name = _WIDGET_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    widget_type = getattr(import_module(module_name, __name__), name)
    install_fluent_api((widget_type,))
    globals()[name] = widget_type
    return widget_type


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))


apply_designer_branding()
