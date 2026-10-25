#!/usr/bin/env bash
# Gỡ MacTahoe đã cài bằng install-cachyos.sh và khôi phục các file đã sao lưu.
# Chạy bằng tài khoản thường (KHÔNG dùng sudo):  bash uninstall-cachyos.sh
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
die()  { printf 'Lỗi: %s\n' "$*" >&2; exit 1; }
warn() { printf 'Cảnh báo: %s\n' "$*" >&2; }
info() { printf '==> %s\n' "$*"; }

[ "$EUID" -ne 0 ] || die "Hãy chạy bằng tài khoản thường, không dùng sudo."

STATE_DIR="$HOME/.local/state/mactahoe-cachyos"
BACKUP_DIR=""
if [ -f "$STATE_DIR/latest-backup" ]; then
    BACKUP_DIR="$(cat "$STATE_DIR/latest-backup")"
    [ -d "$BACKUP_DIR" ] || BACKUP_DIR=""
fi
[ -n "$BACKUP_DIR" ] || warn "Không tìm thấy bản sao lưu; sẽ chỉ gỡ file đã cài."

printf 'Gỡ theme, extension, widget và ứng dụng MacTahoe? [y/N] '
read -r answer
case "$answer" in y|Y|yes|YES) ;; *) echo "Đã hủy."; exit 0 ;; esac

info "Dừng dịch vụ đồng bộ chế độ sáng/tối"
systemctl --user disable --now color-scheme-sync.service 2>/dev/null || true
rm -f "$HOME/.config/systemd/user/color-scheme-sync.service"
systemctl --user daemon-reload 2>/dev/null || true
if command -v mactahoe-widgets >/dev/null 2>&1; then mactahoe-widgets stop 2>/dev/null || true; fi

info "Gỡ extension"
for uuid in UbuntuTahoe@adfoxtheme.github.io UbuntuTahoeDock@adfoxtheme.github.io; do
    gnome-extensions disable "$uuid" 2>/dev/null || true
    rm -rf "$HOME/.local/share/gnome-shell/extensions/$uuid"
done

info "Gỡ theme GTK/Shell bằng trình gỡ của theme gốc"
if [ -f "$ROOT_DIR/vendor/MacTahoe-gtk-theme/install.sh" ]; then
    (cd "$ROOT_DIR/vendor/MacTahoe-gtk-theme" && bash ./install.sh -r) || warn "Gỡ theme gốc báo lỗi"
fi

info "Xóa file đã cài"
rm -f "$HOME/.local/bin/mactahoe-widgets" "$HOME/.local/bin/mactahoe-icon-manager" \
    "$HOME/.local/bin/mactahoe-weather-fetch.py" "$HOME/.local/bin/mactahoe-lunar-fetch.py" \
    "$HOME/.local/bin/am-lich-viet-nam" "$HOME/.local/bin/image-compressor" \
    "$HOME/.local/bin/color-scheme-sync.sh" \
    "$HOME/.local/share/applications/mactahoe-widgets.desktop" \
    "$HOME/.local/share/applications/mactahoe-icon-manager.desktop" \
    "$HOME/.local/share/applications/vn.ihoan.AmLich.desktop" \
    "$HOME/.local/share/applications/vn.ihoan.ImageCompressor.desktop" \
    "$HOME/.local/share/icons/hicolor/scalable/apps/vn.ihoan.AmLich.svg" \
    "$HOME/.local/share/icons/hicolor/scalable/apps/vn.ihoan.ImageCompressor.svg" \
    "$HOME"/.config/conky/mactahoe-*
rm -rf "$HOME/.local/share/fonts/MacTahoe" "$HOME/.local/share/mactahoe-widgets" \
    "$HOME/.local/share/mactahoe-apps" "$HOME/.config/mactahoe-widgets" \
    "$HOME"/.themes/MacTahoe-* "$HOME"/.local/share/themes/MacTahoe-* \
    "$HOME"/.local/share/icons/MacTahoe*
fc-cache -f 2>/dev/null || true
# Ảnh nền trong ~/Pictures/Wallpapers/MacTahoe được giữ lại; xóa tay nếu không cần.

info "Đặt lại thiết lập GNOME về mặc định"
while read -r schema key _; do
    [ -n "${schema:-}" ] || continue
    case "$schema" in
        org.gnome.shell.extensions.ubuntutahoe*|org.gnome.shell.extensions.blur-my-shell*|\
        org.gnome.shell.extensions.globalmenu*|org.gnome.shell.extensions.kimpanel*) continue ;;
    esac
    gsettings reset "$schema" "$key" 2>/dev/null || true
done < "$ROOT_DIR/config/gsettings-cachyos.tsv"
for key in picture-uri picture-uri-dark picture-options; do
    gsettings reset org.gnome.desktop.background "$key" 2>/dev/null || true
done
gsettings reset org.gnome.desktop.screensaver picture-uri 2>/dev/null || true
gsettings reset org.gnome.desktop.screensaver picture-options 2>/dev/null || true
gsettings reset org.gnome.shell favorite-apps 2>/dev/null || true

if [ -n "$BACKUP_DIR" ] && [ -d "$BACKUP_DIR/home" ]; then
    info "Khôi phục file đã sao lưu"
    cp -a "$BACKUP_DIR/home/." "$HOME/"
fi

info "Khôi phục Firefox (nếu có bản sao lưu)"
for firefox_root in "$HOME/.mozilla/firefox" "$HOME/.config/mozilla/firefox" \
    "$HOME/.var/app/org.mozilla.firefox/.mozilla/firefox" \
    "$HOME/.var/app/org.mozilla.firefox/config/mozilla/firefox"; do
    [ -d "$firefox_root" ] || continue
    while IFS= read -r -d '' prefs; do
        profile="${prefs%/prefs.js}"
        if [ -d "$profile/chrome.mactahoe-backup" ]; then
            rm -rf "$profile/chrome"
            mv "$profile/chrome.mactahoe-backup" "$profile/chrome"
        else
            rm -rf "$profile/chrome/MacTahoe"
            rm -f "$profile/chrome/customChrome.css" "$profile/chrome/userChrome.css" \
                "$profile/chrome/userContent.css"
        fi
        if [ -f "$profile/user.js.mactahoe-backup" ]; then
            mv "$profile/user.js.mactahoe-backup" "$profile/user.js"
        fi
    done < <(find "$firefox_root" -mindepth 2 -maxdepth 4 -type f -name prefs.js -print0)
done

update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
printf '\nĐã gỡ xong. Đăng xuất rồi đăng nhập lại để GNOME nạp lại giao diện.\n'
if [ -n "$BACKUP_DIR" ] && [ -f "$BACKUP_DIR/dconf-before.ini" ]; then
    printf 'Muốn khôi phục toàn bộ dconf như trước khi cài: dconf load / < %s/dconf-before.ini\n' "$BACKUP_DIR"
fi
