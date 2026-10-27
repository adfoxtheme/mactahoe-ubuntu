#!/usr/bin/env bash
# Run in an isolated X11/D-Bus session with the Xfce dependencies installed.
set -euo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
test_dir="$(mktemp -d)"
cleanup() {
    if declare -F stop_xfce_panel >/dev/null; then stop_xfce_panel || true; fi
    "$HOME/.local/bin/mactahoe-xfce-widgets" --stop 2>/dev/null || true
    "$HOME/.local/bin/mactahoe-xfce-dock" stop 2>/dev/null || true
    [ -z "${wm_pid:-}" ] || kill "$wm_pid" 2>/dev/null || true
    rm -rf "$test_dir"
}
trap cleanup EXIT
export HOME="$test_dir/home"
export XDG_CONFIG_HOME="$HOME/.config" XDG_DATA_HOME="$HOME/.local/share"
export XDG_CURRENT_DESKTOP=XFCE GDK_BACKEND=x11
BACKUP_DIR="$HOME/.local/state/mactahoe-ubuntu/backup-test"
mkdir -p "$HOME/.local/state/mactahoe-ubuntu"
printf '%s\n' "$BACKUP_DIR" > "$HOME/.local/state/mactahoe-ubuntu/latest-backup"
xfwm4 --compositor=on >/dev/null 2>&1 &
wm_pid=$!
mkdir -p "$BACKUP_DIR" "$HOME/.local/bin" "$HOME/.local/share/applications" \
    "$HOME/.local/share/mactahoe-apps/am-lich-viet-nam" "$HOME/Pictures/Wallpapers/MacTahoe"
cp "$ROOT_DIR/assets/wallpapers/MacTahoe-night.jpeg" "$HOME/Pictures/Wallpapers/MacTahoe/"
cp "$ROOT_DIR/apps/am-lich-viet-nam/lunar.py" "$HOME/.local/share/mactahoe-apps/am-lich-viet-nam/"
dbus-update-activation-environment HOME XDG_CONFIG_HOME XDG_DATA_HOME GDK_BACKEND DISPLAY
backup_item() {
    local relative="$1"
    [ ! -e "$BACKUP_DIR/captured/$relative" ] || return 0
    mkdir -p "$BACKUP_DIR/captured/$(dirname "$relative")"
    if [ -e "$HOME/$relative" ]; then
        mkdir -p "$BACKUP_DIR/home/$(dirname "$relative")"
        cp -a "$HOME/$relative" "$BACKUP_DIR/home/$relative"
    fi
    touch "$BACKUP_DIR/captured/$relative"
}
source "$ROOT_DIR/scripts/desktop.sh"
source "$ROOT_DIR/scripts/xfce-extras.sh"
xfconf-query -c xfce4-panel -p /configver --create -t int -s 2
xfce_write_int_array xfce4-panel /panels 1
xfce_write_int_array xfce4-panel /panels/panel-1/plugin-ids 1
xfconf-query -c xfce4-panel -p /panels/panel-1/position --create -t string -s 'p=6;x=0;y=0'
xfconf-query -c xfce4-panel -p /plugins/plugin-1 --create -t string -s applicationsmenu
schema=net.launchpad.plank.dock.settings:/net/launchpad/plank/docks/mactahoe/
gsettings set "$schema" icon-size 60
xfce_set xsettings /Net/ThemeName string MacTahoe-Dark
xfconf-query -c xfce4-desktop -p /backdrop/screen0/monitorVirtual1/workspace0/image-style --create -t int -s 5
install_xfce_extras
[ "$(gsettings get "$schema" icon-size)" = 44 ]
[ "$(gsettings get "$schema" hide-mode)" = "'dodge-maximized'" ]
[ -x "$HOME/.local/bin/mactahoe-xfce-widgets" ]
[ -f "$HOME/.config/autostart/mactahoe-xfce-dock.desktop" ]
[ -f "$HOME/.config/autostart/mactahoe-xfce-session.desktop" ]
[ "$(xfconf-query -c xfce4-desktop -p /backdrop/screen0/monitorVirtual1/workspace0/last-image)" = "$HOME/Pictures/Wallpapers/MacTahoe/MacTahoe-night.jpeg" ]
# Simulate Kali/session defaults changing it again; login must reapply Tahoe.
xfconf-query -c xfce4-desktop -p /backdrop/screen0/monitorVirtual1/workspace0/last-image -s /kali-wallpaper.png
"$HOME/.local/bin/mactahoe-xfce-session"
[ "$(xfconf-query -c xfce4-desktop -p /backdrop/screen0/monitorVirtual1/workspace0/last-image)" = "$HOME/Pictures/Wallpapers/MacTahoe/MacTahoe-night.jpeg" ]
[ -f "$HOME/.config/plank/mactahoe/launchers/1.dockitem" ]
gsettings set "$schema" icon-size 64
install_xfce_extras
[ "$(gsettings get "$schema" icon-size)" = 64 ]
"$HOME/.local/bin/mactahoe-xfce-dock" stop
dconf reset -f /net/launchpad/plank/docks/mactahoe/
dconf load /net/launchpad/plank/docks/mactahoe/ < "$BACKUP_DIR/plank-before.ini"
[ "$(gsettings get "$schema" icon-size)" = 60 ]
stop_xfce_panel
restore_xfce
printf 'PASS: real Xfconf, Plank settings, pinned launcher, autostart, repeat-install and restore\n'
