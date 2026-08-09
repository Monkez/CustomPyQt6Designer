# MonkezCanva Component Plugin SDK

Component SDK cho phép ứng dụng bổ sung element riêng gồm metadata palette,
schema/migration, typed ports, renderer vector và Inspector auto-apply mà không
sửa mã nguồn MonkezCanva.

## Nguyên tắc an toàn

Ứng dụng host phải chủ động import module Python đã tin cậy và truyền manifest
vào canvas. File document chỉ lưu `type` và JSON data; document không chứa tên
module cần chạy và MonkezCanva không tự import code từ project.

```python
from my_company.monkez_plugin import PLUGIN

canvas.registerElementPlugin(PLUGIN)
```

Khi plugin chưa được cài, record vẫn được giữ nguyên và hiển thị thành Missing
component. Khi đăng ký plugin sau đó, renderer và Inspector được khôi phục tại
chỗ, giữ nguyên element ID, selection và document data.

## Tạo manifest

```python
from monkez_pyqt6.monkez_canva import ElementDefinition, component_plugin

PLUGIN_ID = "com.example.telemetry"

PLUGIN = component_plugin(
    PLUGIN_ID,
    "Telemetry",
    "1.0.0",
    (
        ElementDefinition(
            "temperature_sensor",
            "Temperature sensor",
            "Telemetry",
            190,
            110,
            defaults={"value": 0.0, "unit": "°C"},
            schema={
                "properties": {
                    "value": {"type": "number"},
                    "unit": {"type": "string"},
                }
            },
            plugin_id=PLUGIN_ID,
            plugin_version="1.0.0",
            capabilities={"content", "geometry", "appearance", "ports"},
            renderer_factory=paint_sensor,
            inspector_factory=create_sensor_inspector,
        ),
    ),
    description="Telemetry components for the plant dashboard",
)
```

Mọi definition trong manifest phải có cùng `plugin_id`. Type ID không được trùng
trong manifest. `minimum_sdk` lớn hơn `COMPONENT_SDK_VERSION` hiện tại bị từ chối
ngay khi tạo manifest.

## Callback contract

Renderer có chữ ký:

```python
def paint_sensor(painter, item, rect, option, widget) -> None:
    ...
```

Renderer chỉ vẽ và đọc `item.custom_properties`; không nên sửa document trong
paint event. Nếu callback phát sinh exception, canvas hiển thị Renderer error và
phát diagnostic thay vì làm crash ứng dụng.

Inspector factory có chữ ký:

```python
def create_sensor_inspector(canvas, item) -> QWidget | None:
    ...
```

Control tùy chỉnh gọi `canvas.updateElement(item.element_id, ...)` khi người dùng
thay đổi giá trị. Thay đổi sẽ tự động tham gia validation, Undo/Redo, autosave và
đồng bộ nhiều view. Factory trả về `None` nếu không cần UI riêng.

## Cài đặt, nâng cấp và gỡ

```python
types = canvas.registerElementPlugin(PLUGIN)
canvas.unregisterElementPlugin(PLUGIN.plugin_id)
```

Đăng ký là nguyên tử ở registry: toàn bộ ownership, SDK version và xung đột type
được kiểm tra trước khi thay đổi registry thật. Placeholder và definition do cùng
plugin sở hữu có thể được thay thế; type thuộc plugin khác chỉ được thay khi host
truyền rõ `replace_existing=True`.

Đối với tooling headless:

```python
from monkez_pyqt6.monkez_canva import (
    ElementRegistry,
    install_component_plugin,
    uninstall_component_plugin,
)

registry = ElementRegistry()
install_component_plugin(registry, PLUGIN)
uninstall_component_plugin(registry, PLUGIN)
```

Gỡ plugin chỉ tháo metadata/factory; không xóa element khỏi document.
`componentPluginChanged(plugin_id, enabled)` và `diagnosticMessage` cho phép host
cập nhật plugin manager hoặc log.

## Ví dụ hoàn chỉnh

[canva_component_plugin.py](../examples/canva_component_plugin.py) chứa một
Telemetry sensor hoàn chỉnh với vector renderer, typed output port, schema và
Inspector auto-apply. `canva_demo.bat` tự đăng ký plugin này và hiển thị category
**SDK examples** trong Add pane.
