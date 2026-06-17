from .app_branding import apply_designer_branding
from .fluent_api import install_fluent_api
from .monkez_button import MonkezButton
from .monkez_checkbox import MonkezCheckBox
from .monkez_combobox import MonkezComboBox
from .monkez_containers import MonkezFrame, MonkezGroupBox, MonkezScrollArea
from .monkez_datetime_widgets import MonkezCalendarWidget, MonkezDateEdit, MonkezDateTimeEdit, MonkezTimeEdit
from .monkez_display_widgets import MonkezLCDNumber
from .monkez_gauges import MonkezArcGauge, MonkezLinearGauge, MonkezRadialGauge
from .monkez_image import MonkezImage
from .monkez_progress_bar import MonkezProgressBar
from .monkez_radio_button import MonkezRadioButton
from .monkez_slider import MonkezSlider
from .monkez_switch import MonkezSwitch
from .monkez_text_input import MonkezTextInput
from .monkez_usb_camera import MonkezUSBCamera
from .monkez_value_widgets import MonkezDial, MonkezDoubleSpinBox, MonkezSpinBox

__all__ = [
    "MonkezButton",
    "MonkezArcGauge",
    "MonkezCheckBox",
    "MonkezCalendarWidget",
    "MonkezComboBox",
    "MonkezDateEdit",
    "MonkezDateTimeEdit",
    "MonkezDial",
    "MonkezDoubleSpinBox",
    "MonkezFrame",
    "MonkezGroupBox",
    "MonkezImage",
    "MonkezLCDNumber",
    "MonkezLinearGauge",
    "MonkezProgressBar",
    "MonkezRadioButton",
    "MonkezRadialGauge",
    "MonkezScrollArea",
    "MonkezSlider",
    "MonkezSpinBox",
    "MonkezSwitch",
    "MonkezTextInput",
    "MonkezTimeEdit",
    "MonkezUSBCamera",
]

install_fluent_api(globals()[name] for name in __all__)
apply_designer_branding()
