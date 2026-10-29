#!/usr/bin/env bash
set -u

write_ini() {
    local file="$1" prefer="$2" iface
    mkdir -p "$(dirname "$file")"
    if [ -f "$file" ]; then
        grep -vE '^gtk-application-prefer-dark-theme|^gtk-interface-color-scheme' "$file" > "$file.tmp" || true
        mv "$file.tmp" "$file"
    else
        printf '[Settings]\n' > "$file"
    fi
    printf 'gtk-application-prefer-dark-theme=%s\n' "$prefer" >> "$file"
    # GTK >= 4.16 replaced gtk-application-prefer-dark-theme with
    # gtk-interface-color-scheme. Chrome (GtkUi) reads the new key, so it must
    # be written as well or browsers keep a light color scheme for their
    # contents (e.g. white New Tab page) even when the GTK theme is dark.
    if [ "$prefer" = "1" ]; then iface="dark"; else iface="default"; fi
    printf 'gtk-interface-color-scheme=%s\n' "$iface" >> "$file"
}

apply() {
    local scheme variant prefer
    scheme=$(gsettings get org.gnome.desktop.interface color-scheme 2>/dev/null)
    if [ "$scheme" = "'prefer-dark'" ]; then
        variant="Dark"
        prefer="1"
    else
        variant="Light"
        prefer="0"
    fi
    if [ "$(gsettings get org.gnome.desktop.interface gtk-theme)" != "'MacTahoe-$variant'" ]; then
        gsettings set org.gnome.desktop.interface gtk-theme "MacTahoe-$variant"
    fi
    if [ "$(gsettings get org.gnome.shell.extensions.user-theme name)" != "'MacTahoe-$variant'" ]; then
        gsettings set org.gnome.shell.extensions.user-theme name "MacTahoe-$variant"
    fi
    write_ini "$HOME/.config/gtk-3.0/settings.ini" "$prefer"
    write_ini "$HOME/.config/gtk-4.0/settings.ini" "$prefer"
}

apply
gsettings monitor org.gnome.desktop.interface color-scheme | while read -r _; do
    apply
done
