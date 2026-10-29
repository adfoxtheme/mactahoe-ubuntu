import os
import json
import shutil
import glob

HOME = os.path.expanduser("~")
USER_THEMES_DIR = os.path.join(HOME, ".themes")
USER_ICONS_DIR = os.path.join(HOME, ".local", "share", "icons")
USER_GTK3_SETTINGS = os.path.join(HOME, ".config", "gtk-3.0", "settings.ini")

CHROME_INSTALLATIONS = [
    {
        "type": "Flatpak",
        "config_dir": os.path.join(HOME, ".var", "app", "com.google.Chrome", "config", "google-chrome"),
        "sandbox_root": os.path.join(HOME, ".var", "app", "com.google.Chrome"),
    },
    {
        "type": "Native (Arch / Debian / Fedora)",
        "config_dir": os.path.join(HOME, ".config", "google-chrome"),
        "sandbox_root": None,
    },
]


def update_preferences_theme(prefs_file, system_theme_val):
    """Safely update Chrome's theme Preferences JSON.

    Sets ``extensions.theme.system_theme = 1`` so Chrome follows the GTK
    theme (MacTahoe window controls), and pins
    ``browser.theme.user_color_scheme = 2`` (dark) so Chrome's color scheme
    matches the MacTahoe dark theme.
    """
    if not os.path.isfile(prefs_file):
        return False

    try:
        with open(prefs_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "extensions" not in data:
            data["extensions"] = {}
        if "theme" not in data["extensions"]:
            data["extensions"]["theme"] = {}
        data["extensions"]["theme"]["system_theme"] = system_theme_val

        if "browser" not in data:
            data["browser"] = {}
        if "theme" not in data["browser"]:
            data["browser"]["theme"] = {}
        if system_theme_val == 1:
            data["browser"]["theme"]["user_color_scheme"] = 2

        with open(prefs_file, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return True
    except Exception as e:
        print(f"[Chrome Themer] Failed to update {prefs_file}: {e}")
        return False


def get_preferences_system_theme(prefs_file):
    """Read system_theme value from Chrome's Preferences JSON."""
    if not os.path.isfile(prefs_file):
        return None
    try:
        with open(prefs_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("extensions", {}).get("theme", {}).get("system_theme", None)
    except Exception:
        return None


def detect_chrome():
    """Detect Chrome installations and current theme status."""
    found = []
    is_themed = False

    for item in CHROME_INSTALLATIONS:
        cfg = item["config_dir"]
        if os.path.isdir(cfg):
            def_prefs = os.path.join(cfg, "Default", "Preferences")
            val = get_preferences_system_theme(def_prefs)
            current_is_themed = (val == 1)
            if current_is_themed:
                is_themed = True

            found.append({
                "type": item["type"],
                "config_dir": cfg,
                "is_themed": current_is_themed,
                "system_theme": val,
            })

    is_installed = (
        len(found) > 0
        or shutil.which("google-chrome") is not None
        or shutil.which("google-chrome-stable") is not None
    )
    type_str = ", ".join(f["type"] for f in found) if found else ("Hệ thống" if is_installed else "Chưa cài đặt")

    return {
        "is_installed": is_installed,
        "installations": found,
        "is_themed": is_themed,
        "type_str": type_str,
    }


def ensure_system_gtk3_theme():
    """Ensure host system ~/.config/gtk-3.0/settings.ini specifies MacTahoe-Dark."""
    os.makedirs(os.path.dirname(USER_GTK3_SETTINGS), exist_ok=True)
    lines = []
    if os.path.isfile(USER_GTK3_SETTINGS):
        try:
            with open(USER_GTK3_SETTINGS, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            pass

    has_settings_header = False
    has_theme_name = False
    for i, line in enumerate(lines):
        if "[Settings]" in line:
            has_settings_header = True
        if line.strip().startswith("gtk-theme-name"):
            has_theme_name = True
            lines[i] = "gtk-theme-name=MacTahoe-Dark\n"

    if not has_settings_header:
        lines.insert(0, "[Settings]\n")
    if not has_theme_name:
        lines.append("gtk-theme-name=MacTahoe-Dark\n")

    try:
        with open(USER_GTK3_SETTINGS, "w", encoding="utf-8") as f:
            f.writelines(lines)
    except Exception as e:
        print(f"[Chrome Themer] Could not update {USER_GTK3_SETTINGS}: {e}")


def apply_chrome_theme():
    """Apply MacTahoe GTK theming to all detected Chrome installations."""
    status = detect_chrome()
    if not status["is_installed"]:
        return {"success": False, "message": "Không tìm thấy Google Chrome trên hệ thống!"}

    # 1. Update host GTK3 settings
    ensure_system_gtk3_theme()

    updated_count = 0

    for inst in status["installations"]:
        cfg = inst["config_dir"]
        sandbox_root = inst["sandbox_root"]

        # Flatpak: populate theme into the sandbox so GtkUi can resolve it
        if sandbox_root:
            sandbox_themes_dir = os.path.join(sandbox_root, ".themes")
            if os.path.islink(sandbox_themes_dir):
                os.unlink(sandbox_themes_dir)
            os.makedirs(sandbox_themes_dir, exist_ok=True)

            if os.path.isdir(USER_THEMES_DIR):
                for t in glob.glob(os.path.join(USER_THEMES_DIR, "MacTahoe*")):
                    bname = os.path.basename(t)
                    dst = os.path.join(sandbox_themes_dir, bname)
                    if not os.path.exists(dst):
                        if os.path.isdir(t):
                            shutil.copytree(t, dst, symlinks=True)

            sandbox_gtk3 = os.path.join(sandbox_root, ".config", "gtk-3.0")
            os.makedirs(sandbox_gtk3, exist_ok=True)
            sandbox_gtk3_ini = os.path.join(sandbox_gtk3, "settings.ini")
            try:
                with open(sandbox_gtk3_ini, "w", encoding="utf-8") as f:
                    f.write("[Settings]\ngtk-theme-name=MacTahoe-Dark\ngtk-application-prefer-dark-theme=1\n")
            except Exception:
                pass

        # Update theme prefs in all profiles under config_dir
        for prof_prefs in glob.glob(os.path.join(cfg, "*", "Preferences")):
            update_preferences_theme(prof_prefs, 1)

        updated_count += 1

    return {
        "success": True,
        "message": f"Đã kết nối giao diện GTK MacTahoe cho Google Chrome ({status['type_str']})!",
        "count": updated_count,
    }


def restore_chrome_default():
    """Restore Chrome to its default theme (system_theme = 0)."""
    status = detect_chrome()
    if not status["is_installed"]:
        return {"success": False, "message": "Không tìm thấy Google Chrome trên hệ thống!"}

    restored_count = 0
    for inst in status["installations"]:
        cfg = inst["config_dir"]
        for prof_prefs in glob.glob(os.path.join(cfg, "*", "Preferences")):
            update_preferences_theme(prof_prefs, 0)
        restored_count += 1

    return {
        "success": True,
        "message": f"Đã khôi phục Google Chrome về giao diện mặc định ({status['type_str']})!",
        "count": restored_count,
    }
