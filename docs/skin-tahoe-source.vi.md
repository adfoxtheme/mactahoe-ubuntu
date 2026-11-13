# Vietnamese reference: MacTahoe setup notes for Ubuntu 26.04

> File này ghi lại **đúng** cấu hình đang dùng trên máy, để cài lại Ubuntu chỉ cần làm theo từ trên xuống.
>
> **Đã kiểm chứng trên:**
> - Ubuntu **26.04.1 LTS**
> - GNOME Shell **50.1**, session **Wayland**
> - MacTahoe-gtk-theme commit `1e45e19` (2026-09-28)
> - MacTahoe-icon-theme commit `839848b9` (2026-09-10)
> - Ngày chốt cấu hình: **20/10/2026**
>
> **Kết quả cuối:** GTK + Shell theme `MacTahoe-Dark`, icon `MacTahoe-blue`, cursor `MacTahoe-cursors`, font `SF Pro Display 11`, dock dưới nền tối `#1f1f24`, wallpaper `MacTahoe-night.jpeg`, Firefox snap có theme Tahoe, GDM (màn hình đăng nhập) cũng theme Tahoe.

---

## 0. Chuẩn bị

- Ubuntu 26.04 (GNOME 50), tài khoản có quyền `sudo`, có internet.
- Nên đóng Firefox/Chrome trước khi làm.
- Kiểm tra phiên bản:

```bash
lsb_release -ds
gnome-shell --version
echo "$XDG_SESSION_TYPE"
```

Kết quả đúng phải tương tự:

```text
Ubuntu 26.04.1 LTS
GNOME Shell 50.1
wayland
```

- Backup cấu hình GNOME hiện tại (để lỡ có gì còn restore):

```bash
mkdir -p ~/mac-tahoe-backup
dconf dump / > ~/mac-tahoe-backup/dconf-truoc-khi-theme.txt
```

> Nếu sau này muốn restore: `dconf load / < ~/mac-tahoe-backup/dconf-truoc-khi-theme.txt`

---

## 1. Cài gói phụ thuộc

```bash
sudo apt update
sudo apt install -y \
  git curl unzip \
  sassc libglib2.0-dev-bin imagemagick \
  gnome-tweaks gnome-shell-extension-user-theme dconf-cli \
  breeze-icon-theme
```

Giải thích:

| Gói | Dùng để |
|---|---|
| `git` | clone theme |
| `curl`, `unzip` | tải và giải nén font |
| `sassc` | biên dịch SCSS của theme |
| `libglib2.0-dev-bin` | có `glib-compile-resources`, cần cho GDM |
| `imagemagick` | làm tối/blur ảnh nền GDM |
| `gnome-tweaks` | chỉnh nhanh bằng GUI (không bắt buộc) |
| `gnome-shell-extension-user-theme` | extension `user-theme` để đổi shell theme |
| `dconf-cli` | backup/restore `dconf` |
| `breeze-icon-theme` | theme `MacTahoe-blue` kế thừa icon `breeze`, thiếu sẽ fallback về `hicolor` |

---

## 2. Tải theme

```bash
mkdir -p ~/mac-tahoe
cd ~/mac-tahoe

git clone https://github.com/vinceliuice/MacTahoe-gtk-theme.git
git clone https://github.com/vinceliuice/MacTahoe-icon-theme.git
```

Nếu muốn khớp **chính xác** bản đang dùng (khuyến nghị):

```bash
git -C ~/mac-tahoe/MacTahoe-gtk-theme checkout 1e45e19
git -C ~/mac-tahoe/MacTahoe-icon-theme checkout 839848b9
```

---

## 3. Cài font SF Pro / SF Mono

Theme dùng font Apple: `SF Pro Display`, `SF Pro Text`, `SF Mono`.

```bash
curl -L https://github.com/clickamplify/San-Francisco-Pro-Font/archive/refs/heads/main.zip \
  -o /tmp/sf-pro.zip

unzip -o /tmp/sf-pro.zip -d /tmp

sudo mkdir -p /usr/local/share/fonts/apple
sudo cp -r /tmp/San-Francisco-Pro-Font-main/. /usr/local/share/fonts/apple/
sudo fc-cache -f
```

Kiểm tra:

```bash
fc-list | grep -i 'SF Pro Display' | head -3
fc-list | grep -i 'SF Mono' | head -3
```

Phải thấy ít nhất một dòng `SF Pro Display` và một dòng `SF Mono`.

> Nếu archive tải về có cấu trúc thư mục khác, chỉ cần copy các thư mục con như `SF-Pro`, `SF-Mono`, `NewYork`, `SF-Compact`… vào `/usr/local/share/fonts/apple/`.
>
> Font Apple có bản quyền — chỉ dùng cho mục đích cá nhân.

---

## 4. Cài GTK theme + GNOME Shell theme

```bash
cd ~/mac-tahoe/MacTahoe-gtk-theme
./install.sh -l --shell -i apple
```

Giải thích tham số:

| Tham số | Ý nghĩa |
|---|---|
| `-l` / `--libadwaita` | cài thêm GTK4/libadwaita vào `~/.config/gtk-4.0` — **bắt buộc** để app GNOME 50 (Settings, Files, Software…) có theme |
| `--shell` | cài GNOME Shell theme (thanh top bar, overview, quick settings…) |
| `-i apple` | icon "Activities" trên panel thành logo Apple |

Kết quả:

```text
~/.themes/MacTahoe-Dark
~/.themes/MacTahoe-Light
~/.themes/MacTahoe-Dark-solid
~/.themes/MacTahoe-Light-solid
~/.themes/MacTahoe-Dark-hdpi
...
~/.config/gtk-4.0/gtk.css       -> gtk-Dark.css
~/.config/gtk-4.0/gtk-dark.css  -> gtk-Dark.css
~/.config/gtk-4.0/gtk-Dark.css
~/.config/gtk-4.0/gtk-Light.css
```

> **Chạy bằng user thường, KHÔNG dùng `sudo`.** Script sẽ báo lỗi nếu chạy `sudo` ở bước libadwaita.

---

## 5. Cài icon + cursor

```bash
cd ~/mac-tahoe/MacTahoe-icon-theme
./install.sh -t blue
```

- `-t blue` tạo bộ icon `MacTahoe-blue` và các bộ cursor `MacTahoe-cursors`, `MacTahoe-dark-cursors`, `MacTahoe-light-cursors`.
- Cài vào `~/.local/share/icons`, không cần `sudo`.

Kiểm tra:

```bash
ls ~/.local/share/icons | grep MacTahoe
```

Phải thấy ít nhất:

```text
MacTahoe-blue
MacTahoe-cursors
```

---

## 6. Copy wallpaper

```bash
mkdir -p ~/Pictures/Wallpapers/MacTahoe
cp ~/mac-tahoe/MacTahoe-gtk-theme/wallpaper/MacTahoe-*.jpeg \
   ~/Pictures/Wallpapers/MacTahoe/

ls -l ~/Pictures/Wallpapers/MacTahoe/
```

Phải có:

```text
MacTahoe-day.jpeg
MacTahoe-night.jpeg
```

---

## 7. Bật shell theme + set giao diện

```bash
# Bật extension đổi shell theme
gnome-extensions enable user-theme@gnome-shell-extensions.gcampax.github.com

# Shell theme (thanh top bar, overview...)
gsettings set org.gnome.shell.extensions.user-theme name 'MacTahoe-Dark'

# GTK theme + icon + cursor
gsettings set org.gnome.desktop.interface gtk-theme 'MacTahoe-Dark'
gsettings set org.gnome.desktop.interface icon-theme 'MacTahoe-blue'
gsettings set org.gnome.desktop.interface cursor-theme 'MacTahoe-cursors'
gsettings set org.gnome.desktop.interface cursor-size 24

# Chế độ tối + màu nhấn
gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark'
gsettings set org.gnome.desktop.interface accent-color 'green'

# Font
gsettings set org.gnome.desktop.interface font-name 'SF Pro Display 11'
gsettings set org.gnome.desktop.interface document-font-name 'SF Pro Text 11'
gsettings set org.gnome.desktop.interface monospace-font-name 'SF Mono 11'
gsettings set org.gnome.desktop.interface font-antialiasing 'rgba'
gsettings set org.gnome.desktop.interface font-hinting 'medium'

# Titlebar + nút cửa sổ kiểu macOS (đóng bên trái)
gsettings set org.gnome.desktop.wm.preferences titlebar-font 'SF Pro Display Bold 11'
gsettings set org.gnome.desktop.wm.preferences button-layout 'close,minimize,maximize:'
```

> Nếu `gnome-extensions enable` báo không tìm thấy extension: logout/login rồi chạy lại, hoặc kiểm tra gói `gnome-shell-extension-user-theme` đã cài chưa.

### 7.1. Đưa đồng hồ topbar sang phải (kiểu macOS)

Dùng extension **Just Perfection** (bản 37 hỗ trợ GNOME 50):

```bash
# Cài từ extensions.gnome.org, sau đó:
gnome-extensions enable just-perfection-desktop@just-perfection

# 0 = giữa, 1 = phải, 2 = trái
EXT="$HOME/.local/share/gnome-shell/extensions/just-perfection-desktop@just-perfection"
GSETTINGS_SCHEMA_DIR="$EXT/schemas" \
  gsettings set org.gnome.shell.extensions.just-perfection clock-menu-position 1
# 20 = đẩy sát mép phải; 0 = đầu nhóm bên phải
GSETTINGS_SCHEMA_DIR="$EXT/schemas" \
  gsettings set org.gnome.shell.extensions.just-perfection clock-menu-position-offset 20
```

Nếu vừa cài extension mà `gnome-extensions list` chưa thấy, logout/login một lần rồi bật lại. Có thể chỉnh trực tiếp trong **Extension Manager → Just Perfection → Clock → Position → Right**.

---

## 8. Wallpaper desktop + màn hình khóa

```bash
WALL="$HOME/Pictures/Wallpapers/MacTahoe/MacTahoe-night.jpeg"

gsettings set org.gnome.desktop.background picture-uri "file://$WALL"
gsettings set org.gnome.desktop.background picture-uri-dark "file://$WALL"
gsettings set org.gnome.desktop.background picture-options 'zoom'

gsettings set org.gnome.desktop.screensaver picture-uri "file://$WALL"
gsettings set org.gnome.desktop.screensaver picture-options 'zoom'
```

- `MacTahoe-night.jpeg` cho chế độ tối (đang dùng).
- Nếu muốn chế độ sáng dùng ảnh ngày: đổi `picture-uri` thành `MacTahoe-day.jpeg`.
- Màn hình khóa dùng chung ảnh với desktop.

---

## 9. Dock dưới (Ubuntu Dock / dash-to-dock)

Ubuntu dùng extension `ubuntu-dock@ubuntu.com`, nhưng schema cấu hình vẫn là `org.gnome.shell.extensions.dash-to-dock`.

```bash
D=org.gnome.shell.extensions.dash-to-dock

# Vị trí + hành vi
gsettings set $D dock-position 'BOTTOM'
gsettings set $D extend-height false
gsettings set $D dock-fixed false
gsettings set $D autohide true
gsettings set $D autohide-in-fullscreen true
gsettings set $D intellihide true
gsettings set $D intellihide-mode 'ALL_WINDOWS'
gsettings set $D always-center-icons true
gsettings set $D click-action 'minimize-or-previews'
gsettings set $D show-trash true
gsettings set $D show-mounts false
gsettings set $D show-mounts-network false

# Kích thước + animation
gsettings set $D dash-max-icon-size 48
gsettings set $D icon-size-fixed false
gsettings set $D running-indicator-style 'DOTS'
gsettings set $D animation-time 0.2
gsettings set $D show-delay 0.1
gsettings set $D hide-delay 0.1
gsettings set $D pressure-threshold 100.0
gsettings set $D require-pressure-to-show false
gsettings set $D max-alpha 0.85
gsettings set $D min-alpha 0.15
gsettings set $D custom-theme-shrink false

# Nền tối cố định — đây là mẹo để dock không bị kính trắng của theme
gsettings set $D transparency-mode 'FIXED'
gsettings set $D background-opacity 0.45
gsettings set $D custom-background-color true
gsettings set $D background-color '#1f1f24'
gsettings set $D apply-custom-theme false
```

> **Quan trọng:** `apply-custom-theme false` + `custom-background-color true` + `transparency-mode 'FIXED'` là bộ 3 quyết định dock tối. Nếu dock bị trắng/kính, kiểm tra lại 3 dòng này trước.

---

## 10. Đồng bộ sáng/tối tự động

GNOME có công tắc Sáng/Tối trong **Settings → Appearance**. Script dưới đây giữ GTK theme, shell theme và cờ dark cho Chrome/GTK apps đồng bộ theo công tắc đó.

### 10.1. Tạo script

```bash
mkdir -p ~/.local/bin

cat > ~/.local/bin/color-scheme-sync.sh <<'SCRIPT'
#!/usr/bin/env bash
# Giữ GTK theme + GNOME Shell theme + cờ prefer-dark đồng bộ với chế độ Sáng/Tối của GNOME
set -u

write_ini() {
    local file="$1" prefer="$2"
    mkdir -p "$(dirname "$file")"
    if [ -f "$file" ]; then
        grep -v '^gtk-application-prefer-dark-theme' "$file" > "$file.tmp" || true
        mv "$file.tmp" "$file"
    else
        printf '[Settings]\n' > "$file"
    fi
    printf 'gtk-application-prefer-dark-theme=%s\n' "$prefer" >> "$file"
}

apply() {
    local scheme variant prefer
    scheme=$(gsettings get org.gnome.desktop.interface color-scheme 2>/dev/null)
    if [ "$scheme" = "'prefer-dark'" ]; then
        variant="Dark"
        prefer="1"
    else
        variant="Light"
        prefer="0"
    fi

    if [ "$(gsettings get org.gnome.desktop.interface gtk-theme)" != "'MacTahoe-$variant'" ]; then
        gsettings set org.gnome.desktop.interface gtk-theme "MacTahoe-$variant"
    fi

    if [ "$(gsettings get org.gnome.shell.extensions.user-theme name)" != "'MacTahoe-$variant'" ]; then
        gsettings set org.gnome.shell.extensions.user-theme name "MacTahoe-$variant"
    fi

    # Chrome / app GTK đọc cờ này để biết đang dark hay light
    write_ini "$HOME/.config/gtk-3.0/settings.ini" "$prefer"
    write_ini "$HOME/.config/gtk-4.0/settings.ini" "$prefer"
}

apply
gsettings monitor org.gnome.desktop.interface color-scheme | while read -r _; do
    apply
done
SCRIPT

chmod +x ~/.local/bin/color-scheme-sync.sh
```

### 10.2. Tạo service chạy nền

```bash
mkdir -p ~/.config/systemd/user

cat > ~/.config/systemd/user/color-scheme-sync.service <<'SERVICE'
[Unit]
Description=Sync GTK/Shell theme with GNOME color-scheme

[Service]
Type=simple
ExecStart=%h/.local/bin/color-scheme-sync.sh
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
SERVICE

systemctl --user daemon-reload
systemctl --user enable --now color-scheme-sync.service
```

### 10.3. Kiểm tra + đổi sáng/tối

```bash
systemctl --user is-active color-scheme-sync.service
```

Phải trả về `active`.

Đổi thử:

```bash
# Tối
gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark'

# Sáng
gsettings set org.gnome.desktop.interface color-scheme 'default'
```

Sau vài giây, `gtk-theme` và shell theme phải tự đổi giữa `MacTahoe-Dark` và `MacTahoe-Light`.

> **Lưu ý:** Script hiện tại không đổi symlink `~/.config/gtk-4.0/gtk.css` (đang trỏ cố định `gtk-Dark.css`), nên app GTK4/libadwaita có thể vẫn tối khi chọn chế độ sáng. Nếu muốn GTK4 cũng đổi, thêm dòng này vào trong hàm `apply()` (sau khi set `variant`):
>
> ```bash
> ln -sf "$HOME/.config/gtk-4.0/gtk-$variant.css" "$HOME/.config/gtk-4.0/gtk.css"
> ```
>
> Cấu hình hiện tại **không bật** dòng này — đúng với trạng thái máy đang dùng.

---

## 11. Theme cho Firefox (snap)

> Firefox phải **tắt hoàn toàn** trước khi copy.

### 11.1. Tìm profile Firefox snap

```bash
PROFILE=$(find "$HOME/snap/firefox/common/.mozilla/firefox" \
  -maxdepth 1 -type d -name '*.default*' | head -n1)

echo "$PROFILE"
```

Kết quả dạng:

```text
$HOME/snap/firefox/common/.mozilla/firefox/<profile>
```

> Nếu dùng Firefox bản `.deb` thay vì snap, đổi đường dẫn tìm thành `"$HOME/.mozilla/firefox"`.

### 11.2. Copy theme

```bash
rm -rf "$PROFILE/chrome/MacTahoe"
mkdir -p "$PROFILE/chrome"

cp -r ~/mac-tahoe/MacTahoe-gtk-theme/other/firefox/MacTahoe \
      "$PROFILE/chrome/"

cp ~/mac-tahoe/MacTahoe-gtk-theme/other/firefox/customChrome.css \
   ~/mac-tahoe/MacTahoe-gtk-theme/other/firefox/userChrome.css \
   ~/mac-tahoe/MacTahoe-gtk-theme/other/firefox/userContent.css \
      "$PROFILE/chrome/"
```

### 11.3. Tạo `user.js`

```bash
[ -f "$PROFILE/user.js" ] && cp "$PROFILE/user.js" "$PROFILE/user.js.bak"

cat > "$PROFILE/user.js" <<'EOF'
user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);
user_pref("browser.tabs.drawInTitlebar", true);
user_pref("browser.uidensity", 0);
user_pref("layers.acceleration.force-enabled", true);
user_pref("mozilla.widget.use-argb-visuals", true);
user_pref("widget.gtk.rounded-bottom-corners.enabled", true);
user_pref("svg.context-properties.content.enabled", true);
EOF
```

Mở Firefox lại. Kiểm tra trong `about:config`:

```text
toolkit.legacyUserProfileCustomizations.stylesheets = true
```

> Nếu theme không lên: kiểm tra đúng profile (Firefox `about:profiles`), đúng thư mục `chrome/`, và đã khởi động lại Firefox chưa.

---

## 12. Theme cho GDM (màn hình đăng nhập)

> Bước này cần `sudo` (hoặc `pkexec`) và **phải reboot** mới thấy.

### 12.1. Backup file gốc

```bash
sudo cp -n \
  /usr/share/gnome-shell/theme/Yaru/gnome-shell-theme.gresource \
  /usr/share/gnome-shell/theme/Yaru/gnome-shell-theme.gresource.bak
```

`-n` = không ghi đè nếu backup đã tồn tại.

### 12.2. Cài theme GDM

```bash
cd ~/mac-tahoe/MacTahoe-gtk-theme

sudo ./tweaks.sh -g -i apple \
  -b "$HOME/Pictures/Wallpapers/MacTahoe/MacTahoe-night.jpeg"
```

Giải thích:

| Tham số | Ý nghĩa |
|---|---|
| `-g` | theme cho GDM |
| `-i apple` | icon Activities thành logo Apple |
| `-b <ảnh>` | ảnh nền màn hình đăng nhập |

Nếu không muốn gõ `sudo` trong terminal, dùng `pkexec` (dùng đường dẫn tuyệt đối cho chắc):

```bash
pkexec env DISPLAY="$DISPLAY" XAUTHORITY="$XAUTHORITY" \
  "$HOME/mac-tahoe/MacTahoe-gtk-theme/tweaks.sh" -g -i apple \
  -b "$HOME/Pictures/Wallpapers/MacTahoe/MacTahoe-night.jpeg"
```

Sau đó **reboot**:

```bash
sudo reboot
```

### 12.3. Revert GDM

```bash
cd ~/mac-tahoe/MacTahoe-gtk-theme
sudo ./tweaks.sh -g -r
```

Hoặc copy lại backup:

```bash
sudo cp \
  /usr/share/gnome-shell/theme/Yaru/gnome-shell-theme.gresource.bak \
  /usr/share/gnome-shell/theme/Yaru/gnome-shell-theme.gresource
```

> Trên Ubuntu 26.04 file gốc nằm ở `theme/Yaru/`. Nếu bản Ubuntu khác không có thư mục này, tìm bằng:
>
> ```bash
> find /usr/share/gnome-shell -name 'gnome-shell-theme.gresource'
> ```

---

## 13. Logout / login + reboot

- **Shell theme** và extension `user-theme`: cần **logout/login** (Wayland không restart shell tại chỗ).
- **GDM**: cần **reboot**.
- Firefox: tắt hẳn rồi mở lại.

---

## 14. Checklist kiểm tra sau khi làm

```bash
gsettings get org.gnome.desktop.interface gtk-theme
gsettings get org.gnome.desktop.interface icon-theme
gsettings get org.gnome.desktop.interface cursor-theme
gsettings get org.gnome.desktop.interface color-scheme
gsettings get org.gnome.desktop.interface accent-color
gsettings get org.gnome.desktop.interface font-name
gsettings get org.gnome.shell.extensions.user-theme name
gsettings get org.gnome.shell.extensions.dash-to-dock background-color
gsettings get org.gnome.shell.extensions.dash-to-dock apply-custom-theme
```

Giá trị đúng:

| Lệnh | Kết quả |
|---|---|
| `gtk-theme` | `'MacTahoe-Dark'` |
| `icon-theme` | `'MacTahoe-blue'` |
| `cursor-theme` | `'MacTahoe-cursors'` |
| `color-scheme` | `'prefer-dark'` |
| `accent-color` | `'green'` |
| `font-name` | `'SF Pro Display 11'` |
| `user-theme name` | `'MacTahoe-Dark'` |
| `background-color` | `'#1f1f24'` |
| `apply-custom-theme` | `false` |

Kiểm tra thêm:

```bash
gnome-extensions list --enabled | grep user-theme
ls ~/.themes | grep MacTahoe
ls ~/.local/share/icons | grep MacTahoe
fc-list | grep -i 'SF Pro Display' | head -1
systemctl --user is-active color-scheme-sync.service
```

---

## 15. Gỡ / revert toàn bộ

### 15.1. Gỡ theme

```bash
cd ~/mac-tahoe/MacTahoe-gtk-theme
./install.sh -r

cd ~/mac-tahoe/MacTahoe-icon-theme
./install.sh -r
```

### 15.2. Gỡ GDM theme

```bash
cd ~/mac-tahoe/MacTahoe-gtk-theme
sudo ./tweaks.sh -g -r
```

### 15.3. Reset gsettings

```bash
gsettings reset org.gnome.desktop.interface gtk-theme
gsettings reset org.gnome.desktop.interface icon-theme
gsettings reset org.gnome.desktop.interface cursor-theme
gsettings reset org.gnome.desktop.interface cursor-size
gsettings reset org.gnome.desktop.interface color-scheme
gsettings reset org.gnome.desktop.interface accent-color
gsettings reset org.gnome.desktop.interface font-name
gsettings reset org.gnome.desktop.interface document-font-name
gsettings reset org.gnome.desktop.interface monospace-font-name
gsettings reset org.gnome.desktop.interface font-antialiasing
gsettings reset org.gnome.desktop.interface font-hinting
gsettings reset org.gnome.desktop.wm.preferences titlebar-font
gsettings reset org.gnome.desktop.wm.preferences button-layout
gsettings reset org.gnome.shell.extensions.user-theme name
dconf reset -f /org/gnome/shell/extensions/dash-to-dock/
```

### 15.4. Gỡ script đồng bộ

```bash
systemctl --user disable --now color-scheme-sync.service
rm -f ~/.local/bin/color-scheme-sync.sh
rm -f ~/.config/systemd/user/color-scheme-sync.service
systemctl --user daemon-reload
```

### 15.5. Gỡ font + wallpaper (tuỳ chọn)

```bash
sudo rm -rf /usr/local/share/fonts/apple
sudo fc-cache -f

rm -rf ~/Pictures/Wallpapers/MacTahoe
```

### 15.6. Gỡ theme Firefox (tuỳ chọn)

```bash
PROFILE=$(find "$HOME/snap/firefox/common/.mozilla/firefox" \
  -maxdepth 1 -type d -name '*.default*' | head -n1)

rm -rf "$PROFILE/chrome/MacTahoe"
rm -f "$PROFILE/chrome/customChrome.css" \
      "$PROFILE/chrome/userChrome.css" \
      "$PROFILE/chrome/userContent.css"
# user.js: xoá hoặc khôi phục từ user.js.bak
[ -f "$PROFILE/user.js.bak" ] && mv "$PROFILE/user.js.bak" "$PROFILE/user.js"
```

---

## 16. Lỗi thường gặp

| Hiện tượng | Cách xử lý |
|---|---|
| Shell theme không đổi | `gnome-extensions enable user-theme@gnome-shell-extensions.gcampax.github.com`; logout/login; kiểm tra `gnome-extensions info user-theme@...` |
| App GNOME (Settings, Files) không theme | Chạy lại `./install.sh -l` bằng user thường (không `sudo`); kiểm tra `~/.config/gtk-4.0/gtk.css` có tồn tại; tắt/mở lại app |
| Dock trắng/kính | Kiểm tra `apply-custom-theme false`, `custom-background-color true`, `transparency-mode 'FIXED'`, `background-color '#1f1f24'`; logout/login |
| Icon không đổi | `ls ~/.local/share/icons/MacTahoe-blue/index.theme`; `gtk-update-icon-cache ~/.local/share/icons/MacTahoe-blue`; logout/login |
| Firefox không theme | Đúng profile chưa; `toolkit.legacyUserProfileCustomizations.stylesheets=true`; đã tắt hẳn Firefox trước khi copy |
| GDM không đổi | Phải reboot; kiểm tra file `gnome-shell-theme.gresource` có mtime mới; xem lại `.bak` |
| Update GNOME xong GDM mất theme | Chạy lại bước 12.2 (`tweaks.sh -g ...`) rồi reboot |
| Font không hiện | `sudo fc-cache -f`; `fc-list \| grep -i 'SF Pro'`; kiểm tra đúng thư mục `/usr/local/share/fonts/apple` |
| Sáng/tối không đồng bộ | `systemctl --user status color-scheme-sync.service`; chạy tay `~/.local/bin/color-scheme-sync.sh` xem lỗi |
| `sassc: command not found` | `sudo apt install sassc` |
| `glib-compile-resources: command not found` | `sudo apt install libglib2.0-dev-bin` |
| GDM báo thiếu `convert`/`magick` | `sudo apt install imagemagick` |
| `install.sh` báo không được chạy `sudo` | Chạy lại bằng user thường (chỉ `tweaks.sh -g` mới cần `sudo`) |

---

## 17. Nguồn tham khảo

- MacTahoe GTK theme: <https://github.com/vinceliuice/MacTahoe-gtk-theme>
- MacTahoe Icon theme: <https://github.com/vinceliuice/MacTahoe-icon-theme>
- Font SF Pro (bản cộng đồng): <https://github.com/clickamplify/San-Francisco-Pro-Font>
- Ubuntu 26.04.1 LTS, GNOME Shell 50.1, Wayland.

---

## 18. Tóm tắt cấu hình đang dùng (để đối chiếu)

```text
OS            : Ubuntu 26.04.1 LTS
Desktop       : GNOME Shell 50.1 (Wayland)
GTK theme     : MacTahoe-Dark
Shell theme   : MacTahoe-Dark
Icon theme    : MacTahoe-blue
Cursor        : MacTahoe-cursors (size 24)
Color scheme  : prefer-dark
Accent color  : green
Font          : SF Pro Display 11 / SF Pro Text 11 / SF Mono 11
Titlebar font : SF Pro Display Bold 11
Window buttons: close,minimize,maximize:
Wallpaper     : MacTahoe-night.jpeg (desktop + lock screen)
Dock          : bottom, autohide, fixed dark #1f1f24, opacity 0.45
Firefox       : snap profile + MacTahoe chrome theme
GDM           : MacTahoe + Apple icon + MacTahoe-night background
Sync service  : color-scheme-sync.service (user)
```

---

## 19. MacTahoe Icon Manager (app tự viết)

App GTK4/Adw để đổi icon MacTahoe cho ứng dụng hệ thống, snap, flatpak và app local.

- Script: `~/.local/bin/mactahoe-icon-manager`
- Launcher: `~/.local/share/applications/mactahoe-icon-manager.desktop`
- Mở từ menu ứng dụng **Quản lý icon MacTahoe**, hoặc chạy:

```bash
mactahoe-icon-manager
```

- Kiểm tra dữ liệu (không mở cửa sổ):

```bash
mactahoe-icon-manager --self-test
```

- Cách dùng: chọn app bên trái → chọn icon MacTahoe bên phải → **Áp dụng**. Dòng **Đang sửa:** ở cột phải cho biết app nào sẽ bị đổi.
- Ghi đè được lưu ở `~/.local/share/applications/` (không sửa file hệ thống, không cần sudo).
- Icon đã chọn được copy vào `~/.local/share/mactahoe-icon-manager/icons/` để update/đổi theme không làm hỏng đường dẫn.
- Backup icon gốc ở `~/.local/share/mactahoe-icon-manager/backups/`; nút **Khôi phục** trả lại icon cũ.
- Nếu icon chưa cập nhật ngay: logout/login (Wayland không dùng được Alt+F2 → `r`), hoặc bỏ ghim rồi ghim lại app vào dock.
- Phụ thuộc: `python3-gi`, `gir1.2-gtk-4.0`, `gir1.2-adw-1` (Ubuntu GNOME có sẵn).

---

## 20. Widget Conky kiểu macOS (thời tiết + hệ thống + âm lịch)

Ba widget nền trong suốt, góc bo tròn, font SF Pro, gồm thời tiết, thông tin hệ thống và âm lịch. Widget được mở bằng launcher **Widget MacTahoe**.

### 20.1. Thành phần

| Thành phần | Đường dẫn |
|---|---|
| Cấu hình thời tiết | `~/.config/conky/mactahoe-weather.conf` |
| Cấu hình hệ thống | `~/.config/conky/mactahoe-system.conf` |
| Cấu hình âm lịch | `~/.config/conky/mactahoe-lunar.conf` |
| Phần vẽ Cairo/Lua | `~/.config/conky/mactahoe-widgets.lua` |
| Script lấy thời tiết | `~/.local/bin/mactahoe-weather-fetch.py` |
| Script lấy ngày âm lịch | `~/.local/bin/mactahoe-lunar-fetch.py` |
| Bật/tắt widget | `~/.local/bin/mactahoe-widgets` |
| Cấu hình vị trí thời tiết | `~/.config/mactahoe-widgets/weather.conf` |
| Cache thời tiết + âm lịch | `~/.cache/mactahoe-widgets/` |
| Launcher bật lại widget | `~/.local/share/applications/mactahoe-widgets.desktop` |

> Launcher **Conky mặc định** (`conky.desktop`) đã bị vô hiệu bằng file override `~/.local/share/applications/conky.desktop` (`Hidden=true`, `NoDisplay=true`); bản gốc được giữ ở `~/.local/share/applications-disabled/`. Mục đích là tránh bấm nhầm mở widget đen từ `/etc/conky/conky.conf`. Muốn dùng widget MacTahoe thì bấm launcher **Widget MacTahoe** hoặc chạy `mactahoe-widgets restart`.

### 20.2. Cài / chạy

```bash
# Kiểm tra Conky có Cairo + Imlib2 + RSVG
conky --version | grep -E 'Cairo|Imlib2|RSVG|Wayland'

# Lấy thời tiết lần đầu
~/.local/bin/mactahoe-weather-fetch.py --force

# Lấy ngày âm lịch hôm nay
~/.local/bin/mactahoe-lunar-fetch.py

# Bật cả ba widget
~/.local/bin/mactahoe-widgets start

# Xem trạng thái
~/.local/bin/mactahoe-widgets status

# Tắt / khởi động lại
~/.local/bin/mactahoe-widgets stop
~/.local/bin/mactahoe-widgets restart
```

Nếu vừa sửa file Lua, chạy `mactahoe-widgets restart`.

### 20.3. Đổi vị trí

Sửa trong file `.conf`:

- `alignment = 'top_right'`
- `gap_x = 24` — mép phải của card cách màn hình 30px (Conky có thêm viền trong suốt)
- `gap_y = 80` — widget thời tiết cách mép trên (chừa chỗ cho topbar), giữ nguyên
- `gap_y = 310` — widget hệ thống nằm dưới widget thời tiết, cách card thời tiết 30px
- `gap_y = 630` — widget âm lịch nằm dưới widget hệ thống, cách card hệ thống 30px; cao 150px (một nửa widget hệ thống)

Muốn đổi sang trái: `alignment = 'top_left'`. Muốn đổi thứ tự ba widget: hoán đổi `gap_y`.

### 20.4. Đổi vị trí thời tiết

Sửa `~/.config/mactahoe-widgets/weather.conf`:

```ini
LAT=13.7820
LON=109.2190
CITY=Quy Nhơn
TIMEZONE=Asia/Ho_Chi_Minh
ICON_THEME=/home/<username>/.local/share/icons/MacTahoe-blue/status/32
```

Sau đó:

```bash
~/.local/bin/mactahoe-weather-fetch.py --force
~/.local/bin/mactahoe-widgets restart
```

Dữ liệu lấy từ Open-Meteo, không cần API key, tự cập nhật mỗi 10 phút. Nếu mất mạng, widget giữ dữ liệu cũ.

### 20.5. Widget hệ thống

Hiển thị:

- CPU: % + nhiệt độ CPU từ `/sys/class/thermal/thermal_zone0/temp`
- GPU: % + VRAM + nhiệt độ qua `nvidia-smi`
- RAM: % + đã dùng/tổng + swap
- SSD: % + đã dùng/tổng của `/`
- Mạng: tốc độ xuống/lên + IP của `enp6s0`
- Uptime

Nếu tên card mạng khác `enp6s0`, sửa các biến `${downspeedf enp6s0}`, `${upspeedf enp6s0}`, `${addr enp6s0}` trong `mactahoe-widgets.lua`.

### 20.5.1. Widget âm lịch

Widget thứ ba nằm dưới widget hệ thống, chiều cao **150px** (một nửa widget hệ thống), chỉ hiển thị ngày hôm nay:

- Ngày Âm lịch lớn, tháng âm và năm Can Chi là thông tin chính.
- Dòng Dương lịch nhỏ bên dưới: ngày/tháng/năm và thứ.

Dữ liệu do `mactahoe-lunar-fetch.py` tạo từ module `apps/lunar.py`, được cài vào `~/.local/share/mactahoe-widgets/lunar.py`:

```text
~/.local/share/mactahoe-widgets/lunar.py
```

Sau đó chạy:

```bash
~/.local/bin/mactahoe-lunar-fetch.py
~/.local/bin/mactahoe-widgets restart
```

Widget tự cập nhật cache mỗi 30 phút; qua ngày mới sẽ đổi ngày Dương lịch và Âm lịch tương ứng.

### 20.6. Kiểm tra widget

Nếu widget không hiện, chạy tay để xem lỗi:

```bash
conky -c ~/.config/conky/mactahoe-weather.conf
conky -c ~/.config/conky/mactahoe-system.conf
conky -c ~/.config/conky/mactahoe-lunar.conf
```

### 20.7. Gỡ widget

```bash
~/.local/bin/mactahoe-widgets stop
rm -f ~/.config/autostart/mactahoe-widgets.desktop
rm -f ~/.local/share/applications/mactahoe-widgets.desktop
rm -f ~/.config/conky/mactahoe-{weather,system,lunar}.conf
rm -f ~/.config/conky/mactahoe-widgets.lua
rm -f ~/.local/bin/mactahoe-weather-fetch.py
rm -f ~/.local/bin/mactahoe-lunar-fetch.py
rm -f ~/.local/bin/mactahoe-widgets
rm -rf ~/.config/mactahoe-widgets ~/.cache/mactahoe-widgets
update-desktop-database ~/.local/share/applications
```
