# MacTahoe Setup Reference for Ubuntu 26.04

This guide records the reference configuration used to create the project. For a normal installation, use the repository's `install.sh`; this document describes the individual components and settings.

## Reference system

- Ubuntu 26.04.1 LTS
- GNOME Shell 50.1 on Wayland
- MacTahoe GTK theme commit `1e45e19` (2026-09-28)
- MacTahoe icon theme commit `839848b9` (2026-09-10)

The resulting setup uses `MacTahoe-Dark`, `MacTahoe-blue`, `MacTahoe-cursors`, SF Pro Display 11, a dark dock (`#1f1f24`), the `MacTahoe-night.jpeg` wallpaper, and the Safari Tahoe Firefox theme. GDM theming is optional and carries additional risk.

## Before starting

Close Firefox and Chrome, check the desktop and session versions, and back up the current GNOME configuration:

```bash
lsb_release -ds
gnome-shell --version
echo "$XDG_SESSION_TYPE"

mkdir -p ~/mac-tahoe-backup
dconf dump / > ~/mac-tahoe-backup/dconf-before-theme.txt
```

Restore the backup later with:

```bash
dconf load / < ~/mac-tahoe-backup/dconf-before-theme.txt
```

## Install theme dependencies

```bash
sudo apt update
sudo apt install -y \
  git curl unzip \
  sassc libglib2.0-dev-bin imagemagick \
  gnome-tweaks gnome-shell-extension-user-theme dconf-cli \
  breeze-icon-theme
```

`sassc` compiles the theme stylesheets; `libglib2.0-dev-bin` provides GResource tools needed for GDM; `imagemagick` processes the GDM wallpaper; and `breeze-icon-theme` provides icons inherited by the MacTahoe icon set. Tweaks is optional.

## Install the GTK theme, icons, and fonts

The project bundles the theme sources under `vendor/`. The corresponding upstream repositories are:

- <https://github.com/vinceliuice/MacTahoe-gtk-theme>
- <https://github.com/vinceliuice/MacTahoe-icon-theme>

The GTK theme and icons can be installed from the repository:

```bash
cd "$HOME/mactahoe-ubuntu/vendor/MacTahoe-gtk-theme"
./install.sh -l --shell -i apple

cd "$HOME/mactahoe-ubuntu/vendor/MacTahoe-icon-theme"
./install.sh -t blue
```

Install the included SF Pro and SF Mono fonts for the current user:

```bash
mkdir -p "$HOME/.local/share/fonts/MacTahoe"
cp -a "$HOME/mactahoe-ubuntu/assets/fonts/SF-Pro" \
  "$HOME/mactahoe-ubuntu/assets/fonts/SF-Mono" \
  "$HOME/.local/share/fonts/MacTahoe/"
fc-cache -f "$HOME/.local/share/fonts/MacTahoe"
```

The bundled SF fonts have separate license terms. Review them before redistribution.

## Apply the desktop appearance

Enable the User Themes extension and select the GTK, Shell, icon, cursor, font, dark-mode, and title-bar settings:

```bash
gnome-extensions enable user-theme@gnome-shell-extensions.gcampax.github.com

gsettings set org.gnome.shell.extensions.user-theme name 'MacTahoe-Dark'
gsettings set org.gnome.desktop.interface gtk-theme 'MacTahoe-Dark'
gsettings set org.gnome.desktop.interface icon-theme 'MacTahoe-blue'
gsettings set org.gnome.desktop.interface cursor-theme 'MacTahoe-cursors'
gsettings set org.gnome.desktop.interface cursor-size 24
gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark'
gsettings set org.gnome.desktop.interface accent-color 'green'
gsettings set org.gnome.desktop.interface font-name 'SF Pro Display 11'
gsettings set org.gnome.desktop.interface document-font-name 'SF Pro Text 11'
gsettings set org.gnome.desktop.interface monospace-font-name 'SF Mono 11'
gsettings set org.gnome.desktop.interface font-antialiasing 'rgba'
gsettings set org.gnome.desktop.interface font-hinting 'medium'
gsettings set org.gnome.desktop.wm.preferences titlebar-font 'SF Pro Display Bold 11'
gsettings set org.gnome.desktop.wm.preferences button-layout 'close,minimize,maximize:'
```

If GNOME cannot find User Themes, log out and back in and verify that `gnome-shell-extension-user-theme` is installed.

To move the top-bar clock to the right, install and enable Just Perfection, then set its `clock-menu-position` to `1` and `clock-menu-position-offset` to `20`. These values can also be changed in Extension Manager.

## Set wallpapers and dock options

Set the dark wallpaper for the desktop and lock screen:

```bash
WALL="$HOME/Pictures/Wallpapers/MacTahoe/MacTahoe-night.jpeg"
gsettings set org.gnome.desktop.background picture-uri "file://$WALL"
gsettings set org.gnome.desktop.background picture-uri-dark "file://$WALL"
gsettings set org.gnome.desktop.background picture-options 'zoom'
gsettings set org.gnome.desktop.screensaver picture-uri "file://$WALL"
gsettings set org.gnome.desktop.screensaver picture-options 'zoom'
```

For Ubuntu Dock or Dash to Dock, the reference configuration uses a bottom-positioned dock with smart auto-hide and a fixed dark background. The following three settings determine the dark dock background:

```bash
D=org.gnome.shell.extensions.dash-to-dock
gsettings set "$D" transparency-mode 'FIXED'
gsettings set "$D" custom-background-color true
gsettings set "$D" background-color '#1f1f24'
gsettings set "$D" apply-custom-theme false
```

## Optional automatic light/dark synchronization

The repository includes `apps/color-scheme-sync.sh` and `systemd/color-scheme-sync.service`. The installer configures the user service to synchronize GTK, Shell, and GTK application theme preferences with GNOME's color-scheme setting. Check its state with:

```bash
systemctl --user is-active color-scheme-sync.service
```

The reference configuration keeps the GTK4 `gtk.css` link on the dark variant, so some GTK4/Libadwaita applications may remain dark in light mode.

## Optional Firefox theme

The application theme manager detects Firefox profiles and applies the bundled Safari Tahoe theme. To install it manually, close Firefox, locate its profile (for example with `about:profiles`), copy the contents of `vendor/MacTahoe-gtk-theme/other/firefox/` into that profile's `chrome/` directory, and enable:

```text
toolkit.legacyUserProfileCustomizations.stylesheets = true
```

Restart Firefox after changing its profile.

## Optional GDM theme

> [!CAUTION]
> GDM theme installation replaces a system login-screen resource and can prevent login if the resource is incompatible. Back up the system and make sure you know how to use a TTY before continuing.

The repository's `install-gdm.sh` performs validation, backup, and installation. Do not run it with `sudo`; it requests administrative access when required. To revert:

```bash
sudo "$HOME/mactahoe-ubuntu/vendor/MacTahoe-gtk-theme/tweaks.sh" -g -r
sudo reboot
```

## Verify or revert

Check the active theme and extension state:

```bash
gsettings get org.gnome.desktop.interface gtk-theme
gsettings get org.gnome.desktop.interface icon-theme
gsettings get org.gnome.desktop.interface cursor-theme
gsettings get org.gnome.desktop.interface color-scheme
gnome-extensions list --enabled
systemctl --user is-active color-scheme-sync.service
```

Log out and back in after changing the Shell theme or extensions. The repository's `uninstall.sh` restores backed-up user settings and removes installed project components. The Vietnamese source notes are preserved in [`skin-tahoe-source.vi.md`](./skin-tahoe-source.vi.md).
