#!/usr/bin/env bash
# Shared desktop detection and scalar Xfconf backup/restore helpers.
# shellcheck disable=SC2034 # desktop is read by the installer sourcing this file.
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

xfce_write_int_array() {
    local channel="$1" property="$2" value
    shift 2
    local -a args=()
    for value in "$@"; do args+=(-t int -s "$value"); done
    xfconf-query -c "$channel" -p "$property" --reset 2>/dev/null || true
    if [ "${#args[@]}" -gt 0 ]; then
        xfconf-query -c "$channel" -p "$property" --create --force-array "${args[@]}"
    fi
}

xfce_set_int_array() {
    local channel="$1" property="$2" saved="$BACKUP_DIR/xfconf/$1$2" raw
    shift 2
    if [ ! -e "$saved.type" ]; then
        mkdir -p "$(dirname "$saved")"
        if raw="$(LC_ALL=C xfconf-query -c "$channel" -p "$property" 2>/dev/null)"; then
            printf '%s\n' "$raw" | sed -n '/^[0-9][0-9]*$/p' > "$saved.value"
            printf 'array-int\n' > "$saved.type"
        else
            printf 'absent\n' > "$saved.type"
        fi
    fi
    xfce_write_int_array "$channel" "$property" "$@"
}

apply_xfce() {
    xfce_set xfce4-desktop /desktop-icons/style int 0
    xfce_set xsettings /Net/ThemeName string MacTahoe-Dark
    xfce_set xsettings /Net/IconThemeName string MacTahoe-blue
    xfce_set xsettings /Gtk/CursorThemeName string MacTahoe-cursors
    xfce_set xsettings /Gtk/CursorThemeSize int 24
    xfce_set xsettings /Gtk/FontName string 'SF Pro Display 11'
    xfce_set xsettings /Gtk/MonospaceFontName string 'SF Mono 11'
    xfce_set xsettings /Gtk/DecorationLayout string 'close,minimize,maximize:'
    xfce_set xfwm4 /general/use_compositing bool true
    xfce_set xfwm4 /general/theme string MacTahoe-Dark
    xfce_set xfwm4 /general/title_font string 'SF Pro Display Bold 11'
    xfce_set xfwm4 /general/button_layout string 'CMH|'
    local property helper wallpaper_list
    helper="$(dirname "${BASH_SOURCE[0]}")/wallpaper_properties.py"
    wallpaper_list="$(xfconf-query -c xfce4-desktop -l | python3 "$helper")" || return 1
    if [ -z "$wallpaper_list" ]; then
        printf 'Xfdesktop has no monitor wallpaper properties; retry after the desktop starts.\n' >&2
        return 1
    fi
    # Use actual monitor/workspace properties instead of assuming monitor0.
    while IFS= read -r property; do
        case "$property" in
            /backdrop/*/last-image|/backdrop/*/image-path)
                xfce_set xfce4-desktop "$property" string "$HOME/Pictures/Wallpapers/MacTahoe/MacTahoe-night.jpeg"
                xfce_set xfce4-desktop "${property%/*}/cycle-enable" bool false
                xfce_set xfce4-desktop "${property%/*}/image-style" int 5 ;;
        esac
    done <<< "$wallpaper_list"
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
        elif [ "$type" = array-int ]; then
            local -a values=()
            mapfile -t values < "${file%.type}.value"
            xfce_write_int_array "$channel" "$property" "${values[@]}"
        else
            xfconf-query -c "$channel" -p "$property" --create -t "$type" -s "$(cat "${file%.type}.value")"
        fi
    done < <(find "$BACKUP_DIR/xfconf" -name '*.type' -type f -print0)
}
