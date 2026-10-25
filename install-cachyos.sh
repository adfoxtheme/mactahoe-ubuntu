#!/usr/bin/env bash
# MacTahoe cho GNOME - bộ cài dành cho CachyOS / Arch Linux.
# Chạy bằng tài khoản thường (KHÔNG dùng sudo), từ thư mục gốc của repo:
#     bash install-cachyos.sh
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SKIP_PACKAGES=0
INSTALL_FIREFOX=1
KEEP_FAVORITES=0

usage() {
    cat <<'EOF'
Usage: bash install-cachyos.sh [OPTIONS]

  --skip-packages    Không cài gói bằng pacman (bạn tự cài trước)
  --no-firefox       Không cài theme vào profile Firefox
  --keep-favorites   Giữ nguyên danh sách app ghim trên dock
  -h, --help         Hiện trợ giúp này
EOF
}

die()  { printf 'Lỗi: %s\n' "$*" >&2; exit 1; }
warn() { printf 'Cảnh báo: %s\n' "$*" >&2; }
info() { printf '==> %s\n' "$*"; }

for arg in "$@"; do
    case "$arg" in
        --skip-packages)  SKIP_PACKAGES=1 ;;
        --no-firefox)     INSTALL_FIREFOX=0 ;;
        --keep-favorites) KEEP_FAVORITES=1 ;;
        -h|--help)        usage; exit 0 ;;
        *)                usage >&2; exit 2 ;;
    esac
done

# ---------------------------------------------------------------- kiểm tra
[ "$EUID" -ne 0 ] || die "Hãy chạy bằng tài khoản thường, không dùng sudo."
[ -r /etc/os-release ] || die "Không đọc được /etc/os-release."
. /etc/os-release
case " ${ID:-} ${ID_LIKE:-} " in
    *" cachyos "*|*" arch "*) ;;
    *) die "Bộ cài này dành cho CachyOS/Arch; phát hiện '${PRETTY_NAME:-unknown}'." ;;
esac
command -v pacman >/dev/null 2>&1 || die "Không tìm thấy pacman."
command -v gsettings >/dev/null 2>&1 || die "Không tìm thấy gsettings (cần glib2)."
command -v gnome-shell >/dev/null 2>&1 || die "Chưa cài GNOME Shell (sudo pacman -S gnome-shell)."
for required in vendor/MacTahoe-gtk-theme/install.sh vendor/MacTahoe-icon-theme/install.sh \
    vendor/gnome-extensions config/gsettings-cachyos.tsv; do
    [ -e "$ROOT_DIR/$required" ] || die "Thiếu '$required'. Hãy chạy script từ thư mục gốc của repo."
done
shell_major="$(gnome-shell --version | grep -oE '[0-9]+' | head -n1 || true)"
if [ -z "$shell_major" ] || [ "$shell_major" -lt 48 ]; then
    die "Cần GNOME Shell 48 trở lên; phát hiện '${shell_major:-không rõ}'."
fi
[ -n "${DBUS_SESSION_BUS_ADDRESS:-}" ] || \
    warn "Không thấy D-Bus session; hãy chạy script trong terminal của phiên GNOME/Niri."

if [ "$INSTALL_FIREFOX" -eq 1 ] && pgrep -u "$UID" -x firefox >/dev/null 2>&1; then
    die "Firefox đang chạy. Hãy đóng Firefox rồi chạy lại (hoặc dùng --no-firefox)."
fi

# ---------------------------------------------------------------- gói pacman
if [ "$SKIP_PACKAGES" -eq 0 ]; then
    info "Cài gói bằng pacman"
    wanted=(breeze-icons conky dconf fontconfig libadwaita gtk4 glib2 glib2-devel \
        gnome-shell-extensions gnome-tweaks extension-manager imagemagick librsvg \
        python-gobject python-pillow sassc xorg-xwayland)
    to_install=()
    missing=()
    for pkg in "${wanted[@]}"; do
        if pacman -Si "$pkg" >/dev/null 2>&1; then
            to_install+=("$pkg")
        else
            missing+=("$pkg")
        fi
    done
    if [ "${#missing[@]}" -gt 0 ]; then
        warn "Không thấy trong kho (bỏ qua): ${missing[*]}"
        warn "Nếu thiếu nhiều gói, hãy chạy 'sudo pacman -Syu' rồi thử lại."
    fi
    sudo pacman -S --needed "${to_install[@]}"
fi

# ---------------------------------------------------------------- sao lưu
STATE_DIR="$HOME/.local/state/mactahoe-cachyos"
mkdir -p "$STATE_DIR"
BACKUP_DIR=""
if [ -f "$STATE_DIR/latest-backup" ]; then
    previous_backup="$(cat "$STATE_DIR/latest-backup")"
    if [ -d "$previous_backup" ] && [ "$(dirname "$previous_backup")" = "$STATE_DIR" ]; then
        BACKUP_DIR="$previous_backup"
    fi
fi
if [ -z "$BACKUP_DIR" ]; then
    BACKUP_DIR="$(mktemp -d "$STATE_DIR/backup-$(date +%Y%m%d-%H%M%S)-XXXXXX")"
fi
printf '%s\n' "$BACKUP_DIR" > "$STATE_DIR/latest-backup"

if command -v dconf >/dev/null 2>&1 && [ ! -f "$BACKUP_DIR/dconf-before.ini" ]; then
    dconf dump / > "$BACKUP_DIR/dconf-before.ini" || true
fi

# Chỉ sao lưu bản "gốc" ở lần chạy đầu tiên; các lần sau không ghi đè.
backup_item() {
    local src="$HOME/$1" dst="$BACKUP_DIR/home/$1" mark="$BACKUP_DIR/captured/$1"
    if [ -e "$mark" ]; then
        return 0
    fi
    if [ -e "$src" ] || [ -L "$src" ]; then
        mkdir -p "$(dirname "$dst")"
        cp -a "$src" "$dst"
    fi
    mkdir -p "$(dirname "$mark")"
    : > "$mark"
}

info "Sao lưu cấu hình hiện có vào $BACKUP_DIR"
for relative in \
    .config/gtk-3.0 .config/gtk-4.0 \
    .local/bin/mactahoe-widgets .local/bin/mactahoe-icon-manager \
    .local/bin/mactahoe-weather-fetch.py .local/bin/mactahoe-lunar-fetch.py \
    .local/bin/am-lich-viet-nam .local/bin/image-compressor \
    .local/bin/color-scheme-sync.sh .local/share/fonts/MacTahoe \
    .local/share/mactahoe-widgets .local/share/mactahoe-apps \
    .local/share/applications/mactahoe-widgets.desktop \
    .local/share/applications/mactahoe-icon-manager.desktop \
    .local/share/applications/vn.ihoan.AmLich.desktop \
    .local/share/applications/vn.ihoan.ImageCompressor.desktop \
    .local/share/icons/hicolor/scalable/apps/vn.ihoan.AmLich.svg \
    .local/share/icons/hicolor/scalable/apps/vn.ihoan.ImageCompressor.svg \
    .config/mactahoe-widgets .config/systemd/user/color-scheme-sync.service \
    Pictures/Wallpapers/MacTahoe; do
    backup_item "$relative"
done
for path in "$HOME"/.config/conky/mactahoe-* "$HOME"/.themes/MacTahoe-* \
    "$HOME"/.local/share/themes/MacTahoe-* "$HOME"/.local/share/icons/MacTahoe*; do
    [ -e "$path" ] || continue
    backup_item "${path#"$HOME"/}"
done

mkdir -p "$HOME/.local/share/gnome-shell/extensions" \
    "$HOME/.local/share/fonts" "$HOME/.local/bin" "$HOME/.local/share/applications" \
    "$HOME/.local/share/mactahoe-widgets" "$HOME/.config/conky" \
    "$HOME/.config/mactahoe-widgets" "$HOME/.config/systemd/user" \
    "$HOME/.local/share/mactahoe-apps" \
    "$HOME/.local/share/icons/hicolor/scalable/apps" \
    "$HOME/Pictures/Wallpapers/MacTahoe"

# ---------------------------------------------------------------- theme, icon, font
info "Cài font, theme GTK/Shell, icon, con trỏ, wallpaper"
mkdir -p "$HOME/.local/share/fonts/MacTahoe"
cp -a "$ROOT_DIR/assets/fonts/SF-Pro" "$ROOT_DIR/assets/fonts/SF-Mono" \
    "$HOME/.local/share/fonts/MacTahoe/"
fc-cache -f "$HOME/.local/share/fonts/MacTahoe"
# Chạy bằng 'bash' để không phụ thuộc quyền thực thi (zip/GitHub download hay mất bit +x).
(cd "$ROOT_DIR/vendor/MacTahoe-gtk-theme" && bash ./install.sh -l --shell -i apple -p default)
(cd "$ROOT_DIR/vendor/MacTahoe-icon-theme" && bash ./install.sh -t blue)
mkdir -p "$HOME/.local/share/icons/MacTahoe-cursors" "$HOME/.local/share/icons/MacTahoe-dark-cursors"
cp -a "$ROOT_DIR/vendor/MacTahoe-icon-theme/cursors/dist/." "$HOME/.local/share/icons/MacTahoe-cursors/"
cp -a "$ROOT_DIR/vendor/MacTahoe-icon-theme/cursors/dist-dark/." "$HOME/.local/share/icons/MacTahoe-dark-cursors/"
cp -a "$ROOT_DIR/assets/wallpapers/." "$HOME/Pictures/Wallpapers/MacTahoe/"

# ---------------------------------------------------------------- ứng dụng đi kèm
info "Cài widget, trình quản lý icon, Âm lịch Việt Nam, Nén ảnh"
cp "$ROOT_DIR/apps/mactahoe-widgets" "$ROOT_DIR/apps/mactahoe-icon-manager" \
    "$ROOT_DIR/apps/mactahoe-weather-fetch.py" "$ROOT_DIR/apps/mactahoe-lunar-fetch.py" \
    "$ROOT_DIR/apps/color-scheme-sync.sh" "$HOME/.local/bin/"
cp "$ROOT_DIR/apps/launchers/am-lich-viet-nam" \
    "$ROOT_DIR/apps/launchers/image-compressor" "$HOME/.local/bin/"
chmod +x "$HOME/.local/bin/mactahoe-widgets" "$HOME/.local/bin/mactahoe-icon-manager" \
    "$HOME/.local/bin/mactahoe-weather-fetch.py" "$HOME/.local/bin/mactahoe-lunar-fetch.py" \
    "$HOME/.local/bin/am-lich-viet-nam" "$HOME/.local/bin/image-compressor" \
    "$HOME/.local/bin/color-scheme-sync.sh"
cp "$ROOT_DIR/apps/lunar.py" "$HOME/.local/share/mactahoe-widgets/lunar.py"
mkdir -p "$HOME/.local/share/mactahoe-apps/am-lich-viet-nam" \
    "$HOME/.local/share/mactahoe-apps/image-compressor"
cp -a "$ROOT_DIR/apps/am-lich-viet-nam/." "$HOME/.local/share/mactahoe-apps/am-lich-viet-nam/"
cp -a "$ROOT_DIR/apps/image-compressor/." "$HOME/.local/share/mactahoe-apps/image-compressor/"
cp "$ROOT_DIR/apps/am-lich-viet-nam/assets/vn.ihoan.AmLich.svg" \
    "$HOME/.local/share/icons/hicolor/scalable/apps/"
cp "$ROOT_DIR/apps/image-compressor/assets/vn.ihoan.ImageCompressor.svg" \
    "$HOME/.local/share/icons/hicolor/scalable/apps/"

for conf in "$ROOT_DIR"/conky/mactahoe-*.conf; do
    sed "s|@HOME@|$HOME|g" "$conf" > "$HOME/.config/conky/${conf##*/}"
done
cp "$ROOT_DIR/conky/mactahoe-widgets.lua" "$HOME/.config/conky/"
sed "s|@HOME@|$HOME|g" "$ROOT_DIR/config/weather.conf" \
    > "$HOME/.config/mactahoe-widgets/weather.conf"

if command -v conky >/dev/null 2>&1; then
    if ! conky --version 2>&1 | grep -qiE 'cairo|lua'; then
        warn "Bản conky hiện tại có vẻ không có Lua/Cairo; widget có thể không hiển thị đúng."
    fi
fi

# ---------------------------------------------------------------- extension GNOME
info "Cài extension UbuntuTahoe và UbuntuTahoeDock"
EXTENSION_IDS=(UbuntuTahoe@adfoxtheme.github.io UbuntuTahoeDock@adfoxtheme.github.io)
COMPATIBLE_EXTENSION_IDS=()
# Các extension trùng chức năng với bộ trên, tắt đi để khỏi xung đột.
INCOMPATIBLE_EXTENSION_IDS=(blur-my-shell@aunetx globalmenu@ShiroOSL.github.io \
    just-perfection-desktop@just-perfection kimpanel@kde.org \
    ubuntu-dock@ubuntu.com dash-to-dock@micxgx.gmail.com)
for legacy in "${INCOMPATIBLE_EXTENSION_IDS[@]}"; do
    gnome-extensions disable "$legacy" 2>/dev/null || true
done
for uuid in "${EXTENSION_IDS[@]}"; do
    if ! python3 -c 'import json, sys; data = json.load(open(sys.argv[1], encoding="utf-8")); sys.exit(0 if sys.argv[2] in data.get("shell-version", []) else 1)' \
        "$ROOT_DIR/vendor/gnome-extensions/$uuid/metadata.json" "$shell_major"; then
        warn "Bỏ qua $uuid: không khai báo hỗ trợ GNOME Shell $shell_major."
        INCOMPATIBLE_EXTENSION_IDS+=("$uuid")
        continue
    fi
    target="$HOME/.local/share/gnome-shell/extensions/$uuid"
    backup_item ".local/share/gnome-shell/extensions/$uuid"
    rm -rf "$target"
    cp -a "$ROOT_DIR/vendor/gnome-extensions/$uuid" "$target"
    if [ -d "$target/schemas" ]; then glib-compile-schemas "$target/schemas"; fi
    COMPATIBLE_EXTENSION_IDS+=("$uuid")
done

# Một số schema (blur-my-shell, globalmenu, kimpanel) nằm trong thư mục schemas của UbuntuTahoe.
gs() {
    local schema="$1"; shift
    local command="$1"; shift
    local uuid schema_dir
    case "$schema" in
        org.gnome.shell.extensions.ubuntutahoedock*) uuid=UbuntuTahoeDock@adfoxtheme.github.io ;;
        org.gnome.shell.extensions.ubuntutahoe*|\
        org.gnome.shell.extensions.blur-my-shell*|\
        org.gnome.shell.extensions.globalmenu*|\
        org.gnome.shell.extensions.kimpanel*) uuid=UbuntuTahoe@adfoxtheme.github.io ;;
        *) gsettings "$command" "$schema" "$@"; return $? ;;
    esac
    schema_dir="$HOME/.local/share/gnome-shell/extensions/$uuid/schemas"
    GSETTINGS_SCHEMA_DIR="$schema_dir" gsettings "$command" "$schema" "$@"
}

info "Áp dụng thiết lập GNOME"
while read -r schema key value; do
    [ -n "${schema:-}" ] || continue
    if gs "$schema" writable "$key" >/dev/null 2>&1; then
        gs "$schema" set "$key" "$value" || warn "Không đặt được $schema $key"
    fi
done < "$ROOT_DIR/config/gsettings-cachyos.tsv"

wall="$HOME/Pictures/Wallpapers/MacTahoe/MacTahoe-night.jpeg"
wall_uri="$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).as_uri())' "$wall")"
gsettings set org.gnome.desktop.background picture-uri "$wall_uri"
gsettings set org.gnome.desktop.background picture-uri-dark "$wall_uri"
gsettings set org.gnome.desktop.background picture-options 'zoom'
gsettings set org.gnome.desktop.screensaver picture-uri "$wall_uri"
gsettings set org.gnome.desktop.screensaver picture-options 'zoom'

extension_ids=(user-theme@gnome-shell-extensions.gcampax.github.com)
for uuid in "${COMPATIBLE_EXTENSION_IDS[@]}"; do
    extension_ids+=("$uuid")
done
python3 - "${extension_ids[@]}" -- -- "${INCOMPATIBLE_EXTENSION_IDS[@]}" <<'PY'
import ast
import subprocess
import sys

schema = "org.gnome.shell"
key = "enabled-extensions"
raw_enabled = subprocess.check_output(["gsettings", "get", schema, key], text=True).strip()
enabled = ast.literal_eval(raw_enabled.removeprefix("@as "))
first_separator = sys.argv.index("--")
second_separator = sys.argv.index("--", first_separator + 1)
required = sys.argv[1:first_separator]
incompatible = sys.argv[second_separator + 1:]
enabled = [uuid for uuid in enabled if uuid not in incompatible]
for uuid in required:
    if uuid not in enabled:
        enabled.append(uuid)
variant = "[" + ", ".join(repr(uuid) for uuid in enabled) + "]"
subprocess.run(["gsettings", "set", schema, key, variant], check=True)
PY

# ---------------------------------------------------------------- launcher, dịch vụ
info "Cài launcher và dịch vụ đồng bộ chế độ sáng/tối"
cp "$ROOT_DIR/desktop/mactahoe-widgets.desktop" "$HOME/.local/share/applications/"
cp "$ROOT_DIR/desktop/mactahoe-icon-manager.desktop" "$HOME/.local/share/applications/"
sed "s|^Exec=am-lich-viet-nam$|Exec=$HOME/.local/bin/am-lich-viet-nam|" \
    "$ROOT_DIR/desktop/vn.ihoan.AmLich.desktop" \
    > "$HOME/.local/share/applications/vn.ihoan.AmLich.desktop"
sed "s|^Exec=image-compressor$|Exec=$HOME/.local/bin/image-compressor|" \
    "$ROOT_DIR/desktop/vn.ihoan.ImageCompressor.desktop" \
    > "$HOME/.local/share/applications/vn.ihoan.ImageCompressor.desktop"
cp "$ROOT_DIR/systemd/color-scheme-sync.service" "$HOME/.config/systemd/user/"
systemctl --user daemon-reload || warn "systemctl --user daemon-reload thất bại"
systemctl --user enable --now color-scheme-sync.service || warn "Không bật được color-scheme-sync.service"
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

# Danh sách app ghim: chỉ giữ những app thực sự có trên máy (bản gốc dùng ID của snap/Ubuntu).
if [ "$KEEP_FAVORITES" -eq 0 ]; then
    desktop_dirs=(/usr/share/applications "$HOME/.local/share/applications" \
        /var/lib/flatpak/exports/share/applications \
        "$HOME/.local/share/flatpak/exports/share/applications")
    favorites=()
    for app in firefox.desktop org.mozilla.firefox.desktop google-chrome.desktop \
        org.gnome.Nautilus.desktop org.gnome.Settings.desktop org.gnome.Console.desktop \
        org.gnome.Ptyxis.desktop vn.ihoan.ImageCompressor.desktop vn.ihoan.AmLich.desktop \
        mactahoe-widgets.desktop; do
        for dir in "${desktop_dirs[@]}"; do
            if [ -f "$dir/$app" ]; then favorites+=("$app"); break; fi
        done
    done
    if [ "${#favorites[@]}" -gt 0 ]; then
        list=""
        for app in "${favorites[@]}"; do list+="${list:+, }'$app'"; done
        gsettings set org.gnome.shell favorite-apps "[$list]"
    fi
fi

# ---------------------------------------------------------------- Firefox
if [ "$INSTALL_FIREFOX" -eq 1 ]; then
    info "Cài theme cho Firefox"
    for firefox_root in "$HOME/.mozilla/firefox" "$HOME/.config/mozilla/firefox" \
        "$HOME/.var/app/org.mozilla.firefox/.mozilla/firefox" \
        "$HOME/.var/app/org.mozilla.firefox/config/mozilla/firefox"; do
        [ -d "$firefox_root" ] || continue
        while IFS= read -r -d '' prefs; do
            profile="${prefs%/prefs.js}"
            chrome="$profile/chrome"
            if [ -d "$chrome" ] && [ ! -e "$profile/chrome.mactahoe-backup" ]; then
                cp -a "$chrome" "$profile/chrome.mactahoe-backup"
            fi
            mkdir -p "$chrome"
            cp -a "$ROOT_DIR/vendor/MacTahoe-gtk-theme/other/firefox/MacTahoe" "$chrome/"
            cp "$ROOT_DIR/vendor/MacTahoe-gtk-theme/other/firefox/customChrome.css" \
                "$ROOT_DIR/vendor/MacTahoe-gtk-theme/other/firefox/userChrome.css" \
                "$ROOT_DIR/vendor/MacTahoe-gtk-theme/other/firefox/userContent.css" "$chrome/"
            if [ -f "$profile/user.js" ]; then cp -n "$profile/user.js" "$profile/user.js.mactahoe-backup"; fi
            touch "$profile/user.js"
            while IFS= read -r pref; do
                grep -Fqx "$pref" "$profile/user.js" || printf '%s\n' "$pref" >> "$profile/user.js"
            done < "$ROOT_DIR/config/firefox-user.js"
        done < <(find "$firefox_root" -mindepth 2 -maxdepth 4 -type f -name prefs.js -print0)
    done
fi

# ---------------------------------------------------------------- kết thúc
printf '\nĐã cài xong. Đăng xuất rồi đăng nhập lại để GNOME nạp theme và extension.\n'
printf 'Widget chỉ chạy khi bạn mở "Widget MacTahoe".\nSao lưu: %s\n' "$BACKUP_DIR"
if command -v niri >/dev/null 2>&1; then
    printf '\nBạn có Niri: xem %s/config/niri-mactahoe.kdl để đặt con trỏ/bo góc cho phiên Niri.\n' "$ROOT_DIR"
fi
