# Chất lượng và kiểm tra package

Repository cung cấp các lệnh một-click sau:

```powershell
setup.bat
lint.bat
test.bat
build.bat
```

## MonkezCanva large-scene baseline

Run `benchmark_canva.bat` from the repository root. It uses the managed Python
3.11 environment, exercises native 100/1,000/10,000-node scenes at detail and
overview zoom, streams output into `canva_performance.log` and writes structured
metrics to `canva_performance.json`. Compare frame metrics only when viewport,
Python, Qt, OS and connector option match. The release baseline is retained in
`docs/benchmarks/`.

- `setup.bat` tạo môi trường Python 3.11 và cài runtime, Designer, camera, build,
  lint trong cùng một virtual environment.
- `lint.bat` kiểm tra lỗi cú pháp, import/biến không dùng và các lỗi Python tĩnh
  có độ tin cậy cao.
- `test.bat` chạy toàn bộ test ở Qt offscreen, gồm runtime widget, file `.ui`,
  Designer plugin, splash, launcher, installer và packaging.
- `build.bat` tạo wheel/source archive rồi build, mở kiểm tra và đóng gói
  Designer portable.

## Cam kết hành vi của widget

- Widget không đặt hard minimum size lớn làm khóa layout.
- Màu `QColor` có alpha được giữ nguyên khi chuyển sang Qt stylesheet.
- Theme, property Designer và setter Python cho cùng kết quả runtime.
- Control tương tác giữ nguyên API/signal chuẩn của Qt; property bổ sung không
  tự ý thay đổi các property độc lập như `textVisible`.
- Custom paint có trạng thái disabled/focus và hỗ trợ kích thước compact tại
  những widget có thể co nhỏ.
- `MonkezImage` và camera không import NumPy/OpenCV cho đến khi thật sự cần.

Camera vật lý, backend hệ điều hành và preview Designer vẫn phụ thuộc thiết bị,
driver và quyền truy cập của máy đích. Test tự động bao phủ cấu hình/thread và
đường hiển thị frame; trước khi phát hành ứng dụng camera nên chạy thêm smoke
test trên đúng thiết bị mục tiêu.
