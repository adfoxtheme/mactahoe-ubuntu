#!/usr/bin/env bash
# Run in an isolated X11/D-Bus session with the Xfce dependencies installed.
set -euo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
test_dir="$(mktemp -d)"
trap 'rm -rf "$test_dir"' EXIT
export HOME="$test_dir/home"
export XDG_CONFIG_HOME="$HOME/.config" XDG_DATA_HOME="$HOME/.local/share"
export XDG_CURRENT_DESKTOP=XFCE GDK_BACKEND=x11
BACKUP_DIR="$test_dir/backup"
mkdir -p "$BACKUP_DIR" "$HOME/.local/bin" "$HOME/.local/share/applications" \
    "$HOME/.local/share/mactahoe-apps/am-lich-viet-nam"
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
# This test checks installation, not process startup (covered by test-xfce-ui.py).
nohup() { return 0; }
source "$ROOT_DIR/scripts/desktop.sh"
source "$ROOT_DIR/scripts/xfce-extras.sh"
schema=net.launchpad.plank.dock.settings:/net/launchpad/plank/docks/mactahoe/
gsettings set "$schema" icon-size 60
xfce_set xsettings /Net/ThemeName string MacTahoe-Dark
install_xfce_extras
[ "$(gsettings get "$schema" icon-size)" = 45 ]
[ "$(gsettings get "$schema" hide-mode)" = "'dodge-maximized'" ]
[ -x "$HOME/.local/bin/mactahoe-xfce-widgets" ]
[ -f "$HOME/.config/autostart/mactahoe-xfce-dock.desktop" ]
[ -f "$HOME/.config/plank/mactahoe/launchers/1.dockitem" ]
gsettings set "$schema" icon-size 64
install_xfce_extras
[ "$(gsettings get "$schema" icon-size)" = 64 ]
dconf reset -f /net/launchpad/plank/docks/mactahoe/
dconf load /net/launchpad/plank/docks/mactahoe/ < "$BACKUP_DIR/plank-before.ini"
[ "$(gsettings get "$schema" icon-size)" = 60 ]
restore_xfce
printf 'PASS: real Xfconf, Plank settings, pinned launcher, autostart, repeat-install and restore\n'
