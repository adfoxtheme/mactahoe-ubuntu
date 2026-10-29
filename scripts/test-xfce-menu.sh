#!/usr/bin/env bash
# Run under xvfb-run + dbus-run-session. No user desktop settings are changed.
set -euo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
test_dir="$(mktemp -d)"
export HOME="$test_dir/home" XDG_CURRENT_DESKTOP=XFCE GDK_BACKEND=x11
export XDG_CONFIG_HOME="$HOME/.config" XDG_DATA_HOME="$HOME/.local/share"
BACKUP_DIR="$test_dir/backup"
mkdir -p "$BACKUP_DIR" "$HOME/.local/bin" "$HOME/.config/xfce4/panel" \
    "$HOME/.config/gtk-3.0" "$HOME/.local/share/applications"
dbus-update-activation-environment HOME XDG_CONFIG_HOME XDG_DATA_HOME DISPLAY GDK_BACKEND
source "$ROOT_DIR/scripts/desktop.sh"
source "$ROOT_DIR/scripts/xfce-menu.sh"
cleanup() {
    stop_xfce_panel || true
    [ -z "${wm_pid:-}" ] || kill "$wm_pid" 2>/dev/null || true
    rm -rf "$test_dir"
}
trap cleanup EXIT
backup_item() {
    local relative="$1" captured="$BACKUP_DIR/captured/home/$1"
    [ ! -e "$captured" ] || return 0
    mkdir -p "$(dirname "$captured")"
    if [ -e "$HOME/$relative" ]; then
        mkdir -p "$BACKUP_DIR/home/$(dirname "$relative")"
        cp -a "$HOME/$relative" "$BACKUP_DIR/home/$relative"
    fi
    touch "$captured"
}
xfwm4 --compositor=on > "$test_dir/wm.log" 2>&1 &
wm_pid=$!
xfconf-query -c xsettings -p /Net/ThemeName --create -t string -s Adwaita-dark
xfconf-query -c xfce4-panel -p /configver --create -t int -s 2
xfce_write_int_array xfce4-panel /panels 1
xfce_write_int_array xfce4-panel /panels/panel-1/plugin-ids 1
xfconf-query -c xfce4-panel -p /panels/panel-1/position --create -t string -s 'p=6;x=0;y=0'
xfconf-query -c xfce4-panel -p /plugins/plugin-1 --create -t string -s whiskermenu
printf '/* user rule */\n' > "$HOME/.config/gtk-3.0/gtk.css"
printf 'favorites=tahoe-test.desktop\nlauncher-show-description=true\n' > "$HOME/.config/xfce4/panel/whiskermenu-1.rc"
cat > "$HOME/.local/share/applications/tahoe-test.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Tahoe Test Application
Exec=touch $test_dir/launched
Icon=applications-utilities
Categories=Utility;
EOF
install_xfce_menu
sleep 2
[ "$(xfconf-query -c xfce4-panel -p /plugins/plugin-1/view-mode)" = 0 ]
[ "$(xfconf-query -c xfce4-panel -p /plugins/plugin-1/default-category)" = 2 ]
if [ -f "$HOME/.config/xfce4/panel/whiskermenu-1.rc" ]; then
    grep -q 'favorites=tahoe-test.desktop' "$HOME/.config/xfce4/panel/whiskermenu-1.rc"
else
    xfconf-query -c xfce4-panel -p /plugins/plugin-1/favorites | grep -q tahoe-test.desktop
fi
grep -q 'user rule' "$HOME/.config/gtk-3.0/gtk.css"
timeout 5 "$HOME/.local/bin/mactahoe-xfce-menu" --center
sleep 1
if [ -n "${MACTAHOE_MENU_SCREENSHOT:-}" ]; then
    python3 - "$MACTAHOE_MENU_SCREENSHOT" <<'PY'
import gi
import sys
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk
root = Gdk.get_default_root_window()
Gdk.pixbuf_get_from_window(root, 0, 0, root.get_width(), root.get_height()).savev(sys.argv[1], 'png', [], [])
PY
fi
xdotool type --clearmodifiers 'Tahoe Test Application'
sleep 1
xdotool key Return
sleep 1
[ -f "$test_dir/launched" ]
install_xfce_menu
sleep 1
xfconf-query -c xfce4-panel -p /plugins/plugin-1/favorites | grep -q tahoe-test.desktop
if grep -qi 'Theme parsing error' "$HOME/.cache/mactahoe-xfce/panel.log"; then
    cat "$HOME/.cache/mactahoe-xfce/panel.log" >&2
    exit 1
fi
[ "$(grep -c '@import url("mactahoe-menu.css");' "$HOME/.config/gtk-3.0/gtk.css")" = 1 ]
stop_xfce_panel
restore_xfce
[ "$(xfconf-query -c xfce4-panel -p /plugins/plugin-1)" = whiskermenu ]
if xfconf-query -c xfce4-panel -p /plugins/plugin-1/view-mode >/dev/null 2>&1; then exit 1; fi
# Test the path with no application menu: prepend a new one, preserving the original item array.
rm -rf "$BACKUP_DIR/xfconf/xfce4-panel"
xfconf-query -c xfce4-panel -p /plugins/plugin-1 -s separator
install_xfce_menu
stop_xfce_panel
[ "$(xfconf-query -c xfce4-panel -p /plugins/plugin-2)" = whiskermenu ]
restore_xfce
[ "$(LC_ALL=C xfconf-query -c xfce4-panel -p /panels/panel-1/plugin-ids | sed -n '/^[0-9][0-9]*$/p')" = 1 ]
printf 'PASS: native menu, grid settings, preserved favorites/CSS, application search/launch, reinstall and array restore\n'
