# Application Theme Manager

A Python and GTK4/Libadwaita application for applying the macOS Tahoe appearance to browsers, including **Mozilla Firefox**, **Brave**, and **Google Chrome**.

| Application | Browser appearance |
|---|---|
| <img src="../../assets/screenshots/mactahoe-app-themer.png" alt="Application Theme Manager" width="100%"> | <img src="../../assets/screenshots/mactahoe-browsers.png" alt="Browsers with the Tahoe appearance" width="100%"> |

## Features

- **Mozilla Firefox:** detects profiles across Snap, native APT/DNF/Pacman, and Flatpak installations; installs the Safari Tahoe theme and enables the required `user.js` CSS preference. Restore Firefox's default appearance at any time.
- **Brave:** detects Snap, native, and Flatpak installations; syncs the `MacTahoe-Dark` theme and cursor and enables GTK theming. Restore the default appearance at any time.
- **Google Chrome:** syncs the MacTahoe GTK theme with Chrome and supports native and Flatpak installations.

## Run

```bash
cd "$HOME/mactahoe-ubuntu/apps/mactahoe-app-themer"
python3 main.py
```

Or launch **Application Theme Manager** from GNOME or run:

```bash
mactahoe-app-themer
```

## Files

- `main.py` — Libadwaita application interface.
- `themer_firefox.py` — Firefox profile detection and theme setup.
- `themer_brave.py` — GTK theme and cursor integration for Brave.
- `themer_chrome.py` — GTK theme integration for Chrome.
- `assets/firefox/` — bundled Safari Tahoe CSS theme.
- `assets/io.github.adfoxtheme.MacTahoeAppThemer.svg` — application icon.
