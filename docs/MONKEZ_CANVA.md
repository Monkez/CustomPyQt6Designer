# MonkezCanva

`MonkezCanva` là canvas editor nhúng trực tiếp trong ứng dụng PyQt6. Widget dùng
được ở runtime, có plugin Qt Designer và không phụ thuộc WebEngine.

## Chạy demo

Chạy `canva_demo.bat`. Có thể nhấn `Ctrl+D`, thả `Ctrl` rồi nhấn `E`, hoặc giữ
`Ctrl` và lần lượt nhấn `D`, `E`. Cửa sổ `MonkezCanva Elements` sẽ xuất hiện.
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

- **Elements**: thêm shape, chart, node, ảnh và GIF; duplicate/xóa item.
- **Inspector**: sửa ID, text, source, vị trí, kích thước, rotation, opacity,
  z-order và ba vai trò màu.
- **Layers**: quản lý toàn bộ item theo ID ổn định và chọn nhanh trên canvas.
- **View**: zoom in/out, 100%, fit, di chuyển viewport bốn hướng, center selection
  và chuyển đổi pan/select mode.
- **Save**: checkpoint trong phiên, lưu/đọc bền, undo và redo.

Khi bật Edit Mode, thanh quick actions nổi chồng ở mép trên viewport, không tham gia
layout nên không đẩy canvas xuống hoặc làm thay đổi tâm nhìn. Floatbar cung cấp
Save, zoom out, 100%, zoom in, Fit và các lệnh căn Left, Right, Top, Bottom, tâm
ngang, tâm dọc hoặc đúng tâm hai chiều. Các nút căn chỉ bật khi có từ hai item được
chọn.

Control pane là cửa sổ tool không viền, kích thước gọn, có shadow, header kéo được,
tab tự co đều và nút đóng Edit Mode riêng. Pane dùng chung visual language cho card,
input, layer row, trạng thái lưu và action chính/nguy hiểm.

Có ba cách chọn nhiều item: giữ `Ctrl` khi bấm, kéo rubber-band qua nhiều item,
hoặc chọn nhiều dòng trong tab Layers. Giữ chuột phải trên vùng canvas trống rồi
kéo để di chuyển viewport mà không làm mất selection hiện tại.

`fitContent()` có thể được gọi trước `show()`; canvas sẽ hoãn việc tính tỷ lệ đến
khi viewport có kích thước thật. Zoom tự động được giới hạn trong khoảng dễ thao
tác, tránh graph bị thu thành một chấm nhỏ trên màn hình lớn.

View mode khóa thao tác sửa nhưng vẫn phát signal `elementClicked`. Phím tắt có
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
```

Không thể dùng ID rỗng hoặc trùng. Connector giữ tham chiếu đúng khi ID endpoint
được đổi. Signal `itemIdChanged(old_id, new_id)` cho phép business logic cập nhật
mapping riêng.

Signal chính gồm `elementAdded(str)`, `elementRemoved(str)`,
`elementClicked(str)`, `selectionChanged(str)`, `editModeChanged(bool)` và
`documentChanged()`. Signal `selectionSetChanged(list)` cung cấp toàn bộ ID đang
được chọn; `selectedElementIds()` trả về cùng tập ID theo thứ tự document.

## Lưu và đọc tài liệu

```python
canvas.saveDocument("workflow.monkez-canva.json")
canvas.loadDocument("workflow.monkez-canva.json")

payload = canvas.toJson()
other_canvas.loadDocument(payload)
```

Editor có ba tầng lưu:

1. **Autosave draft**: sau thay đổi, document được debounce và giữ trong bộ nhớ;
   history undo/redo cũng được tạo tại đây.
2. **Save session checkpoint**: lưu mốc khôi phục trong vòng đời process hiện tại;
   đóng app sẽ mất checkpoint này.
3. **Save persistent now**: ghi JSON vào `QStandardPaths.AppDataLocation` và copy
   ảnh/GIF vào thư mục assets do MonkezCanva quản lý. Dữ liệu còn nguyên sau khi
   app chính khởi động lại.

```python
canvas.setPersistenceKey("main-dashboard")
canvas.setAutoSaveDelay(500)
canvas.setAutoSaveEnabled(True)

canvas.saveSession()
canvas.restoreSession()

canvas.savePersistent()
canvas.loadPersistent()
```

Khi `persistenceKey` khác rỗng và `autoSaveEnabled=True`, mỗi autosave debounce sẽ
đồng thời cập nhật bản lưu bền. Nếu không đặt key, autosave chỉ giữ draft/history
trong RAM và nút lưu bền dùng `objectName` hoặc key mặc định.

Định dạng JSON hiện tại có `format: "monkez-canva"`, `version: 1`, danh sách
`elements` và `connectors`. Mỗi element có `metadata` để ứng dụng gắn business ID
hoặc cấu hình riêng. Tài liệu không chứa và không thực thi Python code.

## Thuộc tính Qt Designer

`gridVisible`, `snapToGrid`, `gridSize`, `backgroundColor`, `gridColor`,
`editorShortcutEnabled`, `editMode`, `persistenceKey`, `autoSaveEnabled` và
`autoSaveDelay` xuất hiện trong Property Editor. Không nên
lưu `editMode=True` trong form phát hành; hãy dùng chord runtime khi cần sửa.

## Phạm vi phiên bản đầu

Phiên bản hiện tại đã có inspector, layer/ID manager, ảnh/GIF, autosave, session
checkpoint, lưu bền, history và viewport tools. Các hướng nâng cấp tiếp theo:

- registry để ứng dụng tự đăng ký element/plugin mới;
- nhúng QWidget bất kỳ vào scene;
- clipboard copy/paste đa item hoặc multi-user collaboration;
- data binding declarative, routing connector tránh vật cản và auto layout;
- chart axis/series editor và typed port schema chuyên sâu.

Các phần này nên được phát triển thành lớp extension riêng thay vì làm class lõi
phình to. Xem kiến trúc và roadmap trong `agents/MONKEZ_CANVA_ARCHITECTURE.md`.
