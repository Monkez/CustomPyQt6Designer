# Designer portable

## Dùng bản one-folder

1. Lấy nguyên thư mục `MonkezDesigner`.
2. Giữ nguyên thư mục `_internal` cạnh file chạy.
3. Chạy `MonkezDesigner.exe`.

Không di chuyển riêng file `.exe` ra khỏi thư mục vì Qt, Python bridge và plugin nằm trong `_internal`.

Mở trực tiếp một file UI:

```powershell
MonkezDesigner.exe path\to\main_window.ui
```

## Theme trong Property Editor

Property `themeIndex`:

| Giá trị | Theme |
|---:|---|
| 0 | Material |
| 1 | iOS |
| 2 | Fluent |
| 3 | Bootstrap |
| 4 | Minimal |
| 5 | Dark |

Cũng có thể click phải widget trên canvas và chọn `Monkez Theme`.

## Camera preview

Đặt:

- `previewAutoStart = true`
- `cameraSource = 0`
- `backend = dshow` hoặc `auto` trên Windows

Sau đó nhấn `Ctrl+R`. Camera không tự mở khi widget chỉ nằm trên canvas thiết kế.

## Phát triển từ source

Python bridge của `pyqt6-tools` ổn định nhất với Python 3.11:

```powershell
py -3.11 -m venv .venv311
.\.venv311\Scripts\python.exe -m pip install -e ".[all]"
.\.venv311\Scripts\custom-pyqt6-designer.exe --debug
```

Kiểm tra đường dẫn plugin:

```powershell
.\.venv311\Scripts\custom-pyqt6-plugin-info.exe
```

Build lại portable:

```powershell
.\scripts\build_full_designer.ps1
```

Kết quả nằm tại `dist\MonkezDesigner`. Script không tạo file ZIP và sẽ
tự mở Designer ở chế độ kiểm tra để xác nhận toàn bộ plugin đã được load.
