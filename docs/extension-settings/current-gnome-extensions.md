# Enabled GNOME Extensions on the Reference System

This snapshot records the active configuration. The installer should install or copy the extensions and apply these values to reproduce the desktop. Conky is not enabled at login.

## Blur My Shell

Extension: `blur-my-shell@aunetx`.

- Blur is enabled for `overview` and `appfolder`.
- Blur is disabled for `applications`, `coverflow-alt-tab`, `dash-to-dock`, `lockscreen`, `panel`, `popup`, `screenshot`, and `window-list`.
- Active pipeline: `pipeline_default`, Dual Kawase, radius 30, brightness 0.6.
- `Plank` and `Conky` are excluded.
- `dash-to-dock` has `static-blur=true` but `blur=false`, so dock blur is currently inactive.

## Global Menu for GNOME

Extension: `globalmenu@ShiroOSL.github.io`, version 15. The menu bar and System Menu button are enabled. App, File, Edit, View, Go, Window, and Help menus are enabled. System Menu shortcuts for Settings, Terminal, Software Center, Force Quit, System Monitor, lock, log out, and shutdown are also enabled.

Main values: `show-indicator=true`, `show-logo-menu=true`, `hide-overview-button=true`, `logo-distro-icon-symbolic=true`, and icon size 16.

## Other enabled extensions

- `just-perfection-desktop@just-perfection`, version 37: clock on the right (`clock-menu-position=1`), offset 20; Overview button hidden.

## Related system extensions

The configuration also uses `user-theme@gnome-shell-extensions.gcampax.github.com` and `ubuntu-dock@ubuntu.com`. These ship with Ubuntu or system packages and are not separate extension directories in this repository.
