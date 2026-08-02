# Rà soát khả năng widget

Cập nhật: 2026-08-02

Package hiện có 26 runtime widget và 26 plugin Qt Designer. Việc rà soát tập
trung vào những API ứng dụng thường cần nhưng Qt gốc chưa cung cấp thuận tiện,
đồng thời không tạo property trùng lặp với API kế thừa sẵn có.

## Kết quả đã bổ sung

- `MonkezLCDNumber`: dấu phẩy được vẽ theo đúng baseline của segment với đầu
  chấm và nét đuôi cong đủ rõ ở cả preview nhỏ; hỗ trợ cấu hình số bằng
  `number`, `decimalPlaces`,
  `decimalSeparator`, `groupSeparator`, `groupingEnabled`, `autoDigitCount`.
- `MonkezPagination`: bổ sung điều hướng trang 1-based với ellipsis responsive,
  bốn style Rounded/Pill/Minimal/Compact, cấu hình theo số trang hoặc
  `totalItems`/`pageSize`, điều hướng bàn phím, loop, wheel và đầy đủ màu/trạng
  thái trong Designer.
- `MonkezRadialGauge`: tiếp tục dùng các tên màu theo đúng thành phần trực quan
  (`activeTicksColor`, `inactiveTicksColor`, `needleColor`, `valueTextColor`,
  `scaleTextColor`) thay cho việc buộc người dùng đoán vai trò màu chung chung.

## Phạm vi đã kiểm tra

| Nhóm | Kết luận |
|---|---|
| Action/Input | Các hành vi chuẩn như checked, tri-state, editable, validator, clear button, echo mode và signals đã có từ Qt; package chỉ bổ sung theme, icon, popup và kích thước. |
| Value/Date-time | Range, step, format, orientation, keyboard và signals dùng API Qt chuẩn; các property hình học/màu riêng đã có trong Designer. |
| Display/Gauge | LCD và Radial Gauge là hai khoảng trống API rõ nhất và đã được hoàn thiện; Arc/Linear Gauge đã có threshold, target và orientation. |
| Media | Image đã có Fit/Fill/Stretch/Original, file/Qt/NumPy frame; Camera đã có backend, source, resolution, FPS, mirror và reconnect. |
| Container/Startup | Frame, GroupBox, ScrollArea và Splash đã có geometry, theme và runtime lifecycle cần thiết. |

## Nguyên tắc tiếp tục phát triển

- Ưu tiên API chuyên biệt khi vai trò trực quan không rõ bằng tên chung.
- Tận dụng property/signal kế thừa của Qt thay vì tạo bản sao dễ lệch trạng thái.
- Mọi widget mới phải có runtime class, lazy export, Designer plugin/icon/task
  menu khi cần, Gallery docs/live preview, kiểm thử render và tài liệu người dùng.
- Các ý tưởng như loading button, slider value bubble, badge/toast và breadcrumb
  được giữ ở backlog; chỉ triển khai khi có use case rõ để tránh làm package nặng
  và khó nhất quán.
