#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [ "$EUID" -eq 0 ]; then
    printf 'Run this uninstaller as your normal user, without sudo.\n' >&2
    exit 1
fi

STATE_DIR="$HOME/.local/state/mactahoe-ubuntu"
BACKUP_DIR=""
if [ -f "$STATE_DIR/latest-backup" ]; then
    candidate="$(cat "$STATE_DIR/latest-backup")"
    if [ -n "$candidate" ] && [ -d "$candidate" ]; then
        BACKUP_DIR="$candidate"
    fi
fi
if [ -n "$BACKUP_DIR" ] && [ -d "$BACKUP_DIR/xfconf" ]; then
    if ! command -v xfconf-query >/dev/null 2>&1 ||
       ! xfconf-query -c xsettings -l >/dev/null 2>&1; then
        printf 'Run uninstall.sh from Xfce to restore its settings before removing the theme.\n' >&2
        exit 1
    fi
fi
ICON_MANAGER_DIR="$HOME/.local/share/mactahoe-icon-manager"
LOCAL_APPLICATIONS="$HOME/.local/share/applications"

restore_item() {
    local relative="$1"
    local target="$HOME/$relative"
    local backup="$BACKUP_DIR/home/$relative"
    if [ -n "$BACKUP_DIR" ] && [ -e "$backup" ]; then
        rm -rf "$target"
        mkdir -p "$(dirname "$target")"
        cp -a "$backup" "$target"
    else
        rm -rf "$target"
    fi
}

# Stop only the Tahoe instances before restoring their launchers.
if [ -f "$BACKUP_DIR/plank-before.ini" ]; then
    "$HOME/.local/bin/mactahoe-xfce-widgets" --stop 2>/dev/null || true
    "$HOME/.local/bin/mactahoe-xfce-dock" stop 2>/dev/null || true
    dconf reset -f /net/launchpad/plank/docks/mactahoe/
    dconf load /net/launchpad/plank/docks/mactahoe/ < "$BACKUP_DIR/plank-before.ini"
    for relative in \
        .local/bin/mactahoe-xfce-widgets .local/bin/mactahoe-xfce-dock \
        .local/share/mactahoe-apps/mactahoe-xfce-widgets \
        .local/share/applications/io.github.adfoxtheme.XfceWidgets.desktop \
        .local/share/applications/io.github.adfoxtheme.Launchpad.desktop \
        .config/autostart/mactahoe-xfce-widgets.desktop \
        .config/autostart/mactahoe-xfce-dock.desktop \
        .config/plank/mactahoe .local/share/plank/themes/MacTahoe; do
        restore_item "$relative"
    done
fi
# The LightDM installer keeps a system backup so it can be restored from a TTY.
if [ -f "$STATE_DIR/lightdm-installed" ]; then
    "$ROOT_DIR/install-lightdm.sh" --uninstall
fi

# 1. Dừng các tiến trình và dịch vụ
systemctl --user disable --now color-scheme-sync.service 2>/dev/null || true
rm -f "$HOME/.config/systemd/user/color-scheme-sync.service"
systemctl --user daemon-reload 2>/dev/null || true
"$HOME/.local/bin/mactahoe-widgets" stop 2>/dev/null || true
rm -rf "$HOME/.cache/mactahoe-widgets"

# 2. Khôi phục icon ứng dụng đã sửa bởi Icon Manager
if [ -d "$ICON_MANAGER_DIR/backups" ]; then
    mkdir -p "$LOCAL_APPLICATIONS"
    for backup in "$ICON_MANAGER_DIR"/backups/*.desktop.bak; do
        [ -f "$backup" ] || continue
        desktop_id="${backup##*/}"
        desktop_id="${desktop_id%.bak}"
        rm -f "$LOCAL_APPLICATIONS/$desktop_id"
        cp -a "$backup" "$LOCAL_APPLICATIONS/$desktop_id"
    done
fi
if [ -d "$LOCAL_APPLICATIONS" ]; then
    for desktop_file in "$LOCAL_APPLICATIONS"/*.desktop; do
        [ -f "$desktop_file" ] || continue
        if grep -Fq "$ICON_MANAGER_DIR/icons/" "$desktop_file"; then
            rm -f "$desktop_file"
        fi
    done
fi
rm -rf "$ICON_MANAGER_DIR"

# 3. Gỡ bỏ các ứng dụng, binary, file .desktop và dữ liệu của MacTahoe
for path in .local/bin/mactahoe-icon-manager \
    .local/bin/am-lich-viet-nam .local/bin/image-compressor \
    .local/bin/mactahoe-app-themer \
    .local/bin/gnome-theme-switcher \
    .local/bin/color-scheme-sync.sh \
    .local/share/applications/mactahoe-icon-manager.desktop \
    .local/share/applications/org.gnome.GTK4ThemeSwitcher.desktop \
    .local/share/applications/vn.ihoan.AmLich.desktop \
    .local/share/applications/vn.ihoan.ImageCompressor.desktop \
    .local/share/applications/io.github.adfoxtheme.MacTahoeAppThemer.desktop \
    .local/share/mactahoe-apps/am-lich-viet-nam \
    .local/share/mactahoe-apps/image-compressor \
    .local/share/mactahoe-apps/mactahoe-app-themer \
    .local/share/icons/hicolor/scalable/apps/vn.ihoan.AmLich.svg \
    .local/share/icons/hicolor/scalable/apps/vn.ihoan.ImageCompressor.svg \
    .local/share/icons/hicolor/scalable/apps/io.github.adfoxtheme.MacTahoeAppThemer.svg \
    .config/systemd/user/color-scheme-sync.service; do
    restore_item "$path"
done

if [ ! -f "$BACKUP_DIR/xfce-only" ]; then
# 4. Gỡ extension GNOME Shell
for uuid in UbuntuTahoe@adfoxtheme.github.io UbuntuTahoeDock@adfoxtheme.github.io \
    UbuntuTahoeWidgets@adfoxtheme.github.io \
    blur-my-shell@aunetx globalmenu@ShiroOSL.github.io \
    just-perfection-desktop@just-perfection kimpanel@kde.org; do
    gnome-extensions disable "$uuid" 2>/dev/null || true
    if [ -d "$HOME/.local/share/gnome-shell/extensions/$uuid" ]; then
        rm -rf "$HOME/.local/share/gnome-shell/extensions/$uuid"
        if [ -n "$BACKUP_DIR" ] && [ -d "$BACKUP_DIR/extensions/$uuid" ]; then
            cp -a "$BACKUP_DIR/extensions/$uuid" "$HOME/.local/share/gnome-shell/extensions/"
        fi
    fi
done
gnome-extensions enable ubuntu-dock@ubuntu.com 2>/dev/null || true
gnome-extensions enable dash-to-dock@micxgx.gmail.com 2>/dev/null || true

fi

# 6. Đóng và khôi phục cấu hình Firefox
for firefox_process in firefox firefox-bin firefox-esr; do
    if pgrep -u "$UID" -x "$firefox_process" >/dev/null 2>&1; then
        printf 'Closing Firefox before reverting profile theme...\n' >&2
        pkill -KILL -u "$UID" -x "$firefox_process" || true
    fi
done
sleep 1

for profile_root in \
    "${XDG_CONFIG_HOME:-$HOME/.config}/mozilla/firefox" \
    "$HOME/.mozilla/firefox" \
    "$HOME/.var/app/org.mozilla.firefox/.mozilla/firefox" \
    "$HOME/snap/firefox/common/.mozilla/firefox"; do
    [ -d "$profile_root" ] || continue

    profile_dirs=()
    if [ -f "$profile_root/profiles.ini" ]; then
        while IFS='=' read -r key val; do
            [ "$key" = "Path" ] || continue
            val="$(echo "$val" | tr -d '\r')"
            case "$val" in
                /*) p="$val" ;;
                *)  p="$profile_root/$val" ;;
            esac
            [ -d "$p" ] && profile_dirs+=("$p")
        done < "$profile_root/profiles.ini"
    fi
    while IFS= read -r -d '' prefs; do
        profile_dirs+=("${prefs%/prefs.js}")
    done < <(find "$profile_root" -mindepth 2 -maxdepth 4 -type f -name prefs.js -print0)

    unset seen_profiles
    declare -A seen_profiles=()
    for profile in "${profile_dirs[@]}"; do
        [ -n "$profile" ] && [ -d "$profile" ] || continue
        [ -z "${seen_profiles["$profile"]:-}" ] || continue
        seen_profiles["$profile"]=1

        if [ -f "$profile/user.js.mactahoe-backup" ]; then
            mv "$profile/user.js.mactahoe-backup" "$profile/user.js"
        elif [ -f "$profile/user.js" ] && [ -r "$ROOT_DIR/config/firefox-user.js" ]; then
            grep -Fvx -f "$ROOT_DIR/config/firefox-user.js" "$profile/user.js" > "$profile/user.js.tmp" || true
            mv "$profile/user.js.tmp" "$profile/user.js"
            [ -s "$profile/user.js" ] || rm -f "$profile/user.js"
        fi
        if [ -d "$profile/chrome.mactahoe-backup" ]; then
            rm -rf "$profile/chrome"
            mv "$profile/chrome.mactahoe-backup" "$profile/chrome"
        else
            rm -rf "$profile/chrome/MacTahoe"
            rm -f "$profile/chrome/customChrome.css" "$profile/chrome/userChrome.css" \
                "$profile/chrome/userContent.css"
            rmdir "$profile/chrome" 2>/dev/null || true
        fi
    done
done

if [ -d "$HOME/snap/firefox" ]; then
    rm -f "$HOME/snap/firefox/common/.config/gtk-3.0/gtk.css"
    rm -rf "$HOME/snap/firefox/common/.themes/MacTahoe-Dark"
    for snap_dir in "$HOME/snap/firefox/"*/; do
        snap_ver="$(basename "$snap_dir")"
        if [ "$snap_ver" != "common" ] && [ "$snap_ver" != "current" ]; then
            rm -f "$snap_dir/.config/gtk-3.0/gtk.css"
        fi
    done
fi

# 7. Gỡ theme vendor (Chạy trước khi restore GTK để không xóa nhầm file người dùng)
(cd "$ROOT_DIR/vendor/MacTahoe-gtk-theme" && ./install.sh -r theme app || true)
(cd "$ROOT_DIR/vendor/MacTahoe-icon-theme" && ./install.sh -r || true)
rm -rf "$HOME/.local/share/icons/MacTahoe-cursors" "$HOME/.local/share/icons/MacTahoe-dark-cursors"
if [ -f "$STATE_DIR/gdm-installed" ]; then
    sudo "$ROOT_DIR/vendor/MacTahoe-gtk-theme/tweaks.sh" -g -r || true
    if command -v restorecon >/dev/null 2>&1; then
        sudo restorecon -v /usr/share/gnome-shell/gnome-shell-theme.gresource* \
            /usr/share/gnome-shell/theme/gnome-shell-theme.gresource* \
            /usr/share/gnome-shell/theme/Yaru/gnome-shell-theme.gresource* 2>/dev/null || true
    fi
    rm -f "$STATE_DIR/gdm-installed"
fi

# 8. Khôi phục cấu hình GTK 3 & GTK 4 từ bản sao lưu
if [ -n "$BACKUP_DIR" ] && [ -d "$BACKUP_DIR" ]; then
    for path in gtk-3.0 gtk-4.0; do
        if [ -d "$BACKUP_DIR/$path" ]; then
            rm -rf "$HOME/.config/$path"
            cp -a "$BACKUP_DIR/$path" "$HOME/.config/"
        fi
    done
fi

# 9. Gỡ hình nền MacTahoe (Giữ lại phông chữ để đảm bảo hệ thống luôn hiển thị đẹp, không bị lỗi ô vuông)
if [ -d "$HOME/Pictures/Wallpapers/MacTahoe" ]; then
    if [ -d "$ROOT_DIR/assets/wallpapers" ]; then
        for wp in "$ROOT_DIR"/assets/wallpapers/*; do
            [ -e "$wp" ] || continue
            rm -f "$HOME/Pictures/Wallpapers/MacTahoe/${wp##*/}"
        done
    else
        rm -f "$HOME/Pictures/Wallpapers/MacTahoe/MacTahoe-day.jpeg" \
             "$HOME/Pictures/Wallpapers/MacTahoe/MacTahoe-night.jpeg"
    fi
    rmdir "$HOME/Pictures/Wallpapers/MacTahoe" 2>/dev/null || true
fi

if [ -n "$BACKUP_DIR" ] && [ -d "$BACKUP_DIR/xfconf" ]; then
    source "$ROOT_DIR/scripts/desktop.sh"
    restore_xfce
    if [ -e "$BACKUP_DIR/captured/home/.config/xfce4/panel" ]; then
        restore_item .config/xfce4/panel
    fi
fi

# 10. Khôi phục hoặc reset cài đặt GNOME (dconf/gsettings)
reset_gnome_settings() {
    if [ -r "$ROOT_DIR/config/gsettings.tsv" ]; then
        while read -r schema key value; do
            [ -n "${schema:-}" ] || continue
            case "$schema" in
                org.gnome.shell.extensions.ubuntutahoedock*) uuid=UbuntuTahoeDock@adfoxtheme.github.io ;;
                org.gnome.shell.extensions.ubuntutahoewidgets*) uuid=UbuntuTahoeWidgets@adfoxtheme.github.io ;;
                org.gnome.shell.extensions.ubuntutahoe*|\
                org.gnome.shell.extensions.blur-my-shell*|\
                org.gnome.shell.extensions.globalmenu*|\
                org.gnome.shell.extensions.kimpanel*) uuid=UbuntuTahoe@adfoxtheme.github.io ;;
                *) uuid="" ;;
            esac
            if [ -n "$uuid" ] && [ -d "$ROOT_DIR/vendor/gnome-extensions/$uuid/schemas" ]; then
                GSETTINGS_SCHEMA_DIR="$ROOT_DIR/vendor/gnome-extensions/$uuid/schemas" \
                    gsettings reset "$schema" "$key" 2>/dev/null || true
            else
                gsettings reset "$schema" "$key" 2>/dev/null || true
            fi
            if command -v dconf >/dev/null 2>&1; then
                dconf reset "/${schema//.//}/${key}" 2>/dev/null || true
            fi
        done < "$ROOT_DIR/config/gsettings.tsv"
    fi
    gsettings reset org.gnome.desktop.background picture-uri 2>/dev/null || true
    gsettings reset org.gnome.desktop.background picture-uri-dark 2>/dev/null || true
    gsettings reset org.gnome.desktop.screensaver picture-uri 2>/dev/null || true
    gsettings reset org.gnome.desktop.background picture-options 2>/dev/null || true
    gsettings reset org.gnome.desktop.screensaver picture-options 2>/dev/null || true
}

if [ -n "$BACKUP_DIR" ] && [ -f "$BACKUP_DIR/dconf-before.ini" ]; then
    printf 'Restore the complete pre-install GNOME settings backup? [Y/n] '
    read -r answer || true
    if [[ ! "$answer" =~ ^[Nn]$ ]]; then
        for path in /org/gnome/desktop/interface/ /org/gnome/desktop/background/ \
            /org/gnome/desktop/screensaver/ /org/gnome/desktop/wm/preferences/ \
            /org/gnome/shell/; do
            dconf reset -f "$path" 2>/dev/null || true
        done
        dconf load / < "$BACKUP_DIR/dconf-before.ini"
    else
        reset_gnome_settings
    fi
elif [ ! -f "$BACKUP_DIR/xfce-only" ]; then
    reset_gnome_settings
fi

# 11. Gỡ bỏ các gói hệ thống do MacTahoe cài vào (Giữ lại tuyệt đối fontconfig và các gói phông chữ)
if [ -n "$BACKUP_DIR" ] && [ -f "$BACKUP_DIR/pacman-packages-installed-by-mactahoe" ]; then
    mapfile -t pacman_packages_to_remove < <(
        while IFS= read -r package; do
            [ -n "$package" ] || continue
            # Giữ lại fontconfig và các gói phông chữ hệ thống
            [ "$package" != "fontconfig" ] || continue
            [[ "$package" == *font* ]] && continue
            pacman -Q "$package" >/dev/null 2>&1 && printf '%s\n' "$package"
        done < "$BACKUP_DIR/pacman-packages-installed-by-mactahoe"
    )
    if [ "${#pacman_packages_to_remove[@]}" -gt 0 ]; then
        printf 'Removing pacman packages newly installed by MacTahoe: %s\n' "${pacman_packages_to_remove[*]}"
        sudo pacman -R --noconfirm "${pacman_packages_to_remove[@]}" || true
    fi
elif [ -n "$BACKUP_DIR" ] && [ -f "$BACKUP_DIR/pacman-tracking-legacy" ]; then
    legacy_pacman_packages=(breeze-icons dconf \
        libadwaita gtk4 extension-manager \
        gnome-shell-extensions gnome-tweaks imagemagick \
        glib2 glib2-devel librsvg python-gobject python-pillow sassc)
    printf 'This installation predates package tracking. Remove installed MacTahoe package-list items?\n'
    printf 'This may also remove packages that were installed before MacTahoe. [Y/n] '
    read -r answer || true
    if [[ ! "$answer" =~ ^[Nn]$ ]]; then
        installed_legacy_pacman_packages=()
        for package in "${legacy_pacman_packages[@]}"; do
            [ "$package" != "fontconfig" ] || continue
            [[ "$package" == *font* ]] && continue
            pacman -Q "$package" >/dev/null 2>&1 && installed_legacy_pacman_packages+=("$package")
        done
        if [ "${#installed_legacy_pacman_packages[@]}" -gt 0 ]; then
            sudo pacman -R --noconfirm "${installed_legacy_pacman_packages[@]}" || true
        fi
    fi
elif [ -n "$BACKUP_DIR" ] && [ -f "$BACKUP_DIR/dnf-packages-installed-by-mactahoe" ]; then
    mapfile -t dnf_packages_to_remove < <(
        while IFS= read -r package; do
            [ -n "$package" ] || continue
            # Giữ lại fontconfig và các gói phông chữ hệ thống
            [ "$package" != "fontconfig" ] || continue
            [[ "$package" == *font* ]] && continue
            rpm -q --quiet "$package" 2>/dev/null && printf '%s\n' "$package"
        done < "$BACKUP_DIR/dnf-packages-installed-by-mactahoe"
    )
    if [ "${#dnf_packages_to_remove[@]}" -gt 0 ]; then
        printf 'Removing dnf packages newly installed by MacTahoe: %s\n' "${dnf_packages_to_remove[*]}"
        sudo dnf remove -y "${dnf_packages_to_remove[@]}" || true
        sudo dnf autoremove -y 2>/dev/null || true
    fi
elif [ -n "$BACKUP_DIR" ] && [ -f "$BACKUP_DIR/dnf-tracking-legacy" ]; then
    legacy_dnf_packages=(breeze-icon-theme dconf \
        libadwaita gtk4 gnome-extensions-app \
        gnome-shell-extension-user-theme gnome-tweaks ImageMagick \
        glib2-devel librsvg2-tools python3-gobject python3-pillow sassc)
    printf 'This installation predates package tracking. Remove installed MacTahoe package-list items?\n'
    printf 'This may also remove packages that were installed before MacTahoe. [Y/n] '
    read -r answer || true
    if [[ ! "$answer" =~ ^[Nn]$ ]]; then
        installed_legacy_dnf_packages=()
        for package in "${legacy_dnf_packages[@]}"; do
            [ "$package" != "fontconfig" ] || continue
            [[ "$package" == *font* ]] && continue
            rpm -q --quiet "$package" 2>/dev/null && installed_legacy_dnf_packages+=("$package")
        done
        if [ "${#installed_legacy_dnf_packages[@]}" -gt 0 ]; then
            sudo dnf remove -y "${installed_legacy_dnf_packages[@]}" || true
            sudo dnf autoremove -y 2>/dev/null || true
        fi
    fi
elif [ -n "$BACKUP_DIR" ] && [ -f "$BACKUP_DIR/apt-packages-installed-by-mactahoe" ]; then
    mapfile -t apt_packages_to_remove < <(
        while IFS= read -r package; do
            [ -n "$package" ] || continue
            # Giữ lại fontconfig và các gói phông chữ hệ thống
            [ "$package" != "fontconfig" ] || continue
            [[ "$package" == fonts-* ]] && continue
            dpkg-query -W -f='${db:Status-Abbrev}' "$package" 2>/dev/null | grep -q '^ii' &&
                printf '%s\n' "$package"
        done < "$BACKUP_DIR/apt-packages-installed-by-mactahoe"
    )
    if [ "${#apt_packages_to_remove[@]}" -gt 0 ]; then
        printf 'Removing apt packages newly installed by MacTahoe: %s\n' "${apt_packages_to_remove[*]}"
        sudo apt-get purge -y "${apt_packages_to_remove[@]}" || true
        sudo apt-get autoremove --purge -y 2>/dev/null || true
    fi
elif [ -n "$BACKUP_DIR" ] && [ -f "$BACKUP_DIR/apt-tracking-legacy" ]; then
    legacy_packages=(breeze-icon-theme dconf-cli \
        gir1.2-adw-1 gir1.2-gtk-4.0 gnome-shell-extension-manager \
        gnome-shell-extension-user-theme gnome-tweaks imagemagick \
        libglib2.0-dev-bin librsvg2-bin python3-gi python3-pil sassc)
    printf 'This installation predates package tracking. Purge installed MacTahoe package-list items?\n'
    printf 'This may also remove packages that were installed before MacTahoe. [Y/n] '
    read -r answer || true
    if [[ ! "$answer" =~ ^[Nn]$ ]]; then
        installed_legacy_packages=()
        for package in "${legacy_packages[@]}"; do
            [ "$package" != "fontconfig" ] || continue
            [[ "$package" == fonts-* ]] && continue
            dpkg-query -W -f='${db:Status-Abbrev}' "$package" 2>/dev/null | grep -q '^ii' &&
                installed_legacy_packages+=("$package")
        done
        if [ "${#installed_legacy_packages[@]}" -gt 0 ]; then
            sudo apt-get purge -y "${installed_legacy_packages[@]}" || true
            sudo apt-get autoremove --purge -y 2>/dev/null || true
        fi
    fi
fi

# 12. Khôi phục lại theme/icon cũ nếu có lưu trong backup
if [ -n "$BACKUP_DIR" ]; then
    for path in "$BACKUP_DIR/home/.themes"/MacTahoe-* "$BACKUP_DIR/home/.local/share/icons"/MacTahoe*; do
        [ ! -e "$path" ] || cp -a "$path" "$HOME/${path#"$BACKUP_DIR/home/"}"
    done
fi

# 13. Cập nhật cache hệ thống
fc-cache -f "$HOME/.local/share/fonts" 2>/dev/null || true
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
gtk-update-icon-cache -q -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
systemctl --user daemon-reload 2>/dev/null || true

# 14. Dọn dẹp các thư mục rỗng và file trạng thái
rmdir "$HOME/.local/share/mactahoe-apps" 2>/dev/null || true
rmdir "$HOME/.config/mactahoe-widgets" 2>/dev/null || true
rmdir "$HOME/.local/share/mactahoe-widgets" 2>/dev/null || true
rm -f "$STATE_DIR/latest-backup" "$STATE_DIR/project-path" 2>/dev/null || true
rmdir "$STATE_DIR" 2>/dev/null || true

printf '\nUninstall finished. Pre-existing system packages were preserved.\n'
printf 'Log out and back in to reload the desktop.\n'
