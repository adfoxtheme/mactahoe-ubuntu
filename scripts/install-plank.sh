#!/usr/bin/env bash
# Sourced by install.sh inside the APT package-tracking snapshot.
install_plank() (
    set -euo pipefail
    # Keep an existing dock, including a manually installed Plank Reloaded.
    if command -v plank >/dev/null 2>&1; then
        return 0
    fi

    local package candidate
    for package in plank plank-reloaded; do
        candidate="$(LC_ALL=C apt-cache policy "$package" | awk '$1 == "Candidate:" {print $2}')"
        if [ -n "$candidate" ] && [ "$candidate" != '(none)' ]; then
            sudo apt-get install -y "$package"
            return 0
        fi
    done

    if [ "$distribution_id" != kali ]; then
        printf 'Neither plank nor plank-reloaded is available in your APT repositories.\n' >&2
        return 1
    fi

    # Kali rolling may not ship Plank. Use the upstream Debian package repository:
    # https://github.com/zquestz/plank-reloaded#installation
    # Keep this source and its signing key temporary; do not mix Debian/Ubuntu
    # distribution repositories into Kali or persist a third-party APT source.
    printf 'Plank is unavailable in Kali APT; installing upstream Plank Reloaded...\n'
    sudo apt-get install -y ca-certificates curl gnupg
    local temp_dir
    temp_dir="$(mktemp -d /tmp/mactahoe-plank.XXXXXXXX)"
    trap 'rm -rf -- "$temp_dir"' EXIT
    chmod 755 "$temp_dir"
    mkdir -m 755 "$temp_dir/sources.list.d"
    if [ -d /etc/apt/sources.list.d ]; then
        cp -a /etc/apt/sources.list.d/. "$temp_dir/sources.list.d/"
    fi
    curl --fail --show-error --silent --location --proto '=https' \
        https://zquestz.github.io/ppa/debian/KEY.gpg -o "$temp_dir/upstream-key"
    gpg --batch --yes --dearmor --output "$temp_dir/upstream-key.gpg" "$temp_dir/upstream-key"
    chmod 644 "$temp_dir/upstream-key.gpg"
    printf 'deb [signed-by=%s] https://zquestz.github.io/ppa/debian ./\n' \
        "$temp_dir/upstream-key.gpg" > "$temp_dir/sources.list.d/mactahoe-plank.list"
    local apt_options=(-o "Dir::Etc::sourceparts=$temp_dir/sources.list.d")
    sudo apt-get "${apt_options[@]}" update
    sudo apt-get "${apt_options[@]}" install -y plank-reloaded
    if ! command -v plank >/dev/null 2>&1; then
        printf 'Plank Reloaded was installed but the plank command was not found.\n' >&2
        return 1
    fi
)
