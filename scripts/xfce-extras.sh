#!/usr/bin/env bash
# Sourced by install.sh after common assets and Xfconf settings are installed.
install_xfce_extras() {
    local relative
    for relative in \
        .local/bin/mactahoe-xfce-session \
        .local/share/mactahoe-apps/mactahoe-xfce-session \
        .config/autostart/mactahoe-xfce-session.desktop \
        .local/bin/mactahoe-xfce-widgets .local/bin/mactahoe-xfce-dock \
        .local/share/mactahoe-apps/mactahoe-xfce-widgets \
        .local/share/applications/io.github.adfoxtheme.XfceWidgets.desktop \
        .local/share/applications/io.github.adfoxtheme.Launchpad.desktop \
        .config/autostart/mactahoe-xfce-widgets.desktop \
        .config/autostart/mactahoe-xfce-dock.desktop \
        .config/plank/mactahoe .local/share/plank/themes/MacTahoe; do
        backup_item "$relative"
    done
    mkdir -p "$HOME/.config/autostart" "$HOME/.config/plank/mactahoe/launchers" \
        "$HOME/.local/share/plank/themes/MacTahoe" \
        "$HOME/.local/share/mactahoe-apps/mactahoe-xfce-widgets"
    cp -a "$ROOT_DIR/apps/mactahoe-xfce-widgets/." \
        "$HOME/.local/share/mactahoe-apps/mactahoe-xfce-widgets/"
    mkdir -p "$HOME/.local/share/mactahoe-apps/mactahoe-xfce-session"
    cp "$ROOT_DIR/scripts/desktop.sh" "$ROOT_DIR/scripts/wallpaper_properties.py" \
        "$HOME/.local/share/mactahoe-apps/mactahoe-xfce-session/"
    install -m 0755 "$ROOT_DIR/apps/launchers/mactahoe-xfce-session" "$HOME/.local/bin/"
    install -m 0755 "$ROOT_DIR/apps/launchers/mactahoe-xfce-widgets" "$HOME/.local/bin/"
    install -m 0755 "$ROOT_DIR/apps/launchers/mactahoe-xfce-dock" "$HOME/.local/bin/"
    cp "$ROOT_DIR/desktop/io.github.adfoxtheme."{XfceWidgets,Launchpad}.desktop \
        "$HOME/.local/share/applications/"
    sed -i "s|^Exec=mactahoe-xfce-widgets|Exec=\"$HOME/.local/bin/mactahoe-xfce-widgets\"|" \
        "$HOME/.local/share/applications/io.github.adfoxtheme.XfceWidgets.desktop"
    sed -i "s|^Exec=mactahoe-xfce-menu$|Exec=\"$HOME/.local/bin/mactahoe-xfce-menu\"|" \
        "$HOME/.local/share/applications/io.github.adfoxtheme.Launchpad.desktop"
    cp "$ROOT_DIR/vendor/MacTahoe-gtk-theme/other/plank/theme-Dark/dock.theme" \
        "$HOME/.local/share/plank/themes/MacTahoe/dock.theme"

    # Preserve first-install state and subsequent user customization of the dock.
    if [ ! -e "$BACKUP_DIR/plank-before.ini" ]; then
        dconf dump /net/launchpad/plank/docks/mactahoe/ > "$BACKUP_DIR/plank-before.ini"
    fi
    if [ ! -e "$BACKUP_DIR/plank-configured" ]; then
        local schema=net.launchpad.plank.dock.settings:/net/launchpad/plank/docks/mactahoe/
        gsettings set "$schema" theme MacTahoe
        gsettings set "$schema" position bottom
        gsettings set "$schema" alignment center
        gsettings set "$schema" icon-size 44
        gsettings set "$schema" hide-mode dodge-maximized
        gsettings set "$schema" zoom-enabled true
        gsettings set "$schema" zoom-percent 130
        local launcher number=0
        for launcher in \
            "$HOME/.local/share/applications/io.github.adfoxtheme.Launchpad.desktop" \
            /usr/share/applications/thunar.desktop \
            /usr/share/applications/firefox-esr.desktop \
            /usr/share/applications/org.xfce.terminal.desktop; do
            [ -f "$launcher" ] || continue
            number=$((number + 1))
            # URI escaping covers home directories containing spaces or non-ASCII names.
            python3 - "$launcher" "$HOME/.config/plank/mactahoe/launchers/$number.dockitem" <<'PY'
from pathlib import Path
import sys
Path(sys.argv[2]).write_text('[PlankDockItemPreferences]\nLauncher=' + Path(sys.argv[1]).as_uri() + '\n')
PY
        done
        touch "$BACKUP_DIR/plank-configured"
    fi
    # Migrate the settings shortcut seeded by older releases off the dock.
    # Keep its desktop entry available in Launchpad and the applications menu.
    local dockitem
    for dockitem in "$HOME/.config/plank/mactahoe/launchers/"*.dockitem; do
        [ -f "$dockitem" ] || continue
        if [[ "${dockitem##*/}" =~ ^[0-9]+\.dockitem$ ]] && \
            grep -Fq '/io.github.adfoxtheme.XfceWidgets.desktop' "$dockitem"; then
            rm -f -- "$dockitem"
        fi
    done
    local component
    for component in session widgets dock; do
        cat > "$HOME/.config/autostart/mactahoe-xfce-$component.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=MacTahoe Xfce $component
Exec="$HOME/.local/bin/mactahoe-xfce-$component"
OnlyShowIn=XFCE;
Terminal=false
EOF
    done
    source "$ROOT_DIR/scripts/xfce-menu.sh"
    install_xfce_menu
    "$HOME/.local/bin/mactahoe-xfce-session"
    start_xfce_components
}

start_xfce_components() {
    # Settings application uses PATH, as do the other bundled desktop launchers.
    "$HOME/.local/bin/mactahoe-xfce-widgets" --stop 2>/dev/null || true
    "$HOME/.local/bin/mactahoe-xfce-dock" stop
    mkdir -p "$HOME/.cache/mactahoe-xfce"
    nohup "$HOME/.local/bin/mactahoe-xfce-widgets" \
        > "$HOME/.cache/mactahoe-xfce/widgets.log" 2>&1 < /dev/null &
    local dock_pid
    nohup "$HOME/.local/bin/mactahoe-xfce-dock" \
        > "$HOME/.cache/mactahoe-xfce/dock.log" 2>&1 < /dev/null &
    dock_pid=$!
    local attempt
    for ((attempt=0; attempt<3; attempt++)); do
        sleep 1
        if timeout 5 "$HOME/.local/bin/mactahoe-xfce-widgets" --status; then
            if ! kill -0 "$dock_pid" 2>/dev/null; then
                printf 'Dock startup failed. Details: %s/.cache/mactahoe-xfce/dock.log\n' "$HOME" >&2
                tail -n 12 "$HOME/.cache/mactahoe-xfce/dock.log" >&2
                return 1
            fi
            printf 'Widgets started. Enable all: %s --enable-all\n' "$HOME/.local/bin/mactahoe-xfce-widgets"
            return 0
        fi
    done
    printf 'Widget startup failed. Details: %s/.cache/mactahoe-xfce/widgets.log\n' "$HOME" >&2
    tail -n 12 "$HOME/.cache/mactahoe-xfce/widgets.log" >&2
    return 1
}
