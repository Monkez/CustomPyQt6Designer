# Monkez PyQt6 0.6.0

## MonkezCanva runtime and Designer integration

- Added dependency-free MQTT, WebSocket, OPC-UA and Modbus adapter boundaries.
- Added optional `adapters` extra for real protocol drivers.
- Added binding write-back with safe declarative transforms.
- Added historian retention and aggregate queries per adapter channel.
- Added stable `monkez_canva.runtime` and `monkez_canva.editor` import boundaries.
- Updated the Qt Designer MonkezCanva plugin preview and package metadata.
- Control Pane pages are opaque, compact and collapsed by default.

The core package remains usable without installing any protocol driver. Install
`monkez-pyqt6[adapters]` only when a project needs external protocol clients.
