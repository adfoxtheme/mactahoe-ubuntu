#!/usr/bin/env bash
set -euo pipefail

if [ ! -r /etc/os-release ]; then
    printf 'Cannot identify this operating system.\n' >&2
    exit 1
fi
. /etc/os-release
if [ "${ID:-}" != ubuntu ] && [ "${ID:-}" != debian ] && [ "${ID:-}" != kali ]; then
    printf 'This installer currently supports Ubuntu, Debian, and Kali.\n' >&2
    exit 1
fi

if ! command -v apt-get >/dev/null 2>&1; then
    printf 'Package manager apt-get was not found.\n' >&2
    exit 1
fi

sudo apt-get update
sudo apt-get install -y gnome-tweaks gnome-shell-extension-manager
