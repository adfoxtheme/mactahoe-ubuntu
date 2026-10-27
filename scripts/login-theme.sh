#!/usr/bin/env bash
# ROOT_DIR is set by the installer sourcing this file.
install_login_theme() {
    local manager
    manager="$(python3 "$ROOT_DIR/scripts/display_manager.py")"
    case "$manager" in
        gdm) printf '\nDetected GDM; installing its login theme...\n'
             bash "$ROOT_DIR/install-gdm.sh" ;;
        lightdm) printf '\nDetected LightDM; installing its login theme...\n'
                 bash "$ROOT_DIR/install-lightdm.sh" ;;
        *) printf '\nNo supported GDM/LightDM display manager detected; login theme skipped.\n'
           return 0 ;;
    esac
}
