"""Find Xfdesktop wallpaper properties, including a freshly initialized profile."""
import re
import subprocess
import sys


def wallpaper_properties(properties, monitors=(), workspaces=1):
    found = {line.strip() for line in properties.splitlines()
             if re.fullmatch(r"/backdrop/.+/(?:last-image|image-path)", line.strip())}
    # A fresh profile can have image-style/color properties but no image path yet.
    for line in properties.splitlines():
        match = re.match(r"(/backdrop/.+/workspace\d+)/", line.strip())
        if match:
            found.add(match[1] + "/last-image")
    if not found:
        for monitor in monitors:
            if not monitor or "/" in monitor:
                continue
            for workspace in range(max(1, min(64, workspaces))):
                found.add(f"/backdrop/screen0/monitor{monitor}/workspace{workspace}/last-image")
    return sorted(found)


def main():
    raw = sys.stdin.read()
    monitors, workspaces = [], 1
    if not wallpaper_properties(raw):
        import gi
        gi.require_version("Gdk", "3.0")
        from gi.repository import Gdk
        screen = Gdk.Screen.get_default()
        if screen:
            monitors = [screen.get_monitor_plug_name(i) for i in range(screen.get_n_monitors())]
        try:
            workspaces = int(subprocess.check_output([
                "xfconf-query", "-c", "xfwm4", "-p", "/general/workspace_count",
            ], text=True, stderr=subprocess.DEVNULL))
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    for property_name in wallpaper_properties(raw, monitors, workspaces):
        print(property_name)


if __name__ == "__main__":
    main()
