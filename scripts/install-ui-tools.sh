#!/usr/bin/env bash
set -euo pipefail

if [ ! -r /etc/os-release ]; then
    printf 'Cannot identify this operating system.\n' >&2
    exit 1
fi
. /etc/os-release
distribution_id="${ID:-}"
id_like="${ID_LIKE:-}"

if [ "$distribution_id" = cachyos ] || [ "$distribution_id" = arch ] || [[ "$id_like" =~ (arch|cachyos) ]]; then
    sudo pacman -S --needed gnome-tweaks extension-manager
elif [ "$distribution_id" = fedora ]; then
    sudo dnf install -y gnome-tweaks gnome-extensions-app
elif [ "$distribution_id" = ubuntu ] || [ "$distribution_id" = debian ]; then
    sudo apt-get update
    sudo apt-get install -y gnome-tweaks gnome-shell-extension-manager
else
    printf 'Unsupported distribution: %s\n' "$distribution_id" >&2
    exit 1
fi
