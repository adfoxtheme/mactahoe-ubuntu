# Quản lý icon MacTahoe (MacTahoe Icon Manager)

Ứng dụng GTK4/Adw để đổi icon MacTahoe chuẩn phong cách macOS cho các ứng dụng đã cài đặt trên hệ thống (App hệ thống, Snap, Flatpak, App người dùng).

## Chức năng

- Tự động quét và liệt kê các ứng dụng có trong hệ thống (`/usr/share/applications`, Flatpak, Snap và `~/.local/share/applications`).
- Thay thế icon ứng dụng sang icon MacTahoe tương ứng.
- Tự động sao lưu (backup) icon gốc trước khi thay thế vào `~/.local/share/mactahoe-icon-manager/backups/`.
- Có nút **Khôi phục** để hoàn tác lại icon mặc định bất cứ lúc nào.
- Hỗ trợ chế độ kiểm tra dữ liệu không cần mở giao diện: `mactahoe-icon-manager --self-test`.

## Chạy ứng dụng

```bash
cd "$HOME/mactahoe-ubuntu/apps/mactahoe-icon-manager"
python3 main.py
```

Hoặc bấm biểu tượng **Quản lý icon MacTahoe** trong menu ứng dụng GNOME. Lệnh đã cài:

```bash
mactahoe-icon-manager
```
