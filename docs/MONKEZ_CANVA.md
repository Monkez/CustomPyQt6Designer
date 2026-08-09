# MonkezCanva

## Project scaffolding

Create a portable PyQt6 project with the bundled application skeleton:

```bat
monkez_pyqt6 init -n telemetry_dashboard -python 3.11
```

The command creates `main.py`, `assets/qt-uis`, `images`, `icons`, `logs`,
`configs`, `modules`, `config.json`, and `setup.bat`/`run.bat`/`build.bat`.
The first run creates `.venv` and installs the package automatically. Use
`--no-setup` when generating files in CI or when the environment is prepared
separately.

## Release 0.6.0

The Designer plugin is included in the package and exposes `MonkezCanva` in the
Canvas & Diagram group. Runtime integrations can import adapters and bindings
from `monkez_pyqt6.monkez_canva.runtime`; protocol drivers are optional extras.

### Control Pane tab isolation

The Control Pane uses an explicit tab-bar plus stacked-page composite instead
of native `QTabWidget`. Every page owns an opaque styled surface and the stack
clears its background before each page switch, preventing stale Add/Inspector
pixels on Windows and fractional-DPI displays.

`MonkezCanva` là canvas editor nhúng trực tiếp trong ứng dụng PyQt6. Widget dùng
được ở runtime, có plugin Qt Designer và không phụ thuộc WebEngine.

## Chạy demo

Chạy `canva_demo.bat`. Có thể nhấn `Ctrl+D`, thả `Ctrl` rồi nhấn `E`, hoặc giữ
`Ctrl` và lần lượt nhấn `D`, `E`. Cửa sổ `MonkezCanva` sẽ xuất hiện.
Lặp lại phím tắt để đóng edit mode.

Cửa sổ CMD hiển thị log trực tiếp và đồng thời ghi vào `canva_demo.log` tại thư
mục dự án. Khi shortcut hoạt động, log phải có `Editor shortcut received`, tiếp
theo vị trí toolbox và `toolbox=visible`.

Trong edit mode:

- thêm text, rectangle, ellipse, button, bar chart, line chart và flow node;
- chọn, kéo, kéo góc phải dưới để đổi kích thước và nhấn `Delete` để xóa;
- bật snap-to-grid để căn element;
- giữ `Ctrl` và lăn chuột để zoom;
- bấm `Fit view` để đưa toàn bộ nội dung về tỷ lệ dễ đọc;
- đổi màu element đang chọn từ cửa sổ nổi.

Editor có năm tab:

- **Add**: thêm shape, chart, node, ảnh và GIF; duplicate/xóa item.
- **Inspector**: sửa ID, text, source, vị trí, kích thước, rotation, opacity,
  z-order và các vai trò màu; thay đổi tự áp dụng, không cần nút Apply.
- **Layers**: quản lý toàn bộ item theo ID ổn định và chọn nhanh trên canvas.
- **View**: zoom in/out, 100%, fit, di chuyển viewport bốn hướng, center selection
  và chuyển đổi pan/select mode.
- **Save**: checkpoint trong phiên, lưu/đọc bền, undo và redo.

Khi bật Edit Mode, thanh quick actions nổi chồng ở mép trên Canvas, không tham gia
layout nên không đẩy canvas xuống hoặc làm thay đổi tâm nhìn. Toolbar là child trực
tiếp của Canvas thay vì viewport cuộn, nên giữ nguyên vị trí khi pan scene. Floatbar cung cấp
Save, zoom out, 100%, zoom in, Fit và các lệnh căn Left, Right, Top, Bottom, tâm
ngang, tâm dọc hoặc đúng tâm hai chiều. Các nút căn chỉ bật khi có từ hai item được
chọn.

Control pane là cửa sổ tool không viền, kích thước gọn, có shadow, header kéo được,
tab tự co đều và nút đóng Edit Mode riêng. Giao diện dùng nền trắng ấm, accent coral,
card bo tròn, field hai cột và trạng thái lưu màu teal theo concept `Floating Cards`.
Header hiển thị badge số object đang chọn; khi multi-select, card `Quick arrange`
hiện tám action căn trái/tâm/phải/trên/giữa/dưới và phân bố ngang/dọc. Footer `Saved`
cố định nên không bị cuộn cùng Inspector. Badge chữ `EDIT` đã được bỏ; mọi action
trong pane và floatbar dùng icon vector DPI-safe kèm tooltip.

Card trong Control Pane được vẽ đồng nhất bởi editor thay vì phụ thuộc vào native
`QGroupBox`, vì vậy title luôn nằm gọn bên trong card và không cắt đường viền trên
Windows/High-DPI. Spinbox dùng stepper chìm, không còn các đường kẻ dày quanh mũi
tên; thanh tab dùng icon 16 px, hover rất nhẹ và selected state không còn
đóng khung như một button. Tab active chỉ đổi icon/chữ sang coral và hiện
một vạch ngắn 2 px căn giữa, giúp thanh tab thoáng và không nhảy bố cục.

Mỗi card trong Inspector, View và Save là một accordion độc lập. Bấm toàn bộ hàng
tiêu đề hoặc dùng `Space`/`Enter` khi header có focus để thu gọn/mở rộng; chevron
đổi giữa hướng phải và hướng xuống. Các nhóm chuyên sâu như Node ports, Data
bindings, Workflow runtime, routing/effect, auto-layout, snapping và history mặc
định thu gọn để ưu tiên thuộc tính thường dùng. Trạng thái được giữ trong suốt
phiên editor; action ngữ cảnh như **Open data bindings** tự mở đúng tab và bung
đúng card. Việc đóng/mở chỉ thay đổi bố cục, không ghi document và không kích hoạt
Inspector auto-apply.

Trên Windows, Control Pane dùng cửa sổ trong suốt để giữ shadow mềm. Mỗi tab
và viewport cuộn vì vậy có một paint surface nền riêng; khi chuyển tab, editor
ẩn tất cả page không active, raise page active và yêu cầu vẽ lại. Cơ chế này
ngăn nội dung Inspector/Layers cũ còn lưu trên tab Add ở mức scale 100–200%.
Script `scripts/render_canva_control_pane_qa.py` luôn chụp cả Inspector và ca
chuyển Inspector → Add để kiểm tra lỗi chồng hình.

## Hiệu năng scene lớn và LOD

Tab **View > Rendering** có ba chế độ:

- **Auto**: giữ full detail khi làm việc gần, chuyển sang silhouette gọn khi
  zoom xa hoặc scene có từ 1.000/10.000 object;
- **Quality**: luôn vẽ label, port, plugin renderer, bridge và visual effect;
- **Speed**: ưu tiên thao tác trên scene rất lớn hoặc GPU yếu.

Auto không làm mất ngữ nghĩa tương tác: object đang chọn vẫn full detail,
packet đang truyền vẫn hiển thị, còn export PNG/SVG/PDF luôn dùng Quality.
Grid tự giãn bước vẽ theo lũy thừa khi zoom xa để không tạo nhiễu,
nhưng `gridSize` dùng cho snap và dữ liệu project không thay đổi.
Policy và metrics không ghi vào document, do đó không làm dirty project.

```python
canvas.setPerformanceMode("auto")  # auto | quality | speed
print(canvas.performanceMode())
print(canvas.performanceStats())
print(canvas.renderProfileForLod(0.2, object_count=10_000))
canvas.resetPerformanceStats()
```

Chạy `benchmark_canva.bat` để tạo `canva_performance.json` và log trực tiếp
cho các scene 100, 1.000, 10.000 node. Baseline Windows/Python 3.11/Qt 6.4.2
ngày 2026-08-09 ghi nhận load lần lượt khoảng 55 ms, 556 ms, 6,6 s;
frame overview 10.000 node vẽ 1.672 item nhìn thấy trong khoảng 33 ms.
Số liệu gốc nằm trong `docs/benchmarks/MONKEZ_CANVA_PERFORMANCE_2026-08-09.json`.

Có thể phân bố đều từ ba element trở lên:

```python
canvas.selectElements(["node-a", "node-b", "node-c"])
canvas.distributeSelected("horizontal")
canvas.distributeSelected("vertical")
```

Có ba cách chọn nhiều item: giữ `Ctrl` khi bấm, kéo rubber-band qua nhiều item,
hoặc chọn nhiều dòng trong tab Layers. Giữ chuột phải trên vùng canvas trống rồi
kéo để di chuyển viewport mà không làm mất selection hiện tại.

`fitContent()` có thể được gọi trước `show()`; canvas sẽ hoãn việc tính tỷ lệ đến
khi viewport có kích thước thật. Zoom tự động được giới hạn trong khoảng dễ thao
tác, tránh graph bị thu thành một chấm nhỏ trên màn hình lớn.

View mode khóa thao tác sửa nhưng vẫn phát signal click. `elementClicked` chỉ dành
cho element, `connectorClicked` chỉ dành cho connector và `objectClicked` nhận cả
hai loại, tránh dùng nhầm ID connector với API chỉ dành cho element. Phím tắt có
context theo window. Có thể tắt bằng `editorShortcutEnabled = False`.

## API cơ bản

```python
from monkez_pyqt6.monkez_widgets import MonkezCanva

canvas = MonkezCanva()
source = canvas.addNode("Camera", 0, 0, color="#0ea5e9")
target = canvas.addNode("Detection", 260, 0, color="#7c3aed")
chart = canvas.addChart([20, 48, 72, 63], "line", 520, -30)
canvas.connectElements(source, target)
canvas.connectElements(target, chart)

canvas.setElementText(target, "Person detector")
canvas.setElementColor(target, "#ef4444")
canvas.setElementColor(target, "#fff7ed", role="background")
canvas.setChartData(chart, [32, 66, 54, 88])
canvas.highlightElement(target, "#f59e0b", duration=1200)
canvas.animateElement(target, "pulse", duration=500)

canvas.renameElement(target, "person-detector")
canvas.updateElement("person-detector", x=280, y=40, rotation=5, opacity=0.9)
```

## Ảnh, GIF và kéo-thả

```python
photo_id = canvas.addMedia("assets/photo.png", 100, 120)
gif_id = canvas.addMedia("assets/loading.gif", 420, 120)
```

Có thể kéo file `.png`, `.jpg`, `.jpeg`, `.bmp`, `.webp` hoặc `.gif` từ Explorer
thả trực tiếp lên canvas. GIF dùng `QMovie`, tiếp tục chuyển frame trong scene và
được dừng/giải phóng khi item bị xóa.

## ID và quản lý item

Mỗi item có ID duy nhất. Có thể truyền `element_id=` khi tạo hoặc đổi sau đó:

```python
node = canvas.addNode("Input", element_id="camera-input")
canvas.selectElement("camera-input")
canvas.renameElement("camera-input", "usb-camera-01")
canvas.duplicateSelected()
canvas.bringSelectedToFront()

canvas.selectElements(["usb-camera-01", "result-node"])
canvas.alignSelected("top")
canvas.alignSelected("hcenter")
canvas.alignSelected("center")

# Clipboard giữ lại connector nằm hoàn toàn trong selection.
payload = canvas.copySelection()     # đồng thời ghi MIME riêng vào clipboard
new_ids = canvas.pasteSelection()    # Ctrl+V, tự remap ID và dịch 30 px
canvas.cutSelection()                # Ctrl+X, undo được trong một bước
canvas.duplicateSelection()          # không làm thay đổi clipboard hệ thống

# Di chuyển chính xác; các lần gọi liên tiếp được merge thành một undo step.
canvas.nudgeSelected(1, 0)
```

Không thể dùng ID rỗng hoặc trùng. Connector giữ tham chiếu đúng khi ID endpoint
được đổi. Signal `itemIdChanged(old_id, new_id)` cho phép business logic cập nhật
mapping riêng.

Trong edit mode, phím mũi tên dịch selection `1 px`, `Shift+mũi tên` dịch
`10 px`, còn `Alt+mũi tên` dịch `0,1 px`. `Ctrl+C/X/V` dùng MIME
`application/x-monkez-canva-selection+json`; dữ liệu clipboard có version,
giới hạn kích thước/số object, không chứa code thực thi và chỉ paste element type
đã đăng ký. Chọn nhiều object trong Inspector hiển thị `Mixed` cho giá trị khác
nhau; việc chỉ mở Inspector không ghi đè dữ liệu, và chỉ field vừa sửa mới được
áp dụng đồng loạt bằng một undo command.

## Search palette và command palette

Tab **Add** tìm theo label, type ID, category, capability và plugin owner. Bộ lọc
gồm All, Favorites, Recent và mọi category do registry cung cấp. Bấm biểu tượng
ngôi sao để favorite; danh sách favorites/recent nằm trong `scene` của document
nên tự đi cùng project khi chuyển máy. Thêm component cập nhật Recent trong cùng
command với element, vì vậy Undo không sinh thêm bước phụ.

Nhấn `Ctrl+K` hoặc nút command trên header Control Pane để mở command palette.
Gõ để lọc component hoặc action theo ngữ cảnh; dùng `↑/↓`, `Enter`, `Esc` để thao
tác hoàn toàn bằng bàn phím. Palette tự bật/tắt lệnh dựa trên selection, clipboard,
read-only state và khả năng Undo/Redo. API tương ứng:

```python
canvas.setPaletteFavorite("node", True)
canvas.paletteFavorites()
canvas.paletteRecent()
canvas.addPaletteElement("line_chart")
canvas.showCommandPalette("align left")
canvas.zoomToSelection()
canvas.selectAllElements()
```

## Menu ngữ cảnh, căn chỉnh và smart guides

Click chuột phải trên vùng canvas trống để mở menu Add/Paste/View; giữ và kéo
chuột phải vẫn pan viewport như trước. Click chuột phải trên item hoặc connector
để Copy/Cut/Duplicate/Delete, đổi layer và zoom tới selection. Khi chọn từ hai
element, submenu **Align** và **Match size** cho phép căn hoặc đồng bộ width,
height hay cả hai; mỗi thao tác là một bước Undo duy nhất.

Tab **View** có nhóm **Snapping & guides** để bật riêng Grid, Edges, Centers và
Ports, đặt khoảng bắt dính 1-40 px và ẩn/hiện smart guides. Các tùy chọn này lưu
trong scene của document nên tiếp tục hoạt động khi copy cả project sang máy khác.

```python
canvas.setSnapTargets(("grid", "edges", "centers", "ports"))
canvas.setSnapDistance(8)
canvas.setSmartGuidesVisible(True)
canvas.matchSelectedSize("both")  # width | height | both
```

## Auto layout

Tab **View > Auto layout** có thể sắp xếp toàn document, selection hiện tại,
một connected component hoặc nội dung của group được chọn. **Smart scope** tự
chọn phạm vi phù hợp từ selection. Bốn chiến lược tương tự có thể tìm bằng
`Ctrl+K` và gọi từ menu chuột phải:

- `layered`: phân tầng theo hướng, xử lý cycle và giảm giao cắt;
- `tree`: cây cha/con với khoảng trống theo kích thước subtree;
- `radial`: các vòng tròn dựa trên graph distance;
- `force`: mô phỏng network deterministic kèm collision avoidance.

Node bị lock giữ nguyên tọa độ và trở thành anchor. Các component rời nhau được
đóng gói theo khoảng cách cấu hình. Một lần layout, kể cả fit lại group frame,
chỉ tạo đúng một bước Undo/Redo. `computeAutoLayout()` dùng để preview và không
thay đổi canvas.

```python
preview = canvas.computeAutoLayout(
    "layered", direction="right", scope="component"
)

result = canvas.autoLayout(
    "layered",
    direction="right",       # right | down | left | up
    scope="selection",       # auto | document | selection | component | group
    node_spacing=48,
    layer_spacing=120,
    component_spacing=160,
    preserve_center=True,
    respect_locked=True,
    fit_groups=True,
    fit_view=False,
)

canvas.autoLayoutSelection("tree")
canvas.autoLayoutGroup("pipeline", "layered")
canvas.layoutApplied.connect(lambda metrics: print(metrics))
```

## Document Outline, lock/hide/isolate và minimap

Tab **Layers** hiện là Document Outline: tìm theo ID, loại hoặc nhãn; mỗi dòng
hiển thị rõ trạng thái visible, locked hay hidden. Toolbar bên dưới cho phép
lock/unlock, hide/show, isolate, show all và zoom tới selection. Lock và hidden
là thuộc tính document, hỗ trợ Undo/Redo và được lưu theo project. Isolation chỉ
là bộ lọc viewport tạm thời nên không làm thay đổi trạng thái hidden đã lưu.

Minimap nổi ở góc phải dưới canvas, không chiếm layout và không di chuyển theo
viewport. Click hoặc kéo trên minimap để điều hướng. Tab **View > Navigator** cho
phép ẩn/hiện minimap và lưu tối đa 32 viewport bookmark cùng tâm và mức zoom.

```python
canvas.setObjectLocked("pump", True)
canvas.setObjectsHidden(("debug-label", "debug-edge"), True)
canvas.isolateSelection()
canvas.clearIsolation()
bookmark_id = canvas.addViewportBookmark("Main process")
canvas.goToViewportBookmark(bookmark_id)
```

Signal chính gồm `elementAdded(str)`, `elementRemoved(str)`, `connectorAdded(str)`,
`connectorRemoved(str)`, `elementClicked(str)`, `connectorClicked(str)`,
`objectClicked(str)`, `selectionChanged(str)`, `editModeChanged(bool)` và
`documentChanged()`. Signal `selectionSetChanged(list)` cung cấp toàn bộ ID đang
được chọn; `selectedElementIds()` trả về cùng tập ID theo thứ tự document.

## Connector, line và mô phỏng dòng tín hiệu

Connector là một object độc lập có ID, selection, layer Z, opacity, metadata và
vòng đời signal riêng. Có hai cách tạo: kéo chuột trực tiếp từ marker port của node
sang marker port khác, hoặc chọn đúng hai element rồi bấm **Connect 2 selected
items**. Sau đó chọn chính đường nối để Inspector hiện các thuộc tính chuyên biệt.
Có thể đổi source/target và source/target port mà vẫn giữ nguyên ID connector.

Khi chọn connector trong edit mode, mọi waypoint được hiển thị thành handle tròn
có thể kéo trực tiếp; double-click handle để xóa, hoặc double-click trên đường để
thêm điểm reroute. Orthogonal route hỗ trợ `cornerRadius`; nhiều connector giữa
cùng hai node tự tách lane theo `parallelSpacing`. Self-loop, edge label và vị trí
label theo phần trăm đường đi đều là dữ liệu lưu trong document. Packet và các
hiệu ứng line luôn chạy theo path đã reroute.

```python
edge = canvas.connectElements(
    "pump", "tank", connector_id="water-main",
    sourcePort="water-out", targetPort="water-in",
    route="orthogonal",       # bezier | orthogonal | straight | polyline
    lineStyle="dashdot",      # solid | dash | dot | dashdot
    lineWidth=4,
    arrowStart=False,
    arrowEnd=True,
    cornerRadius=18,
    label="Water flow",
    labelPosition=0.55,
    parallelSpacing=24,
    animated=True,
    flowColor="#06b6d4",
    flowSpeed=1.8,
    metadata={"signal": "water"},
)

canvas.addConnectorWaypoint(edge, (320, 140))
canvas.moveConnectorWaypoint(edge, 0, (360, 160))
canvas.removeConnectorWaypoint(edge, 0)
canvas.clearConnectorWaypoints(edge)
canvas.setConnectorLabel(edge, "Pressure signal", 0.65)
canvas.updateConnector(edge, route="bezier", arrowStart=True)
canvas.animateConnector(edge, True, speed=2.5, color="#38bdf8")
canvas.reconnectConnector(edge, "pump-backup", "tank", "out", "water-in")

line = canvas.addLine(40, 300, element_id="separator", arrowEnd=True)
multi_segment_line = canvas.addLine(
    320, 260, element_id="manual-pipe",
    points=[[0, 80], [100, 10], [220, 90]],
    lineWidth=5, arrowStart=False, arrowEnd=True,
)
```

Animation dùng một lớp dash chuyển động phủ trên stroke chính, phù hợp minh họa
dòng điện, nước hoặc luồng dữ liệu. `canvasObject(id)` truy cập thống nhất element
hoặc connector; `connector(id)`, `connectors()` và `selectedObjectIds()` dành cho
logic cần phân biệt rõ hai loại. Toàn bộ route, waypoint, style, hai đầu mũi tên,
animation, endpoint port và metadata đều được serialize/autosave.

Arrow không còn là element riêng: bật `arrowStart` hoặc `arrowEnd` trên Line.
Polyline cũng chính là Line có từ ba `points` trở lên. `addPolyline()` và document
cũ có type `arrow`/`polyline` vẫn được đọc như alias tương thích, nhưng dữ liệu mới
luôn được chuẩn hóa thành một loại `line`.

### Hiệu ứng line và truyền packet

Line độc lập và connector dùng chung các hiệu ứng `flow`, `pulse`, `glow`,
`particles` và `packet`. Inspector cho phép đổi tức thì màu, tốc độ, chiều chạy,
khoảng cách và cường độ. Với `packet`, có thể bật Loop, đặt thời gian đi hết một
đoạn, chu kỳ phát gói và ảnh icon; nếu không chọn ảnh, editor vẽ icon phong bì.

```python
canvas.updateConnector(
    "network-edge", animated=True, animationEffect="packet",
    packetLoop=True, packetDuration=1.4, packetInterval=0.25,
    packetIcon="assets/message.png",
)
message_id = canvas.send_a_message(
    "network-edge", icon="assets/alert.png", speed=1.5,
    travel_time=1.2, wait_to_end=True,
    payload={"alarm": "overheat", "temperature": 96.2},
    metadata={"topic": "plant/alarm"},
    priority=10, ttl=16, timeout=5, branch_policy="all",
)
```

Nhiều lần gọi tạo được nhiều gói đang bay đồng thời. `messageSent(line_id,
message_id)` phát ở mỗi đoạn packet bắt đầu đi qua; `messageArrived(line_id,
message_id)` phát một lần khi packet tới toàn bộ đích cuối. `sendMessage()` là
alias kiểu Qt của `send_a_message()`.

### MessageTicket và Runtime Debugger

`sendMessageTicket()` là API non-blocking chính của packet runtime v2. Nó trả về
`MessageTicket` sống với state `queued`, `in_flight`, `paused`, `completed`,
`cancelled`, `failed` hoặc `timed_out`. Payload, metadata, priority, TTL theo số
hop, timeout, branch policy, route đã đi và lỗi đều là transient runtime state;
chúng không làm document dirty và không được ghi vào JSON dự án.

```python
ticket = canvas.sendMessageTicket(
    "network-edge",
    message_id="alarm-1042",
    payload={"value": 96.2},
    metadata={"topic": "plant/alarm", "correlationId": "job-77"},
    priority=10,
    ttl=16,
    timeout=5.0,
    branch_policy="first",  # all | first | round_robin
)

canvas.setRuntimeBreakpoint("network-edge", True)
canvas.pauseRuntime()
canvas.stepRuntime()         # xử lý đúng một packet arrival đang chờ
canvas.resumeRuntime()
canvas.cancelMessage(ticket.message_id)

state = canvas.messageTicket(ticket.message_id).snapshot()
trace = canvas.runtimeTrace(ticket.message_id)
canvas.showRuntimeDebugger()

# Dùng với qasync hoặc host đã tích hợp Qt/asyncio:
finished = await canvas.sendMessageAsync("network-edge", payload={"value": 42})
```

Mở debugger bằng `Ctrl+K` và tìm **Runtime debugger**, hoặc từ menu chuột phải
connector. Cửa sổ tách rời có danh sách ticket theo priority, trạng thái, hop và
elapsed time; tab Timeline hiển thị trace có sequence; phần detail hiển thị route,
payload, metadata và lỗi. Toolbar hỗ trợ Pause/Resume, Step, breakpoint trên object
đang chọn, Cancel và dọn ticket đã hoàn tất. Signal `messageTicketChanged(str,
dict)`, `runtimeTraceEvent(dict)`, `runtimePausedChanged(bool)` và
`runtimeBreakpointsChanged(list)` dùng để xây debugger riêng trong ứng dụng host.

#### Replay fixture và link metrics

Ticket đã kết thúc có thể được đóng gói thành fixture JSON portable. Fixture chứa
input, options, expected terminal state, route và sequence sự kiện theo offset tương
đối; không chứa graphics object, timer hoặc timestamp tuyệt đối. Khi replay trên
graph hiện tại, comparator phát hiện route/status/event divergence. File được giới
hạn 1 MiB và 10.000 event, validate trước khi chạy và lưu atomically.

```python
fixture = canvas.captureMessageReplay("alarm-1042", fixture_id="alarm-regression")
canvas.saveMessageReplay("alarm-1042", "tests/alarm.packet-replay.json")

loaded = canvas.loadMessageReplay("tests/alarm.packet-replay.json")
replayed = canvas.replayMessage(
    loaded,
    message_id="alarm-regression-run-2",
    travel_time=0.1,  # tùy chọn để test/QA nhanh hơn
)

canvas.runtimeReplayCompleted.connect(
    lambda message_id, result: print(message_id, result["matched"], result["mismatches"])
)
```

`runtimeLinkMetrics()` ghép từng `segment_started` với `segment_arrived` và trả về
started/arrived/in-flight, failure/timeout/cancel, delivery rate, throughput theo
cửa sổ thời gian cùng latency average/min/max/p50/p95. Sample được giới hạn bộ nhớ;
metric là runtime state nên không làm dirty project. Tab **Links** của Runtime
Debugger cho phép đổi cửa sổ 10 giây, 60 giây, 5 phút hoặc 15 phút, xem chi tiết và
reset riêng link đang chọn hoặc toàn bộ.

```python
for metric in canvas.runtimeLinkMetrics(window=60):
    print(metric["objectId"], metric["throughputPerSecond"], metric["latencyMs"]["p95"])

canvas.resetRuntimeLinkMetrics("network-edge")
```

### Splitter

Splitter là junction có một input và 2–12 output, có ID và port như node. Packet
tới input được chuyển theo `branch_policy`: `all` nhân sang mọi output, `first`
chọn nhánh ổn định đầu tiên, còn `round_robin` luân phiên một nhánh. Hiệu ứng không
bị ngắt khi graph phân nhánh. `wait_to_end=True` chỉ trả về sau khi tất cả nhánh
được chọn hoàn tất.

```python
splitter = canvas.addSplitter(300, 120, output_count=3, element_id="fan-out")
canvas.connectPorts("source", "out", splitter, "in")
canvas.connectPorts(splitter, "out-1", "monitor-a", "in")
canvas.connectPorts(splitter, "out-2", "monitor-b", "in")
canvas.connectPorts(splitter, "out-3", "archive", "in")
```

## Workflow component pack và executor

Workflow Pack là bộ 29 component opt-in, vì vậy palette mặc định vẫn gọn. Gọi
`enableWorkflowComponents()` để thêm bốn nhóm Boundaries, Routing, Timing và Logic.
Mỗi component dùng typed ports, ID ổn định và cấu hình JSON portable trong field
`workflow`; document không lưu callable hay tên module Python.

```python
canvas.enableWorkflowComponents()

source = canvas.addWorkflowComponent("source", 0, 0, element_id="source")
transform = canvas.addWorkflowComponent("transform", 260, 0, element_id="scale")
sink = canvas.addWorkflowComponent("sink", 520, 0, element_id="sink")

canvas.connectPorts(source, "out", transform, "in")
canvas.connectPorts(transform, "out", sink, "in")
canvas.setWorkflowConfig(transform, operation="scale", value=1.5)

result = canvas.runWorkflow(
    source,
    42,
    metadata={"topic": "telemetry"},
    visualize=True,
)
print(result["outputs"][sink])  # [63.0]
```

Các component hiện có:

- Boundaries: Source, Sink, Input/Output interface và Error handler;
- Routing: Junction, Reroute, Merge, Splitter, Switch, Router, Multiplexer,
  Demultiplexer và Bus;
- Timing: Timer, Delay, Queue, Buffer, Throttle, Debounce, Retry và Rate limiter;
- Logic: Gate, Compare, Filter, Transform, Map, Counter và State machine.

Executor thuần Python dùng logical time và hàng đợi deterministic, nên Delay,
Throttle, Debounce và Retry chạy/test được mà không phụ thuộc timer Qt. Cùng document
có thể chạy headless bằng `WorkflowGraph`/`WorkflowExecutor`, hoặc chạy qua canvas để
node hiện badge trạng thái và connector minh họa token bằng packet animation. Runtime
state, trace, payload và output đều transient, không làm document dirty.

Inspector của workflow node có card **Workflow runtime** riêng. JSON thay đổi được
auto-apply và Undo/Redo như property khác; các nút Run here, Step và Debugger cho phép
thử graph ngay tại chỗ. Runtime Debugger có tab Workflow hiển thị timeline theo thứ
tự sequence. Các signal `workflowTraceEvent(dict)`,
`workflowNodeStateChanged(str, str)` và `workflowFinished(dict)` cho phép ứng dụng host
xây status panel riêng.

```python
executor = canvas.createWorkflowExecutor(handlers={"custom-node": my_handler})
token = executor.start("source", {"value": 10})
canvas.stepWorkflow()
canvas.runActiveWorkflow()
canvas.pauseWorkflow()
canvas.resumeWorkflow()
canvas.cancelWorkflow()
```

Custom handler trả payload thường, hoặc `WorkflowNodeResult` khi cần phát ra nhiều
port, delay hay failure edge rõ ràng. Cấu hình Queue/Buffer và Timer ở milestone này
là nền tảng deterministic; backpressure nhiều producer và recurring wall-clock timer
sẽ được bổ sung trong runtime nâng cao.

Queue runtime cÃ³ giá»›i háº¡n toÃ n executor (`max_queue_size`) vÃ  Queue node cÃ³
`capacity`; overflow dÃ¹ng `reject_new`, `drop_newest` hoáº·c `drop_oldest`. Tráº¡ng thÃ¡i
Ã¡p lá»±c Ä‘Æ°á»£c Ä‘á»c qua `workflowQueueStats()` vÃ  khÃ´ng ghi vÃ o document.

Timer cÃ³ schedule logical deterministic, khÃ´ng tá»± cháº¡y vÃ²ng vÃ´ háº¡n trong
`run_until_idle()`. DÃ¹ng `advanceWorkflow(seconds)` cho test/replay, hoáº·c
`startWorkflowClock()` khi muá»‘n drive báº±ng wall-clock Qt:

```python
schedule_id = canvas.scheduleWorkflow(
    timer, {"topic": "heartbeat"}, interval=1.0,
    initial_delay=0.0, max_occurrences=None,
    catch_up="latest", start_clock=True,
)
canvas.pauseWorkflowSchedule(schedule_id)
canvas.resumeWorkflowSchedule(schedule_id)
canvas.cancelWorkflowSchedule(schedule_id)
```

Runtime Debugger hiá»ƒn thá»‹ queue/capacity/utilization, dropped count, schedule
states vÃ  cÃ³ nÃºt Clock/+1 s. Failure edge dÃ¹ng envelope portable trÃªn source port
`error` hoáº·c `failure`, cÃ³ trace vÃ  packet visualization riÃªng.

## Declarative data binding

Binding definition nằm trong element JSON và đi theo dự án; subscription cùng giá
trị live chỉ tồn tại ở runtime. Vì vậy telemetry có thể đổi text, chart, màu, geometry,
port value, highlight hoặc animation mà không làm document dirty và không ghi giá trị
cuối cùng vào autosave.

```python
binding_id = canvas.addDataBinding(
    "temperature-label",
    "text",
    "plant.sensor.temperature",
    binding_id="temperature-text",
    transforms=[
        {"op": "get", "path": "measurement.value"},
        {"op": "round", "digits": 1},
    ],
    format="{value} °C",
    debounce=0.1,
    throttle=0.25,
    stale_after=5.0,
    fallback="No signal",
    error_fallback="Invalid value",
)

canvas.feedDataSource(
    "plant.sensor.temperature",
    {"measurement": {"value": 24.76}},
)
```

Target hỗ trợ: `text`, `data`, `color`, `background`, `textColor`, `flowColor`,
`opacity`, `rotation`, `scale`, `x`, `y`, `width`, `height`, `highlight`,
`animation`, `port.<port-id>` và `property.<schema-name>`. Target `property.*`
được kiểm tra bằng schema của component, phù hợp để cập nhật live gauge, tank,
sensor, KPI hoặc thuộc tính mở rộng khác. Một element chỉ có tối đa một binding
trên mỗi target để kết quả không phụ thuộc thứ tự ngầm.

Transform pipeline không chạy `eval` hoặc Python expression. Các operation an toàn
gồm `get`, `scale`, `offset`, `clamp`, `round`, `map`, `coalesce`, `bool`, `not`,
`string`, `length` và `json`. `format` dùng placeholder `{value}` và field từ mapping.
Kernel dùng logical time nên debounce, throttle, stale và fallback kiểm thử được mà
không phụ thuộc event loop Qt; widget chỉ dùng một timer chung để flush pending update,
poll callable và phát hiện stale.

Nguồn runtime tích hợp sẵn:

```python
canvas.bindSignal("ui.speed", slider.valueChanged)
canvas.bindQObjectProperty("machine.running", machine, "running")
canvas.bindCallable("clock.value", read_clock, interval=0.25)
canvas.bindModelIndex("table.status", model, row=2, column=1)
canvas.bindDataAdapter(
    "mqtt.temperature", mqtt_adapter,
    signal="valueChanged", getter="value",
)

canvas.feedDataSources({
    "ui.speed": 75,
    "machine.running": True,
})  # batch nhiều source, repaint mỗi target đúng một lần
```

Với protocol adapter chuyên nghiệp, khai báo manifest và lifecycle nhỏ gọn thay
vì buộc thư viện protocol vào widget. Xem adapter chạy được tại
`examples/canva_data_adapter.py`.

```python
adapter = SimulatedTelemetryAdapter()
canvas.registerDataAdapter(adapter)  # tự start
canvas.bindAdapterSource(
    "plant.temperature", "demo-telemetry", "temperature"
)

adapter.publish("temperature", 24.8, metadata={"quality": "good"})
canvas.writeDataAdapter("demo-telemetry", "setpoint", 26)
current = canvas.readDataAdapter("demo-telemetry", "setpoint")

health = canvas.dataAdapterHealth("demo-telemetry")
samples = canvas.dataAdapterHistory("demo-telemetry", "temperature", limit=100)
trace = canvas.dataAdapterTrace(limit=200)
canvas.unregisterDataAdapter("demo-telemetry")
```

`DataAdapterManifest` khai báo `read`, `subscribe`, `write`, `history`; registry từ
chối write-back nếu adapter không khai báo `write`. History là ring buffer runtime,
không ghi telemetry hay credential vào project. Adapter có thể publish từ worker
thread; Canvas chuyển update về GUI thread trước khi đổi element. Runtime Debugger
hiển thị state, protocol, số event, write, error và health của từng source.

MQTT, WebSocket, OPC-UA và Modbus adapter không bị ép thành dependency của widget;
host chỉ cần cung cấp QObject có signal/getter hoặc gọi `feedDataSource()`. Dùng
`unbindDataSource()` để tháo subscription; canvas tự disconnect và dừng timer khi
đóng. `dataBindingEvent`, `dataBindingStateChanged` và `dataBindingBatchApplied`
phục vụ logging/debug UI.

Inspector của từng element có card **Data bindings** với danh sách binding, source,
target, JSON transforms, format, debounce/throttle/stale, stale/error fallback và
enabled state. Binding đang chọn tự apply khi sửa. Runtime Debugger có tab Bindings
hiển thị live value, state, last input/apply và lỗi. Chuột phải element hoặc Ctrl+K
→ **Open data bindings** mở thẳng card này.

## Component packs

Ba pack native là opt-in nên không làm palette mặc định trở nên quá dày. Catalog
và schema nằm trong lõi thuần Python; renderer cùng Inspector chỉ được gắn ở Qt
adapter khi ứng dụng bật pack.

```python
canvas.enableComponentPack("dashboard")
canvas.enableComponentPack("industrial")
canvas.enableComponentPack("software")  # alias: flowchart

gauge = canvas.addPackComponent(
    "dash_gauge", 0, 0, element_id="cpu-gauge",
    text="CPU load", value=64, unit="%",
)
tank = canvas.addPackComponent(
    "ind_tank", 260, 0, element_id="process-tank", value=68, unit="%",
)
service = canvas.addPackComponent(
    "soft_service", 520, 0, element_id="metrics-api", technology="FastAPI",
)

canvas.addDataBinding(
    gauge, "property.value", "host.metrics",
    transforms={"op": "get", "path": "cpu"},
)
```

Catalog hiện có 43 component:

- **Dashboard (15):** KPI card, sparkline, gauge, progress ring, pie, donut,
  scatter, area, histogram, heatmap, timeline, event log, data table, status
  light và alarm banner;
- **Industrial (12):** tank, pump, valve, motor, fan, pipe, sensor, PLC,
  circuit breaker, battery, transformer và conveyor;
- **Software & Flowchart (16):** database, server, cloud, API, queue, topic,
  cache, file, service, container, process, decision, document, terminator,
  annotation và sticky note.

Mỗi item có renderer vector native, ID ổn định, schema/version/plugin owner và
card **Component properties** tự sinh theo đúng loại. Industrial và Software
components khai báo typed ports phù hợp; ví dụ tank dùng cổng `fluid`, API dùng
`dict`, sensor phát `number`, decision có `yes`/`no`. Mọi sửa đổi Inspector tự
apply, đi qua Undo/Redo và persistence như element chuẩn.

```python
canvas.componentPacks()
canvas.componentPackDefinitions("dashboard")
canvas.enabledComponentPacks()
canvas.enableAllComponentPacks()
canvas.componentPackEnabled("industrial")
canvas.disableComponentPack("industrial")
```

Disable chỉ tháo renderer/Inspector khỏi registry, không xóa record trong
document. Khi project được mở trên máy chưa bật pack, item xuất hiện dưới dạng
missing-component an toàn và phục hồi đúng ID/dữ liệu ngay khi pack được bật.
Menu chuột phải vùng trống và Ctrl+K đều có action bật/tắt từng pack.

## Node có nhiều port

Mỗi node có thể có số lượng port tùy ý. Port có ID ổn định và một trong ba mode:

- `input`: marker tam giác màu cam, hướng vào node và chỉ nhận kết nối;
- `output`: marker tam giác màu xanh, hướng ra ngoài node và chỉ phát kết nối;
- `free`: marker hình thoi xanh lá, có thể dùng ở một trong hai đầu.

```python
pump = canvas.addNode(
    "Pump", 0, 0, element_id="pump",
    ports=[
        {
            "id": "power", "mode": "input", "side": "left", "label": "Power",
            "dataType": "float", "unit": "V", "required": True,
            "defaultValue": 0.0, "maxConnections": 1,
            "acceptedTypes": ["int"], "acceptedUnits": ["mV"],
            "tooltip": "Điện áp cấp cho bơm",
        },
        {
            "id": "water-out", "mode": "output", "side": "right", "label": "Water",
            "dataType": "float", "unit": "L/min", "convertsTo": ["str"],
        },
        {"id": "service", "mode": "free", "side": "bottom", "label": "Service"},
    ],
)
canvas.addNodePort(
    pump, "alarm", "output", "top", "Alarm",
    dataType="bool", maxConnections=4, tooltip="Cảnh báo đang hoạt động",
)
canvas.removeNodePort(pump, "service")
ports = canvas.nodePorts(pump)

edge = canvas.connectPorts("pump", "water-out", "tank", "water-in")
result = canvas.portCompatibility("pump", "water-out", "tank", "water-in")
```

Mỗi port có `dataType`, `unit`, `required`, `defaultValue`, `maxConnections`
(`0` là không giới hạn), `acceptedTypes`, `acceptedUnits`, `convertsTo` và
`tooltip`. Các trường mở rộng vẫn được bảo toàn trong JSON. Compatibility engine
dùng cùng một contract cho model, API, reconnect, Inspector và kéo chuột; document
từ chối connector sai hướng, vượt cardinality, khác type/unit không có conversion.

Trong Inspector của node, danh sách port hiển thị type, unit và số connection;
toàn bộ contract phía trên có thể sửa trực tiếp và tự apply. Connector Inspector
có selector source/target port kèm type/unit. Khi kéo nối ngược từ input sang
output, editor tự đảo chiều. Candidate hợp lệ có halo xanh, candidate cần conversion
có halo tím, candidate không hợp lệ có halo đỏ; preview và `diagnosticMessage`
giải thích cùng một lý do. Nhấn `Esc` để hủy kéo nối.

Runtime value là trạng thái tạm thời để code/runtime và Inspector quan sát, không
được serialize hoặc làm document dirty:

```python
canvas.portRuntimeValueChanged.connect(on_port_value)
canvas.setPortRuntimeValue("pump", "water-out", 42.5)
value = canvas.portRuntimeValue("pump", "water-out")
state = canvas.portRuntimeState("pump", "water-out")
canvas.clearPortRuntimeValue("pump", "water-out")
```

`setPortRuntimeValue()` kiểm tra type mặc định; truyền `validate=False` nếu runtime
adapter cần đưa giá trị lỗi vào Inspector để chẩn đoán. Nếu chưa có runtime value,
`portRuntimeValue()` trả `defaultValue` khi port khai báo giá trị mặc định.

Các trường Inspector tự apply: combo/check áp dụng ngay, số học debounce ngắn và
text/points áp dụng sau khoảng gõ rất ngắn. Dữ liệu points chưa hoàn chỉnh trong
lúc gõ chỉ tạo diagnostic, không làm đóng ứng dụng hay ghi document lỗi.

Inspector tự thay đổi theo object: media có source picker; chart có series data;
shape có content/geometry/appearance; line có stroke, arrow và points; node có
port editor; connector có endpoint/port, route, flow animation, waypoint, opacity
và layer Z.

## Frame, swimlane và reusable subflow

Group là object document-backed có ID ổn định, không phải lớp trang trí tạm. Nó
xuất hiện trong Layers và Minimap, có Inspector riêng, Undo/Redo, lock/hide,
collapse, lồng group và di chuyển toàn bộ thành viên trong một command. Model từ
chối group tham chiếu thiếu hoặc tạo cycle.

```python
frame = canvas.addFrame(("source", "processor"), label="Processing")
lanes = canvas.addSwimlane(
    ("source", "processor", "sink"),
    "main-pipeline",
    label="Main pipeline",
    lanes=("Ingress", "Compute", "Delivery"),
    orientation="horizontal",
)
subflow = canvas.addSubflow(
    ("retry", "dead-letter"),
    label="Recovery policy",
)

canvas.setGroupCollapsed(subflow, True)
canvas.moveGroup(lanes, 240, 120)
canvas.fitGroupToContents(lanes)
canvas.renameGroup(lanes, "production-pipeline")
```

Double-click header để collapse/expand. Right-click cho phép tạo group từ nhiều
node, fit lại frame, ungroup hoặc export JSON template. Template không chứa Python
code; import remap toàn bộ element, connector và nested-group ID để tránh collision:

```python
canvas.saveSubflowTemplate(subflow, "recovery.monkez-subflow.json")
new_group = canvas.loadSubflowTemplate(
    "recovery.monkez-subflow.json", x=800, y=240
)
```

Subflow dùng lại thường xuyên có thể publish vào catalog portable của project.
Catalog nằm trong `.monkez_canva/templates`, nên đi cùng repository khi copy sang
máy khác:

```python
canvas.saveGroupAsProjectTemplate(
    subflow, "recovery-flow", description="Recovery pipeline", tags=("ops",)
)
available = canvas.projectTemplates("ops")
new_group = canvas.instantiateProjectTemplate("recovery-flow", x=800, y=240)
canvas.showProjectTemplateBrowser()
```

Manifest có ID, label, description, tags, thumbnail và author; payload bị giới
hạn kích thước/số object và được validate trước khi ghi hoặc instantiate. Mỗi lần
instantiate vẫn là một Undo command collision-safe.
Template Browser là cửa sổ Tool tách rời Control Pane, có search theo label,
description/tag, tag filter, preview thumbnail hoặc sơ đồ fallback và nút Insert.
Mở browser từ menu chuột phải vùng trống hoặc `Ctrl+K`. Truyền
`capture_thumbnail=True` vào `saveGroupAsProjectTemplate()` để tự render PNG
portable vào `templates/thumbnails` mà không làm dirty document.

## Document health và semantic diff

`Document Health` là cửa sổ Tool độc lập, mở từ menu chuột phải canvas trống hoặc
`Ctrl+K` với từ khóa `health`. Cửa sổ gồm Health, metrics và Changes since save;
baseline được cập nhật sau mỗi lần save/load nên diff không phụ thuộc thứ tự record.

```python
health = canvas.diagnoseDocument()
print(health.severity, health.counts, health.metrics)

changes = canvas.documentDiff()                 # baseline save/load -> current
external = canvas.documentDiff("review.json")  # supplied document -> current
canvas.exportDocumentReport("reports/canvas-health.json")
canvas.showDocumentDiagnostics()
```

Lớp Qt-free `diagnose_document()` kiểm tra document graph, component registry,
component schema/version, port, group/resource và asset manifest. `diff_documents()`
so sánh scene/element/connector/group/resource theo stable ID, báo field lồng nhau
và tạo SHA-256 fingerprint ổn định ngay cả khi thứ tự record thay đổi. Report chỉ
đọc, không tạo Undo command và không làm dirty document.

## Export hình ảnh, tài liệu và graph

Floatbar có nút **Export** độc lập với Save. Canvas có thể xuất toàn scene hoặc
selection hiện tại sang PNG, PNG nền trong suốt, SVG vector và PDF. Inspector,
selection handle, smart guide, minimap và floatbar không xuất hiện trong kết quả.
Trạng thái selected/visible của mọi object được phục hồi nguyên vẹn sau khi render.

```python
canvas.exportScene("output/diagram.png", scale=2)
canvas.exportScene("output/diagram-transparent.png", transparent=True)
canvas.exportSelection("output/selected.svg", padding=16)

canvas.setExportPageConfiguration({
    "size": "A4",                 # A3, A4, A5, LETTER, LEGAL
    "orientation": "landscape",  # portrait | landscape
    "margin_left_mm": 10,
    "margin_top_mm": 10,
    "margin_right_mm": 10,
    "margin_bottom_mm": 10,
    "resolution": 180,
})
canvas.exportScene("output/diagram.pdf")
canvas.showPageSetup()
canvas.showPrintPreview()
```

`exportGraphic(path, scope=..., format=..., transparent=..., padding=..., scale=...)`
là API chung. `exportCompleted(path, format, scope)` được phát sau khi file hợp lệ
đã được tạo. Export là read-only: không làm dirty document, không tạo Undo command
và dùng được cả khi document đang ở compatibility read-only mode.

Graph exchange không phụ thuộc Graphviz, Mermaid CLI hay Qt:

```python
canvas.exportDot("output/pipeline.dot")
canvas.exportMermaid("output/pipeline.mmd", direction="LR")

from monkez_pyqt6.monkez_canva import export_dot, export_mermaid
dot_text = export_dot(canvas.documentModel(), ["source", "transform", "sink"])
mermaid_text = export_mermaid(canvas.documentModel(), direction="TB")

# Import at an exact top-left position, or omit x/y to center in the viewport.
report = canvas.loadDot("input/pipeline.dot", x=120, y=80)
subflow = canvas.importDot(dot_text, as_subflow=True, group_label="API pipeline")

from monkez_pyqt6.monkez_canva import import_dot
portable_result = import_dot(dot_text)  # Qt-free parse/validation only
```

DOT giữ stable ID, component type, port ID, arrow direction, kích thước và vị trí.
Mermaid dùng alias an toàn, shape phù hợp cho decision/database/terminator/note và
escape nội dung để có thể nhúng trực tiếp vào Markdown. Khi export một group hoặc
nhiều node, nested member và connector nội bộ được tự động đưa vào phạm vi.
Các thao tác này có trong menu chuột phải và Ctrl+K; Page setup và Print preview
dùng native Qt dialog với cùng một cấu hình trang trong phiên chạy.

DOT import hỗ trợ tập con an toàn gồm node/edge, chained edge, quoted ID,
graph/node/edge defaults, endpoint ports và các thuộc tính do MonkezCanva export.
Subgraph, HTML-like label và tính năng cần chạy Graphviz bên ngoài bị từ chối.
Importer giữ ID nếu có thể, tự đổi ID trùng một cách xác định, suy luận typed port,
tự layout node thiếu `pos`, và gom toàn bộ thay đổi vào đúng một Undo command.
Component pack gốc được tự bật khi type đã biết; type lạ hạ cấp thành generic node
và được ghi trong `report["warnings"]` cùng `metadata.dotOriginalType`.

## Lưu và đọc tài liệu

```python
canvas.saveDocument("workflow.monkez-canva.json")
canvas.loadDocument("workflow.monkez-canva.json")

payload = canvas.toJson()
other_canvas.loadDocument(payload)
```

### Document model dùng chung

`CanvasDocument` là model thuần Python, không cần tạo `QApplication` hay `QWidget`.
Record scene, element, connector, port, group và resource là dữ liệu JSON bất biến;
mọi thay đổi tăng `revision` và phát `OperationEvent` chi tiết. Cùng một document có
thể điều khiển nhiều canvas view:

```python
from monkez_pyqt6.monkez_canva import CanvasDocument

document = CanvasDocument.empty({"width": 2400, "height": 1600})
left_canvas.setDocumentModel(document)
right_canvas.setDocumentModel(document)

document.add_element({"id": "source", "type": "node", "text": "Source"})
document.update_element("source", {"text": "Updated in every view"})
document.subscribe(lambda event: print(event.action, event.revision))
```

Các API `addElement`, `updateElement`, `removeElement`, `renameElement`,
`connectElements`, `updateConnector`, `removeConnector`, `renameConnector`,
`addGroup`, `updateGroup`, `removeGroup` và `renameGroup` ghi
vào model trước. Mỗi view chỉ render operation liên quan thay vì dựng lại toàn bộ
scene; selection, zoom, viewport và identity của item được giữ nguyên khi model
được cập nhật từ code hoặc từ một view khác.

### Đăng ký component riêng

Với plugin có một hoặc nhiều component, nên dùng public Component SDK để kiểm tra
ownership và cài toàn manifest theo cách nguyên tử:

```python
from my_company.monkez_plugin import PLUGIN

canvas.registerElementPlugin(PLUGIN)
canvas.componentPluginChanged.connect(print)
```

Xem [MonkezCanva Component Plugin SDK](MONKEZ_CANVA_PLUGIN_SDK.md) và
[`examples/canva_component_plugin.py`](../examples/canva_component_plugin.py)
để có ví dụ đầy đủ về renderer vector, typed port và Inspector auto-apply.
`registerElementDefinition()` bên dưới vẫn là API mức thấp phù hợp cho một
component được khai báo trực tiếp trong ứng dụng.

Plugin portable theo project nằm trong `.monkez_canva/plugins/<package>/`. Mở
Plugin Manager từ menu chuột phải canvas hoặc `Ctrl+K` với từ khóa `plugins` để
xem manifest, component types, đường dẫn và SHA-256. Discovery không chạy code;
chỉ nút **Trust and load** mới import entry point. Trust chỉ giữ trong process và
tự vô hiệu khi bất kỳ source/asset nào trong package thay đổi.

```python
from monkez_pyqt6.monkez_canva import ElementDefinition

def migrate_sensor_v1(record):
    record["value"] = record.pop("reading")
    return record

canvas.registerElementDefinition(
    ElementDefinition(
        "sensor", "Sensor", "Industrial", 150, 86,
        defaults={"unit": "bar"},
        schema={
            "required": ["value"],
            "properties": {
                "value": {"type": "number", "minimum": 0},
                "unit": {"type": "string", "enum": ["bar", "psi"]},
            },
        },
        schema_version=2,
        migrations={1: migrate_sensor_v1},
        plugin_id="industrial-pack",
        plugin_version="1.0.0",
        capabilities={"content", "geometry", "appearance", "ports"},
        renderer_factory=paint_sensor,       # (painter, item, rect, option, widget)
        inspector_factory=inspect_sensor,    # (canvas, item) -> QWidget | None
    )
)
sensor_id = canvas.addElement("sensor", 120, 80, value=42)
```

Category và nút trong Elements pane được tạo từ registry. Nếu project tham chiếu
component của plugin chưa cài, canvas hiển thị placeholder an toàn và giữ nguyên
type/data trong document để có thể khôi phục khi plugin xuất hiện.
`canvas.unregisterElementPlugin("industrial-pack")` gỡ toàn bộ factory thuộc
plugin nhưng không xóa record. Khi đăng ký lại type, placeholder được khôi phục
tại chỗ và giữ nguyên ID. Document không bao giờ tự import module từ JSON.

`canvas.documentModel()`/`canvas.canvasDocument()` trả về model đang gắn. Signal
`documentOperation(dict)` cung cấp bản JSON-safe của event cho code Qt. Loader vẫn
đọc version 1 và tự normalize `arrow`/`polyline` cũ thành unified `line`.

Editor có ba tầng lưu:

1. **Autosave draft**: sau thay đổi, document được debounce và giữ trong bộ nhớ;
   history undo/redo cũng được tạo tại đây.
2. **Save session checkpoint**: lưu mốc khôi phục trong vòng đời process hiện tại;
   đóng app sẽ mất checkpoint này.
3. **Save persistent now**: ghi JSON vào `.monkez_canva/<persistenceKey>.json`
   ngay trong project và copy ảnh/GIF/background/packet icon/resource vào thư
   mục assets bên cạnh.
   JSON chỉ lưu đường dẫn tương đối, vì vậy có thể copy cả project sang máy hoặc
   ổ đĩa khác rồi tự load mà không cần sửa path.

```python
canvas.setPersistenceKey("main-dashboard")
canvas.setProjectDirectory("D:/Projects/MyApp")  # tùy chọn
canvas.setAutoSaveDelay(500)
canvas.setAutoSaveEnabled(True)

canvas.saveSession()
canvas.restoreSession()

canvas.savePersistent()
canvas.loadPersistent()

# Kiểm tra lại SHA-256/size của toàn bộ managed assets
for warning in canvas.verifyPersistentAssets():
    print(warning)
```

Mỗi lần ghi JSON sử dụng file tạm cùng thư mục rồi `os.replace`, vì vậy app bị
dừng giữa lúc lưu không để lại JSON viết dở ở đường dẫn chính. Nếu primary hiện
tại hợp lệ, phiên bản đó được giữ ở `<filename>.json.bak` trước khi thay thế.
Khi primary bị hỏng hoặc mất, loader tự đọc backup, phát
`recoveryLoaded(primary, backup)` và ghi rõ nguyên nhân qua `diagnosticMessage`;
loader không tự ghi đè primary lỗi nên vẫn có thể điều tra hoặc khôi phục thủ công.

File persistent chứa `assetManifest`: mỗi ảnh/GIF, background, packet icon và
resource tương đối có SHA-256 cùng kích thước byte. Khi load, canvas phát
`assetIntegrityChecked(list[str])`; kết quả gần nhất đọc bằng
`assetIntegrityIssues()`. Thiếu file, checksum sai và path thoát khỏi project đều
được cảnh báo nhưng không kích hoạt code hay tự tải nội dung từ bên ngoài.

### Undo/Redo dạng command

```python
canvas.addNode("Source", element_id="source")
canvas.updateElement("source", x=120, y=80)

if canvas.canUndo():
    print(canvas.undoText())
    canvas.undo()
    canvas.redo()

canvas.beginCommandMacro("Move pipeline")
try:
    canvas.updateElement("source", x=200)
    canvas.updateElement("target", x=500)
finally:
    canvas.endCommandMacro()
```

History dùng `QUndoStack` tối đa 80 command. Mỗi command chỉ giữ record thay đổi,
không giữ snapshot toàn document. Kéo, resize và nhập Inspector liên tục trên cùng
object được nén trong 800 ms. `Ctrl+Z`/`Ctrl+Y`, Save pane và floating toolbar dùng
cùng stack. `isDocumentModified()` chỉ trở về `False` sau lưu document/persistent;
autosave draft không đánh dấu nhầm là đã lưu dài hạn.

Project root được tự dò từ working directory hoặc vị trí entry script thông qua
`.git`, `pyproject.toml`, `setup.py` hay `requirements.txt`. Có thể override bằng
`setProjectDirectory()` hoặc biến môi trường `MONKEZ_CANVA_PROJECT_DIR`. Khi
`persistenceKey` khác rỗng và `autoSaveEnabled=True`, mỗi autosave debounce đồng
thời cập nhật bản lưu portable. Dữ liệu AppData của bản cũ được tự phát hiện và
migrate vào project trong lần load đầu tiên.

Sau khi `persistenceKey` (và `projectDirectory` nếu cần) được cấu hình, event loop
sẽ tự nạp file portable nếu Canvas còn trống. Cơ chế này cố ý không thay thế một
Canvas đã được code thêm object. Có thể gọi `loadPersistent()` thủ công khi ứng
dụng thực sự muốn ghi đè nội dung hiện tại.

Khi copy project, cần copy cả thư mục ẩn `.monkez_canva`. Nếu không đặt key,
autosave chỉ giữ draft/history trong RAM và nút lưu bền dùng `objectName` hoặc key
mặc định.

## Grid và background

Tab View cho phép bật/tắt grid, chọn `Lines`, `Dots` hoặc `Cross`, đổi grid color,
background color, chọn background image và mode `Fit`, `Fill` hoặc `Scale`.

```python
canvas.setGridVisible(True)
canvas.setGridStyle("dots")
canvas.setGridColor("#cbd5e1")
canvas.setBackgroundColor("#f8fafc")
canvas.setBackgroundImage("assets/workspace-bg.png")
canvas.setBackgroundImageMode("fill")
```

Các thiết lập scene này nằm trong document/history/autosave và background image
cũng được quản lý như một portable project asset.

Định dạng JSON hiện tại có `format: "monkez-canva"`, `version: 1`, danh sách
`elements` và `connectors`. Mỗi element có `metadata` để ứng dụng gắn business ID
hoặc cấu hình riêng. Tài liệu không chứa và không thực thi Python code.

JSON Schema Draft 2020-12 được export thành `DOCUMENT_JSON_SCHEMA`; ứng dụng có
thể dùng schema này để kiểm tra project trong CI hoặc công cụ ngoài Qt. Bản JSON
độc lập được đóng gói tại `monkez_pyqt6/monkez_canva/schemas/monkez-canva-document-v1.schema.json`.
Nếu file
có document version mới hơn runtime, hoặc một element có `componentVersion` mới
hơn definition đã đăng ký, canvas vẫn dựng phần dữ liệu tương thích để xem nhưng
chuyển sang **read-only**. `isReadOnly()`/`readOnlyReason()` cho biết trạng thái;
mọi mutation, autosave và Save đều bị chặn để runtime cũ không làm mất trường mới.
Layers, zoom/pan, highlight và hiệu ứng runtime vẫn dùng được. Control Pane hiển
thị footer khóa màu amber và chỉ để tab Layers hoạt động.

Control Pane dùng thanh tab icon dạng segmented, card bo góc và lưới thuộc tính
hai cột. Spinbox dùng chevron SVG đóng gói cùng thư viện nên không phụ thuộc
kiểu nút mặc định của Windows. Các thay đổi Inspector vẫn tự apply; footer phân
biệt `Session saved`, `Unsaved changes`, `Saved` và trạng thái read-only.
Card đặt tiêu đề hoàn toàn bên trong bề mặt nên không còn đường viền cắt qua chữ;
vùng tăng/giảm của spinbox có separator nhẹ và trạng thái hover riêng. Thanh tab
dùng selected state coral nhẹ, không chiếm layout và không làm dịch chuyển canvas.

Toàn bộ hiệu ứng line/connector, packet và `animateElement()` chia sẻ một clock
của canvas. `animationStats()` cho biết số target, tick và repaint; dùng
`setAnimationFrameInterval(ms)` để điều chỉnh chu kỳ (tối thiểu 16 ms). Khi
canvas bị ẩn, hiệu ứng trang trí và loop tạm dừng, nhưng packet gửi từ code vẫn
đi tới đích để `wait_to_end=True` không bị treo.

## Thuộc tính Qt Designer

`gridVisible`, `snapToGrid`, `gridSize`, `gridStyle`, `backgroundColor`,
`backgroundImage`, `backgroundImageMode`, `gridColor`, `editorShortcutEnabled`,
`editMode`, `persistenceKey`, `projectDirectory`, `autoSaveEnabled` và
`autoSaveDelay` xuất hiện trong Property Editor. Không nên
lưu `editMode=True` trong form phát hành; hãy dùng chord runtime khi cần sửa.

## Phạm vi phiên bản đầu

Phiên bản hiện tại đã có inspector, layer/ID manager, ảnh/GIF, autosave, session
checkpoint, lưu bền, history và viewport tools. Các hướng nâng cấp tiếp theo:

- registry để ứng dụng tự đăng ký element/plugin mới;
- nhúng QWidget bất kỳ vào scene;
- clipboard copy/paste đa item hoặc multi-user collaboration;
- data binding declarative và auto layout;
- chart axis/series editor và data-type validation giữa các port.

Route `Auto` hiện tự tránh các element hình chữ nhật với clearance cấu hình được.
Crossing bridge làm rõ đường nằm trên tại giao điểm; connector hỗ trợ bus style
`Trunk`/`Double`, độ rộng và `busId`. Các tùy chọn có public API, context action,
Inspector auto-apply và được lưu cùng project.

Các phần này nên được phát triển thành lớp extension riêng thay vì làm class lõi
phình to. Xem kiến trúc và roadmap trong `agents/MONKEZ_CANVA_ARCHITECTURE.md`.
