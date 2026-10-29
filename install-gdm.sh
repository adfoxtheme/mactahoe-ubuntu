#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
GTK_THEME_DIR="$ROOT_DIR/vendor/MacTahoe-gtk-theme"
GDM_DIR="$GTK_THEME_DIR/other/gdm"

if [ "$#" -ne 0 ]; then
    printf 'Usage: %s\n' "$0" >&2
    exit 2
fi
if [ "$EUID" -eq 0 ]; then
    printf 'Run as your normal user, without sudo.\n' >&2
    exit 1
fi
if [ ! -r /etc/os-release ] || ! command -v gsettings >/dev/null 2>&1; then
    printf 'This installer requires Ubuntu, Debian, Kali, Fedora, or CachyOS/Arch.\n' >&2
    exit 1
fi
. /etc/os-release
distribution_id="${ID:-}"
distribution_like="${ID_LIKE:-}"
if [ "$distribution_id" != ubuntu ] && [ "$distribution_id" != debian ] && [ "$distribution_id" != kali ] && \
   [ "$distribution_id" != fedora ] && [ "$distribution_id" != cachyos ] && \
   [ "$distribution_id" != arch ] && [[ ! "$distribution_like" =~ arch ]]; then
    printf 'This installer currently supports Ubuntu, Debian, Kali, Fedora, and CachyOS/Arch; detected %s (%s).\n' \
        "${PRETTY_NAME:-unknown}" "$distribution_id" >&2
    exit 1
fi
if [ "$(python3 "$ROOT_DIR/scripts/display_manager.py")" != gdm ]; then
    printf 'GDM is not the active/configured display manager.\n' >&2
    exit 1
fi
shell_version="$(gnome-shell --version 2>/dev/null || true)"
shell_major="${shell_version##* }"
shell_major="${shell_major%%.*}"
if ! [[ "$shell_major" =~ ^[0-9]+$ ]] || [ "$shell_major" -lt 48 ]; then
    printf 'This installer requires GNOME Shell 48 or newer; detected %s.\n' \
        "${shell_major:-unknown}" >&2
    exit 1
fi
if ! command -v gdm >/dev/null 2>&1 && ! command -v gdm3 >/dev/null 2>&1 && \
   [ ! -x /usr/sbin/gdm ] && [ ! -x /usr/sbin/gdm3 ] && \
   [ ! -x /usr/bin/gdm ] && [ ! -x /usr/bin/gdm3 ]; then
    printf 'GDM is not installed; refusing to change the active display manager.\n' >&2
    exit 1
fi
if [ ! -f "$GDM_DIR/gnome-shell-theme.gresource.xml" ] || \
    [ ! -f "$GDM_DIR/theme/background.png" ]; then
    printf 'The bundled MacTahoe GDM theme source is incomplete.\n' >&2
    exit 1
fi

if [ "$distribution_id" = fedora ]; then
    packages=(glib2-devel sassc)
    if [ -f /usr/share/gnome-shell/theme/gnome-shell-theme.gresource ]; then
        GDM_RESOURCE=/usr/share/gnome-shell/theme/gnome-shell-theme.gresource
    else
        GDM_RESOURCE=/usr/share/gnome-shell/gnome-shell-theme.gresource
    fi
    sudo dnf install -y "${packages[@]}"
elif [ "$distribution_id" = cachyos ] || [ "$distribution_id" = arch ] || [[ "$distribution_like" =~ arch ]]; then
    packages=(glib2 glib2-devel sassc)
    if [ -f /usr/share/gnome-shell/theme/gnome-shell-theme.gresource ]; then
        GDM_RESOURCE=/usr/share/gnome-shell/theme/gnome-shell-theme.gresource
    else
        GDM_RESOURCE=/usr/share/gnome-shell/gnome-shell-theme.gresource
    fi
    sudo pacman -S --needed --noconfirm "${packages[@]}"
elif [ "$distribution_id" = ubuntu ]; then
    packages=(libglib2.0-bin libglib2.0-dev-bin sassc yaru-theme-gnome-shell)
    GDM_RESOURCE=/usr/share/gnome-shell/theme/Yaru/gnome-shell-theme.gresource
    sudo apt-get update
    sudo apt-get install -y "${packages[@]}"
else
    packages=(libglib2.0-bin libglib2.0-dev-bin sassc gnome-shell-common)
    if [ -f /usr/share/gnome-shell/theme/gnome-shell-theme.gresource ]; then
        GDM_RESOURCE=/usr/share/gnome-shell/theme/gnome-shell-theme.gresource
    else
        GDM_RESOURCE=/usr/share/gnome-shell/gnome-shell-theme.gresource
    fi
    sudo apt-get update
    sudo apt-get install -y "${packages[@]}"
fi

if [ ! -f "$GDM_RESOURCE" ]; then
    printf 'The GNOME Shell GDM resource (%s) was not found.\n' "$GDM_RESOURCE" >&2
    exit 1
fi

wall="$HOME/Pictures/Wallpapers/MacTahoe/MacTahoe-night.jpeg"
if [ ! -f "$wall" ]; then
    wall="$ROOT_DIR/assets/wallpapers/MacTahoe-night.jpeg"
fi

generated_css=()
for variant in light dark high-contrast; do
    css="$GDM_DIR/theme/gnome-shell-$variant.css"
    if [ ! -e "$css" ]; then generated_css+=("$css"); fi
done
cleanup_generated_css() {
    local css
    for css in "${generated_css[@]}"; do rm -f "$css"; done
}
trap cleanup_generated_css EXIT

(cd "$GDM_DIR" && ./parse-sass.sh)
tmp_dir="$(mktemp -d)"
trap 'cleanup_generated_css; rm -rf "$tmp_dir"' EXIT
glib-compile-resources --sourcedir="$GDM_DIR/theme" \
    --target="$tmp_dir/gdm-theme.gresource" "$GDM_DIR/gnome-shell-theme.gresource.xml"
gresource list "$tmp_dir/gdm-theme.gresource" >/dev/null

sudo "$GTK_THEME_DIR/tweaks.sh" -g -i apple -b "$wall"
if command -v restorecon >/dev/null 2>&1; then
    sudo restorecon -v "$GDM_RESOURCE"* 2>/dev/null || true
fi
mkdir -p "$HOME/.local/state/mactahoe-ubuntu"
touch "$HOME/.local/state/mactahoe-ubuntu/gdm-installed"
printf 'GDM login theme installed. Reboot to apply it.\n'
