# MacTahoe cho CachyOS (Arch) + GNOME / Niri

Bản chuyển từ repo `adfoxtheme/mactahoe-ubuntu`. Các file gốc không bị sửa; bản này chỉ **thêm** 4 file.

## Cài đặt

Chép các file này vào thư mục gốc của repo (cùng cấp với `install.sh`):

```
install-cachyos.sh
uninstall-cachyos.sh
config/gsettings-cachyos.tsv
config/niri-mactahoe.kdl
```

Rồi chạy trong terminal của phiên GNOME, bằng tài khoản thường (không `sudo`):

```bash
cd ~/mactahoe-ubuntu
bash install-cachyos.sh
```

Tùy chọn: `--skip-packages` (tự cài gói trước), `--no-firefox`, `--keep-favorites` (giữ nguyên app ghim trên dock).
Xong thì đăng xuất rồi đăng nhập lại.

Gỡ cài đặt: `bash uninstall-cachyos.sh`.

## Khác gì so với bản Ubuntu

| Bản Ubuntu | Bản CachyOS |
|---|---|
| `apt-get`, gói `gir1.2-*`, `conky-all`, `python3-pil`... | `pacman`: `libadwaita`, `gtk4`, `conky`, `python-gobject`, `python-pillow`... (gói nào không có trong kho sẽ được báo và bỏ qua) |
| Chỉ chạy khi `ID=ubuntu` | Chấp nhận `cachyos` hoặc distro có `ID_LIKE=arch` |
| Danh sách app ghim có ID của snap/Ubuntu | Chỉ ghim những app thực sự có trên máy |
| Tự `pkill -KILL` Firefox | Yêu cầu bạn đóng Firefox (không giết tiến trình) |
| Tìm profile Firefox ở đường dẫn snap/`~/.mozilla` | Thêm `~/.config/mozilla/firefox` và Flatpak |
| `install-gdm.sh` thay resource Yaru | **Bỏ hẳn**, không đụng màn hình đăng nhập |
| Theo dõi gói đã cài bằng `dpkg` | Bỏ; chỉ sao lưu file cấu hình và `dconf` |

## Lưu ý

- **Niri:** theme GTK, icon, font, chế độ sáng/tối dùng chung với Niri. Dock, global menu và blur là extension GNOME Shell nên chỉ có trong phiên GNOME. Gợi ý cursor/bo góc cho Niri nằm trong `config/niri-mactahoe.kdl`; script không tự sửa config Niri của bạn.
- **Widget Conky** dùng X11 (`cairo_xlib`), chạy qua XWayland. Trong Niri cần `xwayland-satellite`.
- Dịch vụ `color-scheme-sync` bật ở mức `default.target` nên cũng chạy trong phiên Niri; vô hại, nhưng có thể tắt bằng `systemctl --user disable --now color-scheme-sync`.
- Vị trí thời tiết mặc định trong `config/weather.conf` là Quy Nhơn; đổi trong ứng dụng Widget MacTahoe.
- Font SF Pro đi kèm repo gốc: kiểm tra giấy phép trước khi phân phối lại.
- Script **chưa được chạy thử trên máy CachyOS thật** (chỉ kiểm tra cú pháp). Lần đầu nên đọc qua và để ý thông báo "Cảnh báo".
