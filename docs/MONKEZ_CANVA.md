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
```

Signal chính gồm `elementAdded(str)`, `elementRemoved(str)`,
`elementClicked(str)`, `selectionChanged(str)`, `editModeChanged(bool)` và
`documentChanged()`.

## Lưu và đọc tài liệu

```python
canvas.saveDocument("workflow.monkez-canva.json")
canvas.loadDocument("workflow.monkez-canva.json")

payload = canvas.toJson()
other_canvas.loadDocument(payload)
```

Định dạng JSON hiện tại có `format: "monkez-canva"`, `version: 1`, danh sách
`elements` và `connectors`. Mỗi element có `metadata` để ứng dụng gắn business ID
hoặc cấu hình riêng. Tài liệu không chứa và không thực thi Python code.

## Thuộc tính Qt Designer

`gridVisible`, `snapToGrid`, `gridSize`, `backgroundColor`, `gridColor`,
`editorShortcutEnabled` và `editMode` xuất hiện trong Property Editor. Không nên
lưu `editMode=True` trong form phát hành; hãy dùng chord runtime khi cần sửa.

## Phạm vi phiên bản đầu

Phiên bản hiện tại tập trung vào scene editor, chart nhẹ và flow diagram. Chưa có:

- registry để ứng dụng tự đăng ký element/plugin mới;
- nhúng QWidget bất kỳ vào scene;
- undo/redo theo command stack, copy/paste hoặc multi-user collaboration;
- data binding declarative, routing connector tránh vật cản và auto layout;
- property inspector đầy đủ cho text, kích thước, chart axis và port schema.

Các phần này nên được phát triển thành lớp extension riêng thay vì làm class lõi
phình to. Xem kiến trúc và roadmap trong `agents/MONKEZ_CANVA_ARCHITECTURE.md`.
