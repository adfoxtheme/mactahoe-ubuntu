#!/usr/bin/env bash
# Shared desktop detection and scalar Xfconf backup/restore helpers.
detect_desktop() {
    local session="${XDG_CURRENT_DESKTOP:-${XDG_SESSION_DESKTOP:-${DESKTOP_SESSION:-}}}"
    case "${session,,}" in
        *xfce*)
            desktop=xfce
            if ! command -v xfconf-query >/dev/null 2>&1 ||
               ! xfconf-query -c xsettings -l >/dev/null 2>&1; then
                printf 'Run this installer from an active Xfce desktop session.\n' >&2
                exit 1
            fi ;;
        *gnome*|ubuntu|ubuntu:*)
            desktop=gnome
            if ! command -v gnome-shell >/dev/null 2>&1 ||
               ! gsettings get org.gnome.desktop.interface gtk-theme >/dev/null 2>&1; then
                printf 'Run this installer from an active GNOME desktop session.\n' >&2
                exit 1
            fi ;;
        *) printf 'Unsupported desktop: %s. Log in to GNOME or Xfce first.\n' "${session:-unknown}" >&2
           exit 1 ;;
    esac
}

xfce_set() {
    local channel="$1" property="$2" type="$3" value="$4"
    local saved="$BACKUP_DIR/xfconf/$channel$property"
    if [ ! -e "$saved.type" ]; then
        mkdir -p "$(dirname "$saved")"
        if xfconf-query -c "$channel" -p "$property" > "$saved.value" 2>/dev/null; then
            printf '%s\n' "$type" > "$saved.type"
        else
            printf 'absent\n' > "$saved.type"
        fi
    fi
    xfconf-query -c "$channel" -p "$property" --create -t "$type" -s "$value"
}

apply_xfce() {
    xfce_set xsettings /Net/ThemeName string MacTahoe-Dark
    xfce_set xsettings /Net/IconThemeName string MacTahoe-blue
    xfce_set xsettings /Gtk/CursorThemeName string MacTahoe-cursors
    xfce_set xsettings /Gtk/CursorThemeSize int 24
    xfce_set xsettings /Gtk/FontName string 'SF Pro Display 11'
    xfce_set xsettings /Gtk/MonospaceFontName string 'SF Mono 11'
    xfce_set xsettings /Gtk/DecorationLayout string 'close,minimize,maximize:'
    xfce_set xfwm4 /general/theme string MacTahoe-Dark
    xfce_set xfwm4 /general/title_font string 'SF Pro Display Bold 11'
    xfce_set xfwm4 /general/button_layout string 'CMH|'
    local property
    # Use actual monitor/workspace properties instead of assuming monitor0.
    while IFS= read -r property; do
        case "$property" in
            /backdrop/*/last-image|/backdrop/*/image-path)
                xfce_set xfce4-desktop "$property" string "$HOME/Pictures/Wallpapers/MacTahoe/MacTahoe-night.jpeg"
                xfce_set xfce4-desktop "${property%/*}/image-style" int 5 ;;
        esac
    done < <(xfconf-query -c xfce4-desktop -l)
}

restore_xfce() {
    if ! command -v xfconf-query >/dev/null 2>&1 ||
       ! xfconf-query -c xsettings -l >/dev/null 2>&1; then
        printf 'Log in to Xfce and rerun uninstall.sh to restore its settings.\n' >&2
        return 1
    fi
    local file relative channel property type
    while IFS= read -r -d '' file; do
        relative="${file#"$BACKUP_DIR/xfconf/"}"
        channel="${relative%%/*}"
        property="/${relative#*/}"
        property="${property%.type}"
        type="$(cat "$file")"
        if [ "$type" = absent ]; then
            xfconf-query -c "$channel" -p "$property" --reset || true
        else
            xfconf-query -c "$channel" -p "$property" --create -t "$type" -s "$(cat "${file%.type}.value")"
        fi
    done < <(find "$BACKUP_DIR/xfconf" -name '*.type' -type f -print0)
}
