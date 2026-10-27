# Installer scripts

`install-ui-tools.sh` installs GNOME Tweaks and Extension Manager on Ubuntu, Debian, and Kali GNOME. `desktop.sh` detects GNOME/Xfce and applies or restores Xfconf settings. The complete A–Z installer and uninstaller are at the project root as `install.sh` and `uninstall.sh`.

Run `bash scripts/test-desktop.sh` for isolated desktop detection, Xfconf application, repeat-install and restore checks.

Xfce extras are installed by `xfce-extras.sh`. LightDM GTK Greeter installation and rollback are implemented by `lightdm_theme.py` and invoked through `../install-lightdm.sh`.

Validation on Linux:

```bash
python3 -m unittest discover -s apps/mactahoe-xfce-widgets -v
python3 -m unittest discover -s scripts -p 'test_*.py' -v
bash scripts/test-desktop.sh
xvfb-run -a dbus-run-session -- bash scripts/test-xfce-install.sh
xvfb-run -a dbus-run-session -- python3 scripts/test-xfce-ui.py
```

The X11 tests require GTK3 GI, psutil, Xvfb, Xauth, D-Bus, Xfconf, dconf-cli, Xfwm4, Xfdesktop and Plank. Each creates a temporary HOME and an isolated D-Bus session. Set `MACTAHOE_UI_SCREENSHOT` to an absolute PNG path to capture the widget UI. On WSL, run with `env -u WAYLAND_DISPLAY GDK_BACKEND=x11` before `xvfb-run`.
