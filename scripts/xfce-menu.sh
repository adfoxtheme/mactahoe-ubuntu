#!/usr/bin/env bash
# Uses backup_item and xfce_set from the main installer. Menu categories/favorites stay intact.
xfce_panel_pids() {
    local candidate
    while read -r candidate; do
        if grep -zFxq "DISPLAY=${DISPLAY:-}" "/proc/$candidate/environ" 2>/dev/null; then
            printf '%s\n' "$candidate"
        fi
    done < <(pgrep -u "$UID" -x xfce4-panel || true)
}

stop_xfce_panel() {
    [ -n "$(xfce_panel_pids)" ] || return 0
    xfce4-panel --quit
    local attempt
    for ((attempt=0; attempt<30; attempt++)); do
        [ -n "$(xfce_panel_pids)" ] || return 0
        sleep 0.1
    done
    printf 'Xfce panel did not stop; refusing to overwrite its menu settings.\n' >&2
    return 1
}

start_xfce_panel() {
    [ -z "$(xfce_panel_pids)" ] || return 0
    mkdir -p "$HOME/.cache/mactahoe-xfce"
    nohup xfce4-panel --disable-wm-check > "$HOME/.cache/mactahoe-xfce/panel.log" 2>&1 < /dev/null &
}

install_xfce_menu() (
    local relative property plugin plugin_type panel_id new_id=1
    local -a menu_plugins=() properties=() plugin_ids=()
    mapfile -t properties < <(xfconf-query -c xfce4-panel -l)
    for property in "${properties[@]}"; do
        if [[ "$property" =~ ^/plugins/plugin-([0-9]+)$ ]]; then
            plugin="${BASH_REMATCH[1]}"
            [ "$plugin" -lt "$new_id" ] || new_id=$((plugin + 1))
            plugin_type="$(xfconf-query -c xfce4-panel -p "$property")"
            if [ "$plugin_type" = whiskermenu ]; then menu_plugins+=("$plugin"); fi
        fi
    done
    stop_xfce_panel
    trap start_xfce_panel EXIT
    # A standard Xfce panel can have the older Applications Menu instead of Whisker.
    if [ "${#menu_plugins[@]}" -eq 0 ]; then
        for property in "${properties[@]}"; do
            [[ "$property" =~ ^/plugins/plugin-([0-9]+)$ ]] || continue
            plugin="${BASH_REMATCH[1]}"
            if [ "$(xfconf-query -c xfce4-panel -p "$property")" = applicationsmenu ]; then
                xfce_set xfce4-panel "$property" string whiskermenu
                menu_plugins+=("$plugin")
                break
            fi
        done
    fi
    # If no application menu exists, prepend one to the first panel without removing its items.
    if [ "${#menu_plugins[@]}" -eq 0 ]; then
        panel_id="$(printf '%s\n' "${properties[@]}" | sed -n 's|^/panels/panel-\([0-9]*\)/plugin-ids$|\1|p' | head -n1)"
        if [ -z "$panel_id" ]; then
            printf 'No Xfce panel found. Add a panel first, then rerun install.sh.\n' >&2
            return 1
        fi
        mapfile -t plugin_ids < <(LC_ALL=C xfconf-query -c xfce4-panel -p "/panels/panel-$panel_id/plugin-ids" | sed -n '/^[0-9][0-9]*$/p')
        xfce_set xfce4-panel "/plugins/plugin-$new_id" string whiskermenu
        xfce_set_int_array xfce4-panel "/panels/panel-$panel_id/plugin-ids" "$new_id" "${plugin_ids[@]}"
        menu_plugins+=("$new_id")
    fi
    for relative in .local/bin/mactahoe-xfce-menu \
        .local/share/mactahoe-apps/mactahoe-xfce-menu \
        .config/gtk-3.0/gtk.css .config/gtk-3.0/mactahoe-menu.css; do
        backup_item "$relative"
    done
    mkdir -p "$HOME/.local/share/mactahoe-apps/mactahoe-xfce-menu" "$HOME/.config/gtk-3.0"
    cp "$ROOT_DIR/vendor/MacTahoe-gtk-theme/src/assets/gnome-shell/activities/activities-apple.svg" \
        "$HOME/.local/share/mactahoe-apps/mactahoe-xfce-menu/apple.svg"
    install -m 0755 "$ROOT_DIR/apps/launchers/mactahoe-xfce-menu" "$HOME/.local/bin/"
    cp "$ROOT_DIR/scripts/launchpad.py" "$ROOT_DIR/config/launchpad.css" \
        "$HOME/.local/share/mactahoe-apps/mactahoe-xfce-menu/"
    cp "$ROOT_DIR/config/xfce-menu.css" "$HOME/.config/gtk-3.0/mactahoe-menu.css"
    python3 "$ROOT_DIR/scripts/xfce_menu.py" css "$HOME/.config/gtk-3.0/gtk.css"
    "$HOME/.local/bin/mactahoe-xfce-menu" --stop
    local key value type rc
    for plugin in "${menu_plugins[@]}"; do
        relative=".config/xfce4/panel/whiskermenu-$plugin.rc"
        backup_item "$relative"
        # Remember each rc file so uninstall can restore both existing and newly created files.
        grep -Fqx "$relative" "$BACKUP_DIR/xfce-menu-files" 2>/dev/null || printf '%s\n' "$relative" >> "$BACKUP_DIR/xfce-menu-files"
        local -a rc_settings=()
        while IFS='|' read -r key type value; do
            xfce_set xfce4-panel "/plugins/plugin-$plugin/$key" "$type" "$value"
            rc_settings+=("$key=$value")
        done <<EOF
button-icon|string|$HOME/.local/share/mactahoe-apps/mactahoe-xfce-menu/apple.svg
button-title|string|Applications
show-button-title|bool|false
show-button-icon|bool|true
view-mode|int|0
default-category|int|2
launcher-icon-size|int|4
launcher-show-description|bool|false
launcher-show-tooltip|bool|true
category-icon-size|int|1
category-show-name|bool|true
position-search-alternate|bool|false
position-categories-alternate|bool|true
position-profile-alternate|bool|true
menu-width|int|740
menu-height|int|560
menu-opacity|int|98
EOF
        # 2.8 uses rc settings; 2.10+ uses Xfconf. Set both formats.
        rc_settings+=("view-as-icons=true")
        rc="$HOME/$relative"
        python3 "$ROOT_DIR/scripts/xfce_menu.py" rc "$rc" "${rc_settings[@]}"
    done
    printf 'MacTahoe applications menu installed. Apple opens the panel menu; Launchpad opens the fullscreen app grid.\n'
)
