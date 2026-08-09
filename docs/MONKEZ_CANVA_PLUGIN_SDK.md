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

Project package là lựa chọn có UI nhưng vẫn giữ nguyên ranh giới này: discovery
chỉ đọc manifest và SHA-256, không import Python. Người dùng/host phải bấm rõ
**Trust and load** cho đúng fingerprint trong phiên hiện tại. Trust không lưu vào
project, vì vậy copy repository sang máy khác không thể tự chạy code.

## Đóng gói plugin portable

Đặt mỗi package trong `.monkez_canva/plugins/<package>/`:

```text
.monkez_canva/plugins/packaged-notes/
├── plugin.json
└── plugin.py
```

Manifest tối thiểu:

```json
{
  "format": "monkez-canva-plugin",
  "version": 1,
  "pluginId": "com.example.packaged-notes",
  "label": "Packaged Notes",
  "pluginVersion": "1.0.0",
  "minimumSdk": 1,
  "entryPoint": {"file": "plugin.py", "symbol": "PLUGIN"},
  "componentTypes": ["packaged_note"]
}
```

`plugin.py` xuất một `ComponentPlugin` tại symbol đã khai báo. Package path phải
relative, entry phải là `.py`, không chấp nhận symlink; manifest, số file và tổng
dung lượng đều có giới hạn. Fingerprint bao phủ tên và nội dung mọi source/asset
trong package; cache `__pycache__` sinh sau khi load không tham gia fingerprint.

```python
packages = canvas.discoverProjectPlugins()  # read-only, không thực thi code
fingerprint = canvas.trustProjectPlugin("com.example.packaged-notes")
canvas.loadProjectPlugin("com.example.packaged-notes")
canvas.unloadProjectPlugin("com.example.packaged-notes")
canvas.revokeProjectPluginTrust("com.example.packaged-notes")
canvas.showProjectPluginManager()
```

Có thể truyền `trust_fingerprint=...` vào `loadProjectPlugin()` để gộp một quyết
định trust chính xác với thao tác load. Nếu package đổi dù chỉ một byte, trust cũ
không còn hợp lệ và stale candidate bị từ chối trước khi entry point chạy.

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

[`examples/canva_plugin_package`](../examples/canva_plugin_package) là package
portable hoàn chỉnh gồm `plugin.json` và entry point. Copy nguyên thư mục này vào
`.monkez_canva/plugins/` để thử luồng discovery → Trust and load → unload/revoke.
