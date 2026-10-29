#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [ "$#" -ne 0 ]; then
    printf 'Usage: %s\n' "$0" >&2
    exit 2
fi

if [ "$EUID" -eq 0 ]; then
    printf 'Run as your normal user, without sudo.\n' >&2
    exit 1
fi
if [ ! -r /etc/os-release ] || ! command -v gsettings >/dev/null 2>&1; then
    printf 'This installer requires Ubuntu, Debian, Fedora, or CachyOS/Arch and a running GNOME session.\n' >&2
    exit 1
fi
. /etc/os-release
distribution_id="${ID:-}"
distribution_like="${ID_LIKE:-}"
if [ "$distribution_id" != ubuntu ] && [ "$distribution_id" != debian ] && \
   [ "$distribution_id" != fedora ] && [ "$distribution_id" != cachyos ] && \
   [ "$distribution_id" != arch ] && [[ ! "$distribution_like" =~ arch ]]; then
    printf 'This installer currently supports Ubuntu, Debian, Fedora, and CachyOS/Arch; detected %s (%s).\n' \
        "${PRETTY_NAME:-unknown}" "$distribution_id" >&2
    exit 1
fi
if [ "$distribution_id" = fedora ]; then
    if ! command -v dnf >/dev/null 2>&1; then
        printf 'Package manager dnf was not found.\n' >&2
        exit 1
    fi
elif [ "$distribution_id" = cachyos ] || [ "$distribution_id" = arch ] || [[ "$distribution_like" =~ arch ]]; then
    if ! command -v pacman >/dev/null 2>&1; then
        printf 'Package manager pacman was not found.\n' >&2
        exit 1
    fi
else
    if ! command -v apt-get >/dev/null 2>&1; then
        printf 'Package manager apt-get was not found.\n' >&2
        exit 1
    fi
fi
shell_major="$(gnome-shell --version | grep -oE '[0-9]+' | head -n1)"
if [ -z "$shell_major" ] || [ "$shell_major" -lt 48 ]; then
    printf 'This installer requires GNOME Shell 48 or newer; detected %s.\n' "${shell_major:-unknown}" >&2
    exit 1
fi
for firefox_process in firefox firefox-bin firefox-esr; do
    if pgrep -u "$UID" -x "$firefox_process" >/dev/null 2>&1; then
        printf 'Force-closing Firefox before installing its profile theme...\n' >&2
        pkill -KILL -u "$UID" -x "$firefox_process" || true
    fi
done
sleep 1
for firefox_process in firefox firefox-bin firefox-esr; do
    if pgrep -u "$UID" -x "$firefox_process" >/dev/null 2>&1; then
        printf 'Could not stop Firefox; close it manually and run the installer again.\n' >&2
        exit 1
    fi
done

STATE_DIR="$HOME/.local/state/mactahoe-ubuntu"
mkdir -p "$STATE_DIR"
BACKUP_DIR=""
if [ -f "$STATE_DIR/latest-backup" ]; then
    previous_backup="$(cat "$STATE_DIR/latest-backup")"
    if [ -d "$previous_backup" ] && [ "$(dirname "$previous_backup")" = "$STATE_DIR" ]; then
        BACKUP_DIR="$previous_backup"
    fi
fi
if [ -z "$BACKUP_DIR" ]; then
    BACKUP_DIR="$(mktemp -d "$STATE_DIR/backup-$(date +%Y%m%d-%H%M%S)-XXXXXX")"
fi

if [ "$distribution_id" = fedora ]; then
    package_list=(breeze-icon-theme dconf fontconfig \
        libadwaita gtk4 gnome-extensions-app \
        gnome-shell-extension-user-theme gnome-tweaks ImageMagick \
        glib2-devel librsvg2-tools python3-gobject python3-pillow sassc)
    dnf_snapshot="$BACKUP_DIR/dnf-packages-before-mactahoe"
    dnf_installed="$BACKUP_DIR/dnf-packages-installed-by-mactahoe"
    if [ ! -e "$BACKUP_DIR/dnf-tracking-version" ] && [ ! -e "$BACKUP_DIR/dnf-tracking-legacy" ]; then
        if [ -e "$STATE_DIR/project-path" ]; then
            touch "$BACKUP_DIR/dnf-tracking-legacy"
        else
            rpm -qa --qf '%{NAME}\n' | LC_ALL=C sort -u > "$dnf_snapshot"
        fi
    fi
    sudo dnf install -y "${package_list[@]}"
    if [ -f "$dnf_snapshot" ] && [ ! -e "$BACKUP_DIR/dnf-tracking-version" ]; then
        rpm -qa --qf '%{NAME}\n' | LC_ALL=C sort -u > "$BACKUP_DIR/dnf-packages-after-mactahoe"
        awk 'NR==FNR {seen[$0]=1; next} !seen[$0]' "$dnf_snapshot" "$BACKUP_DIR/dnf-packages-after-mactahoe" > "$dnf_installed"
        rm -f "$dnf_snapshot" "$BACKUP_DIR/dnf-packages-after-mactahoe"
        touch "$BACKUP_DIR/dnf-tracking-version"
    fi
elif [ "$distribution_id" = cachyos ] || [ "$distribution_id" = arch ] || [[ "$distribution_like" =~ arch ]]; then
    package_list=(breeze-icons dconf fontconfig \
        libadwaita gtk4 extension-manager \
        gnome-shell-extensions gnome-tweaks imagemagick \
        glib2 glib2-devel librsvg python-gobject python-pillow sassc)
    pacman_snapshot="$BACKUP_DIR/pacman-packages-before-mactahoe"
    pacman_installed="$BACKUP_DIR/pacman-packages-installed-by-mactahoe"
    if [ ! -e "$BACKUP_DIR/pacman-tracking-version" ] && [ ! -e "$BACKUP_DIR/pacman-tracking-legacy" ]; then
        if [ -e "$STATE_DIR/project-path" ]; then
            touch "$BACKUP_DIR/pacman-tracking-legacy"
        else
            pacman -Qq | LC_ALL=C sort -u > "$pacman_snapshot"
        fi
    fi
    sudo pacman -S --needed --noconfirm "${package_list[@]}"
    if [ -f "$pacman_snapshot" ] && [ ! -e "$BACKUP_DIR/pacman-tracking-version" ]; then
        pacman -Qq | LC_ALL=C sort -u > "$BACKUP_DIR/pacman-packages-after-mactahoe"
        awk 'NR==FNR {seen[$0]=1; next} !seen[$0]' "$pacman_snapshot" "$BACKUP_DIR/pacman-packages-after-mactahoe" > "$pacman_installed"
        rm -f "$pacman_snapshot" "$BACKUP_DIR/pacman-packages-after-mactahoe"
        touch "$BACKUP_DIR/pacman-tracking-version"
    fi
else
    package_list=(breeze-icon-theme dconf-cli fontconfig \
        gir1.2-adw-1 gir1.2-gtk-4.0 gnome-shell-extension-manager \
        gnome-shell-extension-user-theme gnome-tweaks imagemagick \
        libglib2.0-dev-bin librsvg2-bin python3-gi python3-pil sassc)
    apt_snapshot="$BACKUP_DIR/apt-packages-before-mactahoe"
    apt_installed="$BACKUP_DIR/apt-packages-installed-by-mactahoe"
    if [ ! -e "$BACKUP_DIR/apt-tracking-version" ] && [ ! -e "$BACKUP_DIR/apt-tracking-legacy" ]; then
        if [ -e "$STATE_DIR/project-path" ]; then
            touch "$BACKUP_DIR/apt-tracking-legacy"
        else
            dpkg-query -W -f='${db:Status-Abbrev}\t${binary:Package}\n' \
                | awk '$1 ~ /^ii/ {print $2}' | LC_ALL=C sort -u > "$apt_snapshot"
        fi
    fi
    sudo apt-get update
    sudo apt-get install -y "${package_list[@]}"
    if [ -f "$apt_snapshot" ] && [ ! -e "$BACKUP_DIR/apt-tracking-version" ]; then
        dpkg-query -W -f='${db:Status-Abbrev}\t${binary:Package}\n' \
            | awk '$1 ~ /^ii/ {print $2}' | LC_ALL=C sort -u > "$BACKUP_DIR/apt-packages-after-mactahoe"
        awk 'NR==FNR {seen[$0]=1; next} !seen[$0]' "$apt_snapshot" "$BACKUP_DIR/apt-packages-after-mactahoe" > "$apt_installed"
        rm -f "$apt_snapshot" "$BACKUP_DIR/apt-packages-after-mactahoe"
        touch "$BACKUP_DIR/apt-tracking-version"
    fi
fi

mkdir -p "$HOME/.local/share/gnome-shell/extensions" \
    "$HOME/.local/share/fonts" "$HOME/.local/bin" "$HOME/.local/share/applications" \
    "$HOME/.config/systemd/user" \
    "$HOME/.local/share/mactahoe-apps" \
    "$HOME/.local/share/icons/hicolor/scalable/apps" \
    "$HOME/Pictures/Wallpapers/MacTahoe"

if command -v dconf >/dev/null 2>&1 && [ ! -f "$BACKUP_DIR/dconf-before.ini" ]; then
    dconf dump / > "$BACKUP_DIR/dconf-before.ini" || true
fi
for path in gtk-3.0 gtk-4.0; do
    if [ ! -e "$BACKUP_DIR/captured/.config/$path" ]; then
        mkdir -p "$BACKUP_DIR/captured/.config"
        if [ -e "$HOME/.config/$path" ] && [ ! -e "$BACKUP_DIR/$path" ]; then
            cp -a "$HOME/.config/$path" "$BACKUP_DIR/"
        fi
        touch "$BACKUP_DIR/captured/.config/$path"
    fi
done
backup_item() {
    local relative="$1" backup_path="$BACKUP_DIR/home/$1" captured="$BACKUP_DIR/captured/home/$1"
    if [ ! -e "$captured" ]; then
        mkdir -p "$BACKUP_DIR/captured/home/$(dirname "$relative")"
        if { [ -e "$HOME/$relative" ] || [ -L "$HOME/$relative" ]; } && \
            [ ! -e "$backup_path" ] && [ ! -L "$backup_path" ]; then
            mkdir -p "$BACKUP_DIR/home/$(dirname "$relative")"
            cp -a "$HOME/$relative" "$backup_path"
        fi
        touch "$captured"
    fi
}
for relative in \
    .local/bin/mactahoe-icon-manager \
    .local/bin/am-lich-viet-nam .local/bin/image-compressor \
    .local/bin/mactahoe-app-themer \
    .local/bin/color-scheme-sync.sh .local/share/fonts/MacTahoe \
    .local/share/applications/mactahoe-icon-manager.desktop \
    .local/share/applications/vn.ihoan.AmLich.desktop \
    .local/share/applications/vn.ihoan.ImageCompressor.desktop \
    .local/share/applications/io.github.adfoxtheme.MacTahoeAppThemer.desktop \
    .local/share/mactahoe-apps/am-lich-viet-nam \
    .local/share/mactahoe-apps/image-compressor \
    .local/share/mactahoe-apps/mactahoe-app-themer \
    .local/share/icons/hicolor/scalable/apps/vn.ihoan.AmLich.svg \
    .local/share/icons/hicolor/scalable/apps/vn.ihoan.ImageCompressor.svg \
    .local/share/icons/hicolor/scalable/apps/io.github.adfoxtheme.MacTahoeAppThemer.svg \
    .config/systemd/user/color-scheme-sync.service \
    Pictures/Wallpapers/MacTahoe; do
    backup_item "$relative"
done
if [ ! -e "$BACKUP_DIR/captured/theme-icons" ]; then
    mkdir -p "$BACKUP_DIR/captured"
    for path in "$HOME"/.themes/MacTahoe-* "$HOME"/.local/share/icons/MacTahoe*; do
        [ ! -e "$path" ] || backup_item "${path#"$HOME"/}"
    done
    touch "$BACKUP_DIR/captured/theme-icons"
fi
printf '%s\n' "$BACKUP_DIR" > "$STATE_DIR/latest-backup"
printf '%s\n' "$ROOT_DIR" > "$STATE_DIR/project-path"

mkdir -p "$HOME/.local/share/fonts/MacTahoe"
cp -a "$ROOT_DIR/assets/fonts/SF-Pro" "$ROOT_DIR/assets/fonts/SF-Mono" \
    "$HOME/.local/share/fonts/MacTahoe/"
fc-cache -f "$HOME/.local/share/fonts/MacTahoe"
(cd "$ROOT_DIR/vendor/MacTahoe-gtk-theme" && ./install.sh -l --shell -i apple -p default)
# Install the full GTK 3/4 theme into ~/.themes so that GTK3 apps and
# Chrome's GtkUi can actually resolve "MacTahoe-Dark". Without this only
# libadwaita apps get themed (via the gtk-4.0 config override) and browsers
# like Google Chrome end up with a mixed light/dark UI.
(cd "$ROOT_DIR/vendor/MacTahoe-gtk-theme" && ./install.sh -d "$HOME/.themes" -c dark)
(cd "$ROOT_DIR/vendor/MacTahoe-icon-theme" && ./install.sh -t blue)
mkdir -p "$HOME/.local/share/icons/MacTahoe-cursors" "$HOME/.local/share/icons/MacTahoe-dark-cursors"
cp -a "$ROOT_DIR/vendor/MacTahoe-icon-theme/cursors/dist/." "$HOME/.local/share/icons/MacTahoe-cursors/"
cp -a "$ROOT_DIR/vendor/MacTahoe-icon-theme/cursors/dist-dark/." "$HOME/.local/share/icons/MacTahoe-dark-cursors/"
cp -a "$ROOT_DIR/assets/wallpapers/." "$HOME/Pictures/Wallpapers/MacTahoe/"

cp "$ROOT_DIR/apps/mactahoe-icon-manager" \
    "$ROOT_DIR/apps/color-scheme-sync.sh" "$HOME/.local/bin/"
cp "$ROOT_DIR/apps/launchers/am-lich-viet-nam" \
    "$ROOT_DIR/apps/launchers/image-compressor" \
    "$ROOT_DIR/apps/launchers/mactahoe-app-themer" "$HOME/.local/bin/"
chmod +x "$HOME/.local/bin/mactahoe-icon-manager" \
    "$HOME/.local/bin/am-lich-viet-nam" "$HOME/.local/bin/image-compressor" \
    "$HOME/.local/bin/mactahoe-app-themer" \
    "$HOME/.local/bin/color-scheme-sync.sh"
mkdir -p "$HOME/.local/share/mactahoe-apps/am-lich-viet-nam" \
    "$HOME/.local/share/mactahoe-apps/image-compressor" \
    "$HOME/.local/share/mactahoe-apps/mactahoe-app-themer"
cp -a "$ROOT_DIR/apps/am-lich-viet-nam/." \
    "$HOME/.local/share/mactahoe-apps/am-lich-viet-nam/"
cp -a "$ROOT_DIR/apps/image-compressor/." \
    "$HOME/.local/share/mactahoe-apps/image-compressor/"
cp -a "$ROOT_DIR/apps/mactahoe-app-themer/." \
    "$HOME/.local/share/mactahoe-apps/mactahoe-app-themer/"
cp "$ROOT_DIR/apps/am-lich-viet-nam/assets/vn.ihoan.AmLich.svg" \
    "$HOME/.local/share/icons/hicolor/scalable/apps/"
cp "$ROOT_DIR/apps/image-compressor/assets/vn.ihoan.ImageCompressor.svg" \
    "$HOME/.local/share/icons/hicolor/scalable/apps/"
cp "$ROOT_DIR/apps/mactahoe-app-themer/assets/io.github.adfoxtheme.MacTahoeAppThemer.svg" \
    "$HOME/.local/share/icons/hicolor/scalable/apps/"

EXTENSION_IDS=(UbuntuTahoe@adfoxtheme.github.io UbuntuTahoeDock@adfoxtheme.github.io UbuntuTahoeWidgets@adfoxtheme.github.io)
COMPATIBLE_EXTENSION_IDS=()
INCOMPATIBLE_EXTENSION_IDS=(blur-my-shell@aunetx globalmenu@ShiroOSL.github.io \
    just-perfection-desktop@just-perfection kimpanel@kde.org \
    ubuntu-dock@ubuntu.com dash-to-dock@micxgx.gmail.com)
for leg in "${INCOMPATIBLE_EXTENSION_IDS[@]}"; do
    gnome-extensions disable "$leg" 2>/dev/null || true
done
for uuid in "${EXTENSION_IDS[@]}"; do
    if ! python3 -c 'import json, sys; data = json.load(open(sys.argv[1], encoding="utf-8")); sys.exit(0 if sys.argv[2] in data.get("shell-version", []) else 1)' \
        "$ROOT_DIR/vendor/gnome-extensions/$uuid/metadata.json" "$shell_major"; then
        printf 'Skipping %s: it does not declare support for GNOME Shell %s.\n' "$uuid" "$shell_major"
        INCOMPATIBLE_EXTENSION_IDS+=("$uuid")
        continue
    fi
    target="$HOME/.local/share/gnome-shell/extensions/$uuid"
    if [ ! -e "$BACKUP_DIR/captured/extensions/$uuid" ]; then
        mkdir -p "$BACKUP_DIR/captured/extensions"
        if [ -d "$target" ] && [ ! -e "$BACKUP_DIR/extensions/$uuid" ]; then
            mkdir -p "$BACKUP_DIR/extensions"
            cp -a "$target" "$BACKUP_DIR/extensions/"
        fi
        touch "$BACKUP_DIR/captured/extensions/$uuid"
    fi
    mkdir -p "${target%/*}"
    rm -rf "$target"
    cp -a "$ROOT_DIR/vendor/gnome-extensions/$uuid" "$target"
    if [ -d "$target/schemas" ]; then glib-compile-schemas "$target/schemas"; fi
    COMPATIBLE_EXTENSION_IDS+=("$uuid")
done

gs() {
    local schema="$1"; shift
    local command="$1"; shift
    local uuid schema_dir
    case "$schema" in
        org.gnome.shell.extensions.ubuntutahoedock*) uuid=UbuntuTahoeDock@adfoxtheme.github.io ;;
        org.gnome.shell.extensions.ubuntutahoewidgets*) uuid=UbuntuTahoeWidgets@adfoxtheme.github.io ;;
        org.gnome.shell.extensions.ubuntutahoe*|\
        org.gnome.shell.extensions.blur-my-shell*|\
        org.gnome.shell.extensions.globalmenu*|\
        org.gnome.shell.extensions.kimpanel*) uuid=UbuntuTahoe@adfoxtheme.github.io ;;
        *) gsettings "$command" "$schema" "$@"; return $? ;;
    esac
    schema_dir="$HOME/.local/share/gnome-shell/extensions/$uuid/schemas"
    GSETTINGS_SCHEMA_DIR="$schema_dir" gsettings "$command" "$schema" "$@"
}

while read -r schema key value; do
    [ -n "${schema:-}" ] || continue
    if gs "$schema" writable "$key" >/dev/null 2>&1; then gs "$schema" set "$key" "$value"; fi
done < "$ROOT_DIR/config/gsettings.tsv"

wall="$HOME/Pictures/Wallpapers/MacTahoe/MacTahoe-night.jpeg"
wall_uri="$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).as_uri())' "$wall")"
gsettings set org.gnome.desktop.background picture-uri "$wall_uri"
gsettings set org.gnome.desktop.background picture-uri-dark "$wall_uri"
gsettings set org.gnome.desktop.background picture-options 'zoom'
gsettings set org.gnome.desktop.screensaver picture-uri "$wall_uri"
gsettings set org.gnome.desktop.screensaver picture-options 'zoom'

extension_ids=(user-theme@gnome-shell-extensions.gcampax.github.com)
for uuid in "${COMPATIBLE_EXTENSION_IDS[@]}"; do
    extension_ids+=("$uuid")
done
python3 - "${extension_ids[@]}" -- -- "${INCOMPATIBLE_EXTENSION_IDS[@]}" <<'PY'
import ast
import subprocess
import sys

schema = "org.gnome.shell"
key = "enabled-extensions"
raw_enabled = subprocess.check_output(["gsettings", "get", schema, key], text=True).strip()
enabled = ast.literal_eval(raw_enabled.removeprefix("@as "))
first_separator = sys.argv.index("--")
second_separator = sys.argv.index("--", first_separator + 1)
required = sys.argv[1:first_separator]
disabled = sys.argv[first_separator + 1:second_separator]
incompatible = sys.argv[second_separator + 1:]
enabled = [uuid for uuid in enabled if uuid not in disabled and uuid not in incompatible]
for uuid in required:
    if uuid not in enabled:
        enabled.append(uuid)
variant = "[" + ", ".join(repr(uuid) for uuid in enabled) + "]"
subprocess.run(["gsettings", "set", schema, key, variant], check=True)
PY

cp "$ROOT_DIR/desktop/mactahoe-icon-manager.desktop" "$HOME/.local/share/applications/"
sed "s|^Exec=am-lich-viet-nam$|Exec=$HOME/.local/bin/am-lich-viet-nam|" \
    "$ROOT_DIR/desktop/vn.ihoan.AmLich.desktop" \
    > "$HOME/.local/share/applications/vn.ihoan.AmLich.desktop"
sed "s|^Exec=image-compressor$|Exec=$HOME/.local/bin/image-compressor|" \
    "$ROOT_DIR/desktop/vn.ihoan.ImageCompressor.desktop" \
    > "$HOME/.local/share/applications/vn.ihoan.ImageCompressor.desktop"
sed "s|^Exec=mactahoe-app-themer$|Exec=$HOME/.local/bin/mactahoe-app-themer|" \
    "$ROOT_DIR/desktop/io.github.adfoxtheme.MacTahoeAppThemer.desktop" \
    > "$HOME/.local/share/applications/io.github.adfoxtheme.MacTahoeAppThemer.desktop"
cp "$ROOT_DIR/systemd/color-scheme-sync.service" "$HOME/.config/systemd/user/"
systemctl --user daemon-reload
systemctl --user enable --now color-scheme-sync.service

# Khởi tạo profile mặc định nếu Firefox (DEB/APT/RPM/Pacman) chưa từng mở
if [ -f /etc/debian_version ] || [ -f /etc/fedora-release ] || [ -f /etc/arch-release ] || [ -f /etc/cachyos-release ] || \
   { command -v lsb_release >/dev/null 2>&1 && lsb_release -i | grep -qiE 'debian|fedora|arch|cachy'; }; then
    for ff_cmd in firefox firefox-esr; do
        if command -v "$ff_cmd" >/dev/null 2>&1 && [ ! -d "$HOME/snap/firefox" ]; then
            "$ff_cmd" --headless -screenshot /dev/null about:blank >/dev/null 2>&1 || true
            break
        fi
    done
fi

for firefox_root in \
    "${XDG_CONFIG_HOME:-$HOME/.config}/mozilla/firefox" \
    "$HOME/.mozilla/firefox" \
    "$HOME/.var/app/org.mozilla.firefox/.mozilla/firefox" \
    "$HOME/snap/firefox/common/.mozilla/firefox"; do
    [ -d "$firefox_root" ] || continue

    profile_dirs=()
    if [ -f "$firefox_root/profiles.ini" ]; then
        while IFS='=' read -r key val; do
            [ "$key" = "Path" ] || continue
            val="$(echo "$val" | tr -d '\r')"
            case "$val" in
                /*) p="$val" ;;
                *)  p="$firefox_root/$val" ;;
            esac
            [ -d "$p" ] && profile_dirs+=("$p")
        done < "$firefox_root/profiles.ini"
    fi
    while IFS= read -r -d '' prefs; do
        profile_dirs+=("${prefs%/prefs.js}")
    done < <(find "$firefox_root" -mindepth 2 -maxdepth 4 -type f -name prefs.js -print0)

    unset seen_profiles
    declare -A seen_profiles=()
    for profile in "${profile_dirs[@]}"; do
        [ -n "$profile" ] && [ -d "$profile" ] || continue
        [ -z "${seen_profiles["$profile"]:-}" ] || continue
        seen_profiles["$profile"]=1

        chrome="$profile/chrome"
        if [ -d "$chrome" ] && [ ! -e "$profile/chrome.mactahoe-backup" ]; then
            cp -a "$chrome" "$profile/chrome.mactahoe-backup"
        fi
        mkdir -p "$chrome"
        cp -a "$ROOT_DIR/vendor/MacTahoe-gtk-theme/other/firefox/MacTahoe" "$chrome/"
        cp "$ROOT_DIR/vendor/MacTahoe-gtk-theme/other/firefox/customChrome.css" \
            "$ROOT_DIR/vendor/MacTahoe-gtk-theme/other/firefox/userChrome.css" \
            "$ROOT_DIR/vendor/MacTahoe-gtk-theme/other/firefox/userContent.css" "$chrome/"
        if [ -f "$profile/user.js" ]; then
            cp -n "$profile/user.js" "$profile/user.js.mactahoe-backup"
        else
            touch "$profile/user.js"
        fi
        while IFS= read -r pref; do
            grep -Fqx "$pref" "$profile/user.js" || printf '%s\n' "$pref" >> "$profile/user.js"
        done < "$ROOT_DIR/config/firefox-user.js"
    done
done

if [ -d "$HOME/snap/firefox" ]; then
    mkdir -p "$HOME/snap/firefox/common/.config/gtk-3.0" "$HOME/snap/firefox/common/.themes"
    cp "$ROOT_DIR/config/gtk-snap.css" "$HOME/snap/firefox/common/.config/gtk-3.0/gtk.css"
    for snap_dir in "$HOME/snap/firefox/"*/; do
        snap_ver="$(basename "$snap_dir")"
        if [ "$snap_ver" != "common" ] && [ "$snap_ver" != "current" ] && [ -d "$snap_dir/.config" ]; then
            mkdir -p "$snap_dir/.config/gtk-3.0"
            rm -f "$snap_dir/.config/gtk-3.0/gtk.css"
            cp "$ROOT_DIR/config/gtk-snap.css" "$snap_dir/.config/gtk-3.0/gtk.css"
        fi
    done
    if [ -d "$HOME/.themes/MacTahoe-Dark" ]; then
        cp -a "$HOME/.themes/MacTahoe-Dark" "$HOME/snap/firefox/common/.themes/"
    fi
fi

update-desktop-database "$HOME/.local/share/applications" || true
printf '\nInstalled. Log out and back in to load GNOME Shell extensions.\nBackup: %s\n' "$BACKUP_DIR"
