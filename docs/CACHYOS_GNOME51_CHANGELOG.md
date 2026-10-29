# MacTahoe CachyOS (GNOME 51+)

Bản fork tối ưu hóa và hoàn thiện bộ giao diện **MacTahoe CachyOS** cho các bản phân phối Linux hiện đại chạy **GNOME Shell 51+ (Mutter 51)** như **CachyOS**, **Arch Linux**, đồng thời bổ sung các tính năng tùy biến sâu, hỗ trợ đa màn hình và trình quản lý Clipboard tương tự Windows.

---

## 🚀 Các điểm cải tiến & tính năng mới

### 1. Hỗ trợ toàn diện CachyOS & Arch Linux (Rolling Release)
- **Hệ thống gói**: Hỗ trợ tự động nhận diện `pacman` và AUR helper (`yay`, `paru`).
- **User-space Fallback (Zero-sudo)**: Nếu không có quyền root (`sudo`), bộ cài tự động trích xuất các gói phụ thuộc (như `breeze-icons`, thư viện Python, fonts, extension schemas) vào thư mục người dùng (`~/.local/share`, `~/.local/lib/python3.14/site-packages`) để bộ giao diện hoạt động ngay lập tức mà không yêu cầu nhập mật khẩu root.

### 2. Khắc phục toàn bộ Breaking Changes trên GNOME Shell 51 (Mutter 51)
- **`pointerWatcher.js`**: GNOME 51 đã xóa bỏ `resource:///org/gnome/shell/ui/pointerWatcher.js`. Bản fork này bổ sung module `pointerWatcher.js` nội bộ sử dụng `global.backend.get_cursor_tracker()`.
- **`St.BoxLayout` orientation**: GNOME 51 loại bỏ thuộc tính `vertical: true/false`. Đã chuyển đổi toàn bộ sang `orientation: Clutter.Orientation.VERTICAL / HORIZONTAL` trên tất cả các extension.
- **Tọa độ con trỏ đa màn hình**: Trên GNOME 51, `meta_cursor_tracker_get_pointer` trả về kiểu `Graphene.Point { x, y }` thay vì mảng số. Đã cập nhật trích xuất tọa độ chính xác, tránh việc popup bị neo sai vào góc màn hình `(0, 0)`.
- **Loại bỏ `Clutter.get_default_backend()`**: Thay thế bằng `global.stage.context.get_backend().get_default_seat()` để lấy input device an toàn.
- **Biên dịch GSettings Schemas tự động**: Biên dịch tất cả schema vào `~/.local/share/glib-2.0/schemas/` và cập nhật biến môi trường cho `color-scheme-sync.service`.

### 3. Tùy biến Topbar linh hoạt & Giao diện Preferences Native
- **Trang cài đặt Native (Adw / GTK4)**: Bổ sung file `prefs.js` cho tiện ích `UbuntuTahoe`, cho phép bật/tắt các tùy chọn theo thời gian thực mà không cần sửa code.
- **Bật / tắt Global Menu**: Dễ dàng tắt cụm thanh menu Mac (File / Edit / View / Go) vốn ít hữu dụng trên các ứng dụng Linux.
- **Vị trí đồng hồ**: Tùy chọn đặt đồng hồ ở vị trí chính giữa (mặc định của GNOME) hoặc góc phải (kiểu macOS).
- **Ẩn cụm icon góc trái**: Tùy chọn ẩn hoàn toàn nút Activities / logo Apple trên thanh panel để thanh trên cùng thoáng và gọn gàng hơn.

### 4. Tối ưu hóa Đa màn hình (Multi-Monitor Support)
- **Desktop Widgets trên màn hình thứ 2**: Thêm tùy chọn `target-monitor` trong schema của `UbuntuTahoeWidgets`. Người dùng có thể chỉ định hiển thị các widget desktop (Đồng hồ, thời tiết, âm lịch, giám sát phần cứng) sang màn hình phụ (ví dụ: màn hình 2) thay vì chỉ cố định ở màn hình chính.
- **Dock đa màn hình**: Tích hợp tùy chọn `multi-monitor` hiển thị và quản lý dock thông minh trên nhiều màn hình.

### 5. Widget Thời tiết chính xác (Open-Meteo Geocoding)
- **Định vị tọa độ thực**: Thay vì chỉ đổi tên thành phố hiển thị trong khi tọa độ thực vẫn giữ nguyên, widget thời tiết đã được tích hợp **Open-Meteo Geocoding API** để tự động tra cứu tọa độ kinh độ/vĩ độ chính xác theo tên thành phố.
- **Preset 16 tỉnh thành lớn Việt Nam**: Tích hợp danh sách chọn nhanh các tỉnh thành phố phổ biến (Hà Nội, TP.HCM, Đà Nẵng, Hải Phòng, Cần Thơ, Nha Trang, Huế, v.v.).
- **Tìm kiếm thành phố toàn cầu**: Ô tìm kiếm trực tiếp trong trang Preferences cho phép tìm bất kỳ địa điểm nào trên thế giới.

### 6. Trình quản lý Clipboard tích hợp (Phím tắt Super + V)
- **Tích hợp sẵn tiện ích Clipboard Indicator** đã được vá tương thích 100% với GNOME Shell 51.
- **Phím tắt chuẩn Windows**: Mở nhanh danh sách lịch sử sao chép bằng tổ hợp <kbd>Super</kbd> + <kbd>V</kbd> (hệ thống tự động giải phóng phím này từ tray thông báo của GNOME).
- **Mở ngay tại vị trí chuột**: Bảng clipboard tự động hiển thị ngay dưới con trỏ chuột trên màn hình bạn đang làm việc.
- **Dán tự động (Paste on Select)**: Click hoặc ấn Enter vào một mục trong lịch sử sẽ tự động dán ngay vào ứng dụng đang thao tác.

---

## 📥 Hướng dẫn cài đặt trên CachyOS / Arch Linux

Chạy lệnh sau trên terminal để tải bản fork và cài đặt:

```bash
cd "$HOME" && \
git clone -b cachyos-support https://github.com/1440isme/mactahoe-cachyos.git mactahoe-cachyos && \
cd mactahoe-cachyos && \
./install.sh
```

Sau khi cài đặt xong, chỉ cần **Đăng xuất (Log Out) và Đăng nhập lại** để tận hưởng giao diện mới hoàn chỉnh!
