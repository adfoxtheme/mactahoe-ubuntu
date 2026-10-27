#!/usr/bin/env bash
# Isolated tests: no desktop or system package operations are performed.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/desktop.sh"
test_dir="$(mktemp -d)"
trap 'rm -rf "$test_dir"' EXIT
BACKUP_DIR="$test_dir/backup"
mock_dir="$test_dir/mock"
mkdir -p "$mock_dir"
xfconf-query() {
    [ "${mock_offline:-0}" = 0 ] || return 1
    local channel="" property="" value="" action=get
    while [ "$#" -gt 0 ]; do
        case "$1" in
            -c) channel="$2"; shift 2 ;;
            -p) property="$2"; shift 2 ;;
            -s) value="$2"; action=set; shift 2 ;;
            -t) shift 2 ;;
            -l) action=list; shift ;;
            --reset) action=reset; shift ;;
            --create) shift ;;
            *) return 2 ;;
        esac
    done
    local file="$mock_dir/$channel$property"
    case "$action" in
        list) [ "$channel" != xfce4-desktop ] || printf '/backdrop/screen0/monitorHDMI-1/workspace0/last-image\n' ;;
        get) [ -f "$file" ] && cat "$file" ;;
        set) mkdir -p "$(dirname "$file")"; printf '%s\n' "$value" > "$file" ;;
        reset) rm -f "$file" ;;
    esac
}
gnome-shell() { printf 'GNOME Shell 49.1\n'; }
gsettings() { return 0; }
XDG_CURRENT_DESKTOP=XFCE detect_desktop
[ "$desktop" = xfce ]
XDG_CURRENT_DESKTOP=ubuntu:GNOME detect_desktop
[ "$desktop" = gnome ]
if (XDG_CURRENT_DESKTOP=KDE detect_desktop) 2>/dev/null; then exit 1; fi
if (mock_offline=1 XDG_CURRENT_DESKTOP=XFCE detect_desktop) 2>/dev/null; then exit 1; fi
mkdir -p "$mock_dir/xsettings/Net"
printf 'Kali-Dark\n' > "$mock_dir/xsettings/Net/ThemeName"
apply_xfce
[ "$(cat "$mock_dir/xsettings/Net/ThemeName")" = MacTahoe-Dark ]
[ "$(cat "$mock_dir/xfwm4/general/button_layout")" = 'CMH|' ]
[ "$(cat "$mock_dir/xfce4-desktop/backdrop/screen0/monitorHDMI-1/workspace0/last-image")" = "$HOME/Pictures/Wallpapers/MacTahoe/MacTahoe-night.jpeg" ]
# Reinstall must retain the original, rather than backing up MacTahoe.
apply_xfce
restore_xfce
[ "$(cat "$mock_dir/xsettings/Net/ThemeName")" = Kali-Dark ]
[ ! -e "$mock_dir/xfwm4/general/theme" ]
[ ! -e "$mock_dir/xfce4-desktop/backdrop/screen0/monitorHDMI-1/workspace0/last-image" ]
printf 'PASS: desktop detection, Xfce settings, monitor wallpaper, reinstall, restore and absent properties\n'
