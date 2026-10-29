#!/usr/bin/env bash
# Verify dispatch independently from the currently selected desktop, without sudo.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/login-theme.sh"
ROOT_DIR=/test-repo
python3() { printf '%s\n' "$test_manager"; }
bash() { printf '%s\n' "$1"; return "${test_failure:-0}"; }
test_manager=gdm
[[ "$(install_login_theme)" == *'/test-repo/install-gdm.sh'* ]]
test_manager=lightdm
[[ "$(install_login_theme)" == *'/test-repo/install-lightdm.sh'* ]]
test_manager=unknown
[[ "$(install_login_theme)" == *'login theme skipped'* ]]
test_manager=gdm
if test_failure=1 install_login_theme >/dev/null; then exit 1; fi
printf 'PASS: GDM/LightDM dispatch, unsupported manager and child-installer failure\n'
