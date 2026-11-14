# MacTahoe for GNOME

A macOS Tahoe-inspired desktop theme and a set of custom GNOME extensions and applications.

> [!NOTE]
> Tested on Ubuntu 26.04, Debian 13 (Trixie), Fedora 40+, and CachyOS/Arch Linux with GNOME Shell 48 or later.

## Screenshots

<p align="center"><img src="assets/screenshots/mactahoe-desktop.png" alt="MacTahoe desktop with widgets and dock on GNOME" width="100%"></p>

| Overview and settings | Applications |
|---|---|
| <img src="assets/screenshots/mactahoe-overview.png" alt="GNOME Overview with the MacTahoe theme" width="100%"> | <img src="assets/screenshots/mactahoe-settings.png" alt="GNOME Settings and Files with the MacTahoe theme" width="100%"> |
| <img src="assets/screenshots/mactahoe-icon-manager.png" alt="MacTahoe Icon Manager" width="100%"> | <img src="assets/screenshots/mactahoe-app-themer.png" alt="Application Theme Manager" width="100%"> |
| <img src="assets/screenshots/mactahoe-extensions.png" alt="Managing and customizing extensions" width="100%"> | <img src="assets/screenshots/mactahoe-browsers.png" alt="Browsers with the macOS Tahoe appearance" width="100%"> |

## What's included

- `vendor/MacTahoe-gtk-theme/` and `vendor/MacTahoe-icon-theme/`: bundled theme sources.
- `assets/fonts/`, `assets/wallpapers/`, and `assets/screenshots/`: fonts, wallpapers, and project screenshots.
- `apps/`: GTK4 applications for icon management, the Vietnamese lunar calendar, image compression, and browser theming.
- `desktop/`: desktop launchers for the applications.
- `vendor/gnome-extensions/`: UbuntuTahoe, UbuntuTahoeDock, UbuntuTahoeWidgets, UbuntuTahoeClipboard, UbuntuTahoeSpotlight, and the optional UbuntuTahoeGlass extension.
- `config/gsettings.tsv` and `config/firefox-user.js`: GNOME and Firefox settings used by the installer.
- `docs/`: setup notes and extension configuration references.

The GTK and Shell themes, icons, cursor, SF fonts, and wallpapers provide the core appearance. The top bar is transparent through the Shell CSS and does not require blur. Firefox receives rounded window corners and a Safari-inspired theme.

UbuntuTahoe combines the global menu, right-aligned clock, overview and app-folder blur, and input method panel. UbuntuTahoeDock provides a floating bottom dock with smart auto-hide and adjustable icon size. UbuntuTahoeWidgets provides desktop clock, weather, system, lunar calendar, and break-reminder widgets. The clipboard and Spotlight extensions are also included.

GNOME Tweaks and Extension Manager are optional configuration tools, not theme components. The project also includes a MacTahoe icon manager, Vietnamese lunar calendar, image compressor, and browser theme manager. The calendar works offline; image compression is performed locally with Pillow.

Custom extension settings for Dock, Widgets, and Liquid Glass support **System default**, **Tiếng Việt**, and **English**. The initial setting follows the system locale. The widget labels and weather information follow the selected language. Other bundled extension UI and application interfaces are in English.

Extensions are checked against the declared GNOME Shell versions and are enabled for the next login. UbuntuTahoe, UbuntuTahoeDock, UbuntuTahoeWidgets, UbuntuTahoeClipboard, and UbuntuTahoeSpotlight are enabled by default. UbuntuTahoeGlass is installed but disabled by default.

## Install or update

Run this command from a terminal:

```bash
cd "$HOME" && if [ -d mactahoe-ubuntu/.git ]; then git -C mactahoe-ubuntu pull --ff-only; else git clone https://github.com/adfoxtheme/mactahoe-ubuntu.git mactahoe-ubuntu; fi && cd "$HOME/mactahoe-ubuntu" && ./install.sh
```

After installation, log out and back in so GNOME loads the new themes and extensions.

To update an existing checkout:

```bash
cd "$HOME/mactahoe-ubuntu" && git pull --ff-only && ./install.sh
```

### Optional GDM theme

To theme the system login screen, run:

```bash
cd "$HOME/mactahoe-ubuntu" && ./install-gdm.sh
```

> [!CAUTION]
> **Changing the GDM resources can break the login screen.** This affects the system login screen, not the GNOME lock screen. The script replaces the system GDM resource with a compiled theme resource. If it is incompatible, GDM may show a black screen or prevent login.
>
> Run this only if you can recover the system from a TTY. Make a backup or VM snapshot first. Do not run `sudo ./install-gdm.sh`; the script requests administrative access when needed.
>
> To restore from a TTY, sign in as your regular user and run:
>
> ```bash
> sudo "$HOME/mactahoe-ubuntu/vendor/MacTahoe-gtk-theme/tweaks.sh" -g -r
> sudo reboot
> ```
>
> Adjust the repository path if it is not `~/mactahoe-ubuntu`. If the installer stops during validation or compilation, the GDM resource has not yet been changed.

## Configure extensions

Open **Extension Manager** or **Extensions** to configure the custom extensions.

- **UbuntuTahoeDock:** choose whether the dock hides when windows are maximized, is always hidden, or is always visible; adjust the icon size.
- **UbuntuTahoeWidgets:** enable or disable individual widgets, configure the OpenWeather API key and city, set the refresh interval, and adjust widget margins. Use the language row to select the system default, Vietnamese, or English.
- **UbuntuTahoeSpotlight:** press <kbd>Super</kbd> + <kbd>Alt</kbd> + <kbd>F</kbd> to search for applications, perform calculations, and run system actions.
- **UbuntuTahoeGlass:** optional GPU shader effects for the dock, application windows, and Quick Settings. Enable the extension before opening its preferences.
- **UbuntuTahoeClipboard:** clipboard history with up to 20 items; press <kbd>Win</kbd> + <kbd>Alt</kbd> + <kbd>Space</kbd>.

The dock, widget, and glass preference pages include a language selector. The default follows the system locale, and a manual selection is saved.

## Applications

Launch the applications from GNOME's app grid or from a terminal:

```bash
mactahoe-icon-manager
am-lich-viet-nam
image-compressor
mactahoe-app-themer
```

The UI is in English. Desktop launchers provide Vietnamese names and descriptions when the system locale is Vietnamese.

## Supported systems

- Ubuntu 26.04 LTS
- Debian 13 (Trixie)
- Fedora 40 and later
- CachyOS / Arch Linux

The installer supports GNOME Shell 45 through 51+, subject to the extension metadata and APIs available in each release.

## Sources and licensing

The theme source versions are recorded in the corresponding `vendor/` directories. Review each component's license before redistribution. SF Pro fonts are included; check their license terms before redistribution.
