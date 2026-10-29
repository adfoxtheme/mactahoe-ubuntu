#!/usr/bin/env bash
set -u

USER_THEME_SCHEMA="$HOME/.local/share/gnome-shell/extensions/user-theme@gnome-shell-extensions.gcampax.github.com/schemas"
if [ -d "$USER_THEME_SCHEMA" ]; then
    export GSETTINGS_SCHEMA_DIR="$USER_THEME_SCHEMA:${GSETTINGS_SCHEMA_DIR:-}"
fi

write_ini() {
    local file="$1" prefer="$2" variant="$3"
    mkdir -p "$(dirname "$file")"
    if [ -f "$file" ]; then
        grep -v -E '^(gtk-application-prefer-dark-theme|gtk-theme-name)' "$file" > "$file.tmp" || true
        mv "$file.tmp" "$file"
    else
        printf '[Settings]\n' > "$file"
    fi
    printf 'gtk-theme-name=MacTahoe-%s\n' "$variant" >> "$file"
    printf 'gtk-application-prefer-dark-theme=%s\n' "$prefer" >> "$file"
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
    write_ini "$HOME/.config/gtk-3.0/settings.ini" "$prefer" "$variant"
    write_ini "$HOME/.config/gtk-4.0/settings.ini" "$prefer" "$variant"
    if [ -f "$HOME/.config/gtk-4.0/gtk-$variant.css" ]; then
        ln -sfn "$HOME/.config/gtk-4.0/gtk-$variant.css" "$HOME/.config/gtk-4.0/gtk.css"
        ln -sfn "$HOME/.config/gtk-4.0/gtk-$variant.css" "$HOME/.config/gtk-4.0/gtk-dark.css"
    fi
}

apply
gsettings monitor org.gnome.desktop.interface color-scheme | while read -r _; do
    apply
done
