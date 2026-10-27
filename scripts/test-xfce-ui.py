"""Run under xvfb-run + dbus-run-session; exercises real GTK, Xfconf and Plank.

Uses a temporary HOME and never accesses the user's desktop settings.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import shutil

ROOT = Path(__file__).resolve().parent.parent
temporary = tempfile.TemporaryDirectory(prefix="mactahoe-ui-")
os.environ.update(HOME=temporary.name, XDG_CONFIG_HOME=temporary.name + "/.config",
                  XDG_DATA_HOME=temporary.name + "/.local/share", XDG_CURRENT_DESKTOP="XFCE",
                  GDK_BACKEND="x11")
subprocess.run(["dbus-update-activation-environment", "DISPLAY", "XAUTHORITY", "GDK_BACKEND",
                "HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME"], check=True)
home = Path(temporary.name)
theme = home / ".local/share/plank/themes/MacTahoe"
theme.mkdir(parents=True)
shutil.copy2(ROOT / "vendor/MacTahoe-gtk-theme/other/plank/theme-Dark/dock.theme", theme)
launcher = home / ".local/share/applications/launchpad.desktop"
launcher.parent.mkdir(parents=True)
launcher.write_text("[Desktop Entry]\nType=Application\nName=Launchpad\nIcon=view-app-grid-symbolic\nExec=true\n")
pin = home / ".config/plank/mactahoe/launchers/1.dockitem"
pin.parent.mkdir(parents=True)
pin.write_text("[PlankDockItemPreferences]\nLauncher=" + launcher.as_uri() + "\n")
schema = "net.launchpad.plank.dock.settings:/net/launchpad/plank/docks/mactahoe/"
for key, value in (("theme", "MacTahoe"), ("icon-size", "45"), ("hide-mode", "none")):
    subprocess.run(["gsettings", "set", schema, key, value], check=True)
sys.path.insert(0, str(ROOT / "apps/mactahoe-xfce-widgets"))
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk
from widgets import Widgets

children = []
failures = []
app = Widgets()
app.settings["show_weather"] = False  # Deterministic, offline test.


def exercise():
    try:
        assert len(app.windows) == 2
        assert app.clock_label.get_text()
        assert app.lunar_label.get_text()
        assert "RAM" in app.system_label.get_text(), app.system_label.get_text()
        assert not app.cards["weather"].get_visible()
        app.show_preferences()
        app.preferences.response(Gtk.ResponseType.APPLY)
        assert (Path(temporary.name) / ".config/mactahoe-xfce/widgets.json").is_file()
        app.preferences.destroy()
        app.settings["show_weather"] = True
        app.apply_visibility()
        app.finish_weather(app.weather_generation, "28°  Hà Nội", "Có mây\nĐộ ẩm 72% · Gió 8 km/h\nOpen-Meteo")
        app.toggle_rest()
        assert app.rest.on_break
        # Running the same command remotely must forward to the same application.
        children.append(subprocess.Popen(["python3", str(ROOT / "apps/mactahoe-xfce-widgets/widgets.py"), "--preferences"]))
        GLib.timeout_add_seconds(2, capture)
    except Exception as error:
        failures.append(error)
        app.quit()
    return False


def capture():
    try:
        assert app.preferences is not None
        app.preferences.destroy()
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
        if os.environ.get("MACTAHOE_UI_SCREENSHOT"):
            root = Gdk.get_default_root_window()
            image = Gdk.pixbuf_get_from_window(root, 0, 0, root.get_width(), root.get_height())
            image.savev(os.environ["MACTAHOE_UI_SCREENSHOT"], "png", [], [])
        # A queued remote --stop ends the primary instance.
        children.append(subprocess.Popen(["python3", str(ROOT / "apps/mactahoe-xfce-widgets/widgets.py"), "--stop"]))
    except Exception as error:
        failures.append(error)
        app.quit()
    return False


try:
    children.append(subprocess.Popen(["xfwm4", "--compositor=on"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    # The dock and widget windows must coexist with Xfce's desktop window.
    children.append(subprocess.Popen(["xfdesktop"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    children.append(subprocess.Popen(["plank", "--name=mactahoe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    GLib.timeout_add_seconds(4, exercise)
    GLib.timeout_add_seconds(25, lambda: (failures.append(RuntimeError("UI test timed out")), app.quit(), False)[-1])
    app.run(["widgets.py"])
    if failures:
        raise failures[0]
    print("PASS: X11 GTK widgets, preferences save, visibility, metrics, lunar, rest, single-instance and remote stop")
finally:
    for child in children:
        if child.poll() is None:
            child.terminate()
        child.wait(timeout=5)
    temporary.cleanup()
