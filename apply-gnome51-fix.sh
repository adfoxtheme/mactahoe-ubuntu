#!/usr/bin/env bash
# Vá UbuntuTahoe / UbuntuTahoeDock cho GNOME Shell 51 rồi cài lại hai extension.
# Chạy từ thư mục gốc của repo (cùng cấp với install-cachyos.sh):  bash apply-gnome51-fix.sh
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PATCH_FILE="$ROOT_DIR/gnome51-fix.patch"
EXT_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/gnome-shell/extensions"

die() { printf 'Lỗi: %s\n' "$*" >&2; exit 1; }

[ -f "$PATCH_FILE" ] || die "Thiếu $PATCH_FILE."
[ -d "$ROOT_DIR/vendor/gnome-extensions" ] || die "Hãy chạy script từ thư mục gốc của repo."
command -v patch >/dev/null 2>&1 || die "Thiếu lệnh 'patch' (sudo pacman -S patch)."

cd "$ROOT_DIR"
if patch -p1 --dry-run --forward -s < "$PATCH_FILE" >/dev/null 2>&1; then
    patch -p1 --forward < "$PATCH_FILE"
    echo "==> Đã vá mã nguồn."
elif patch -p1 --dry-run --reverse -s < "$PATCH_FILE" >/dev/null 2>&1; then
    echo "==> Bản vá đã được áp dụng trước đó, bỏ qua."
else
    die "Không áp dụng được bản vá (file đã bị sửa khác bản gốc?)."
fi

for uuid in UbuntuTahoe@adfoxtheme.github.io UbuntuTahoeDock@adfoxtheme.github.io; do
    target="$EXT_DIR/$uuid"
    mkdir -p "$EXT_DIR"
    rm -rf "$target"
    cp -a "$ROOT_DIR/vendor/gnome-extensions/$uuid" "$target"
    if [ -d "$target/schemas" ]; then glib-compile-schemas "$target/schemas"; fi
    echo "==> Đã cài lại $uuid"
done

printf '\nXong. Hãy ĐĂNG XUẤT rồi đăng nhập lại (Wayland không nạp lại extension được).\n'
printf 'Nếu dock vẫn lỗi, xem log:  journalctl -b -o cat /usr/bin/gnome-shell | grep -i ubuntutahoe\n'
