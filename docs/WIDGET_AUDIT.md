# Rà soát khả năng widget

Cập nhật: 2026-08-03

Package hiện có 35 runtime widget/component và 34 plugin Qt Designer. `MonkezToast`
chỉ dùng ở runtime nên không xuất hiện trong Widget Box. Việc rà soát tập
trung vào những API ứng dụng thường cần nhưng Qt gốc chưa cung cấp thuận tiện,
đồng thời không tạo property trùng lặp với API kế thừa sẵn có.

## Kết quả đã bổ sung

- `MonkezLCDNumber`: chỉ dùng dấu chấm thập phân nguyên bản của `QLCDNumber`;
  đã bỏ phần vẽ dấu phẩy cùng các property separator/grouping để giao diện ổn
  định và nhất quán. Chuỗi cũ chứa dấu phẩy được tự loại bỏ khi nạp; hỗ trợ cấu
  hình số bằng `number`, `decimalPlaces`, `displayText`, `autoDigitCount`.
  `digitColor` không bị stylesheet chung của ứng dụng lấn át nhưng vẫn cho phép
  stylesheet gắn trực tiếp ghi đè.
- `MonkezPagination`: bổ sung điều hướng trang 1-based với ellipsis responsive,
  bốn style Rounded/Pill/Minimal/Compact, cấu hình theo số trang hoặc
  `totalItems`/`pageSize`, điều hướng bàn phím, loop, wheel và đầy đủ màu/trạng
  thái trong Designer.
- `MonkezTable`: data grid native theo kiến trúc model/view, không tạo item cho
  từng cell; có global/per-column filter, stable multi-sort, local/server
  pagination, typed delegates, selection/editing, CSV, state persistence và
  bốn style cùng ba mật độ hiển thị.
- `MonkezRadialGauge`: tiếp tục dùng các tên màu theo đúng thành phần trực quan
  (`activeTicksColor`, `inactiveTicksColor`, `needleColor`, `valueTextColor`,
  `scaleTextColor`) thay cho việc buộc người dùng đoán vai trò màu chung chung.

## Chuẩn hóa anti-alias và viền

- Các nét viền tự vẽ được căn theo độ rộng pen và pixel vật lý, giữ toàn bộ nét
  nằm trong hình học của widget thay vì để nửa nét bị cắt ở mép.
- Quy tắc dùng chung đã được áp dụng cho ComboBox popup, GroupBox, RadioButton,
  Switch, Pagination, Calendar, Table badge/frame, RangeSlider và Dial.
- Bán kính bo được giảm tương ứng sau khi inset nét, nhờ đó bốn góc có cùng độ
  đậm và không còn góc trên mờ hoặc đường viền chắp nối.
- `handleSize` của RangeSlider và Dial nay là đường kính ngoài thực tế, không bị
  cộng thêm độ dày border.
- Combobox chọn định dạng màu trong Gallery dùng trực tiếp `MonkezComboBox`, loại
  bỏ phần drop-down native bị lệch viền và khác kiểu với các control bên cạnh.
- `MonkezStatusBadge` vẽ trực tiếp nền alpha, viền và text bằng QPainter thay vì
  dựa vào clipping của Qt stylesheet. Radius được giới hạn theo kích thước thực,
  nên sáu theme đều giữ góc bo rõ ràng kể cả khi radius theme lớn hơn nửa chiều cao.

## Phạm vi đã kiểm tra

| Nhóm | Kết luận |
|---|---|
| Action/Input | Các hành vi chuẩn như checked, tri-state, editable, validator, clear button, echo mode và signals đã có từ Qt; package chỉ bổ sung theme, icon, popup và kích thước. |
| Value/Date-time | Range, step, format, orientation, keyboard và signals dùng API Qt chuẩn; các property hình học/màu riêng đã có trong Designer. |
| Display/Gauge | Table có workflow dữ liệu chuyên nghiệp; LCD và ba gauge có formatting, color role, threshold, target và orientation cần thiết. |
| Media | Image đã có Fit/Fill/Stretch/Original, file/Qt/NumPy frame; Camera đã có backend, source, resolution, FPS, mirror và reconnect. |
| Container/Startup | Frame, GroupBox và Splash đã có geometry, theme và runtime lifecycle cần thiết. ScrollArea tự theo dõi layout/widget con để bật tắt scrollbar AsNeeded. |

## Nguyên tắc tiếp tục phát triển

- Ưu tiên API chuyên biệt khi vai trò trực quan không rõ bằng tên chung.
- Tận dụng property/signal kế thừa của Qt thay vì tạo bản sao dễ lệch trạng thái.
- Mọi widget mới phải có runtime class, lazy export, Designer plugin/icon/task
  menu khi cần, Gallery docs/live preview, kiểm thử render và tài liệu người dùng.
- Nhóm feedback/navigation cần thiết đã có status badge, toast, loading
  indicator/overlay, range slider, segmented control, file picker và breadcrumb.
  Loading và Icon-only là hai chế độ của `MonkezButton`, không còn là hai loại
  widget riêng phải ghi nhớ. Slider value bubble và các composite chuyên ngành
  vẫn ở backlog.
