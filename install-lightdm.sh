#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
case "${1:-}" in
    '') [ "$#" -eq 0 ] || exit 2; action=install ;;
    --uninstall) [ "$#" -eq 1 ] || exit 2; action=uninstall ;;
    *) printf 'Usage: %s [--uninstall]\n' "$0" >&2; exit 2 ;;
esac
if [ "$EUID" -eq 0 ]; then
    printf 'Run as your normal user; the installer requests sudo when needed.\n' >&2
    exit 1
fi
if [ "$action" = install ]; then
    if [ "$(python3 "$ROOT_DIR/scripts/display_manager.py")" != lightdm ]; then
        printf 'LightDM is not the active/configured display manager.\n' >&2
        exit 1
    fi
    if [ ! -f "$HOME/.themes/MacTahoe-Dark/gtk-3.0/gtk.css" ]; then
        printf 'Run ./install.sh first to build the MacTahoe GTK theme.\n' >&2
        exit 1
    fi
    # Parse the generated GTK stylesheet as the desktop user before changing system files.
    python3 - "$HOME/.themes/MacTahoe-Dark/gtk-3.0/gtk.css" <<'PY'
import gi
import sys
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
Gtk.CssProvider().load_from_path(sys.argv[1])
PY
fi
sudo /usr/bin/python3 "$ROOT_DIR/scripts/lightdm_theme.py" "$action" \
    --theme "$HOME/.themes/MacTahoe-Dark/gtk-3.0" --assets "$ROOT_DIR/assets" \
    --cursor "$ROOT_DIR/vendor/MacTahoe-icon-theme/cursors/dist"

STATE_DIR="$HOME/.local/state/mactahoe-ubuntu"
if [ "$action" = install ]; then
    mkdir -p "$STATE_DIR"
    touch "$STATE_DIR/lightdm-installed"
else
    rm -f "$STATE_DIR/lightdm-installed"
fi
