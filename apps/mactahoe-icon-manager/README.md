# MacTahoe Icon Manager

A GTK4/Libadwaita application for setting MacTahoe icons on installed system, Snap, Flatpak, and user applications.

## Features

- Scans application launchers in `/usr/share/applications`, Flatpak, Snap, and `~/.local/share/applications`.
- Replaces application icons with matching MacTahoe icons.
- Backs up original launchers to `~/.local/share/mactahoe-icon-manager/backups/`.
- Restore the original icon at any time.
- Includes a data self-test that does not require opening the interface: `mactahoe-icon-manager --self-test`.

## Run

```bash
cd "$HOME/mactahoe-ubuntu/apps/mactahoe-icon-manager"
python3 main.py
```

Or launch **MacTahoe Icon Manager** from GNOME or run:

```bash
mactahoe-icon-manager
```
