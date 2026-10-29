# MacTahoe Xfce Widgets

GTK3 desktop windows for Xfce/X11, kept above Xfdesktop and below normal applications.
The main `install.sh` installs Python GI, GTK3, psutil, Plank, the launcher, a settings
menu entry and Xfce-only autostart entries.

- Clock and date, Vietnamese lunar date using the bundled calendar's UTC+7 algorithm.
- Weather from Open-Meteo, or OpenWeather with an optional personal API key.
- CPU, RAM, home filesystem usage/free space, network rates and available AMD/NVIDIA GPU utilization.
- Work/break countdown and desktop notifications, with a manual break/reset button.
- Per-widget visibility, monitor selection, margins and refresh/reminder intervals.
- Plank preferences for smart hiding, icon size, zoom, placement and pinned launchers.

```bash
mactahoe-xfce-widgets --enable-all
mactahoe-xfce-widgets --status
mactahoe-xfce-widgets --preferences
mactahoe-xfce-widgets --stop
mactahoe-xfce-dock preferences
```

Settings live in `${XDG_CONFIG_HOME:-~/.config}/mactahoe-xfce/widgets.json` (mode 0600).
Logs are in `~/.cache/mactahoe-xfce/`. Settings are kept when uninstalling so a later
installation can reuse them. The original Plank/Xfconf settings and autostart files
are restored by `uninstall.sh`. Only the named `mactahoe` Plank instance is managed.

On smaller screens the cards use compact spacing and a scroll area; the settings
button stays accessible below the cards. Use a composited X11 session for translucent
rounded cards. Xfce Wayland is not supported by this Plank-based implementation.

Weather requires an internet connection; city lookup uses Open-Meteo geocoding.
Leave the city blank to use coordinates directly. Provider attribution appears in
the weather card. GPU telemetry is hidden when the driver does not expose it.

Run model tests with `python3 -m unittest discover -s apps/mactahoe-xfce-widgets -v`.
The repository's `scripts/test-xfce-ui.py` exercises the actual GTK UI under Xvfb.
