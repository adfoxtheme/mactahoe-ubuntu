import os
import json
import shutil
import glob

HOME = os.path.expanduser("~")
USER_THEMES_DIR = os.path.join(HOME, ".themes")
USER_ICONS_DIR = os.path.join(HOME, ".local", "share", "icons")
USER_GTK3_SETTINGS = os.path.join(HOME, ".config", "gtk-3.0", "settings.ini")

BRAVE_INSTALLATIONS = [
    {
        "type": "Snap (Ubuntu)",
        "config_dir": os.path.join(HOME, "snap", "brave", "current", ".config", "BraveSoftware", "Brave-Browser"),
        "snap_root": os.path.join(HOME, "snap", "brave", "current"),
    },
    {
        "type": "Native (Debian / Fedora / CachyOS / Ubuntu Deb)",
        "config_dir": os.path.join(HOME, ".config", "BraveSoftware", "Brave-Browser"),
        "snap_root": None,
    },
    {
        "type": "Flatpak",
        "config_dir": os.path.join(HOME, ".var", "app", "com.brave.Browser", "config", "BraveSoftware", "Brave-Browser"),
        "snap_root": os.path.join(HOME, ".var", "app", "com.brave.Browser"),
    },
]


def update_preferences_system_theme(prefs_file, system_theme_val):
    """Safely update system_theme in Brave's Preferences JSON."""
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

        with open(prefs_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"[Brave Themer] Failed to update {prefs_file}: {e}")
        return False


def get_preferences_system_theme(prefs_file):
    """Read system_theme value from Brave's Preferences JSON."""
    if not os.path.isfile(prefs_file):
        return None
    try:
        with open(prefs_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("extensions", {}).get("theme", {}).get("system_theme", None)
    except Exception:
        return None


def detect_brave():
    """Detect Brave installations and current theme status."""
    found = []
    is_themed = False

    for item in BRAVE_INSTALLATIONS:
        cfg = item["config_dir"]
        if os.path.isdir(cfg):
            # Check Default profile
            def_prefs = os.path.join(cfg, "Default", "Preferences")
            val = get_preferences_system_theme(def_prefs)
            snap_themes_ok = True

            if item["snap_root"] and "snap" in item["type"].lower():
                snap_themes_dir = os.path.join(item["snap_root"], ".themes", "MacTahoe-Dark")
                snap_themes_ok = os.path.isdir(snap_themes_dir)

            current_is_themed = (val == 1) and snap_themes_ok
            if current_is_themed:
                is_themed = True

            found.append({
                "type": item["type"],
                "config_dir": cfg,
                "snap_root": item["snap_root"],
                "is_themed": current_is_themed,
                "system_theme": val,
            })

    is_installed = len(found) > 0 or shutil.which("brave") is not None or shutil.which("brave-browser") is not None
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
        print(f"[Brave Themer] Could not update {USER_GTK3_SETTINGS}: {e}")


def is_brave_running():
    import subprocess
    try:
        out = subprocess.check_output(["pgrep", "-u", str(os.getuid()), "brave"]).decode().strip()
        return bool(out)
    except Exception:
        return False


def apply_brave_theme():
    """Apply MacTahoe GTK theming to all detected Brave installations."""
    status = detect_brave()
    if not status["is_installed"]:
        return {"success": False, "message": "Không tìm thấy Brave trên hệ thống!"}

    # 1. Update host GTK3 settings
    ensure_system_gtk3_theme()

    updated_count = 0
    running = is_brave_running()

    for inst in status["installations"]:
        cfg = inst["config_dir"]
        snap_root = inst["snap_root"]

        # If Snap: populate theme into snap sandbox
        if snap_root and "snap" in inst["type"].lower():
            snap_themes_dir = os.path.join(snap_root, ".themes")
            if os.path.islink(snap_themes_dir):
                os.unlink(snap_themes_dir)
            os.makedirs(snap_themes_dir, exist_ok=True)

            # Copy MacTahoe themes from ~/.themes
            if os.path.isdir(USER_THEMES_DIR):
                for t in glob.glob(os.path.join(USER_THEMES_DIR, "MacTahoe*")):
                    bname = os.path.basename(t)
                    dst = os.path.join(snap_themes_dir, bname)
                    if not os.path.exists(dst):
                        if os.path.isdir(t):
                            shutil.copytree(t, dst, symlinks=True)

            # Copy icons / cursors
            snap_icons_dir = os.path.join(snap_root, ".local", "share", "icons")
            os.makedirs(snap_icons_dir, exist_ok=True)
            if os.path.isdir(USER_ICONS_DIR):
                for ic in glob.glob(os.path.join(USER_ICONS_DIR, "MacTahoe*")):
                    bname = os.path.basename(ic)
                    dst = os.path.join(snap_icons_dir, bname)
                    if not os.path.exists(dst):
                        if os.path.isdir(ic):
                            shutil.copytree(ic, dst, symlinks=True)

            # Configure gtk-3.0 in snap
            snap_gtk3 = os.path.join(snap_root, ".config", "gtk-3.0")
            os.makedirs(snap_gtk3, exist_ok=True)
            snap_gtk3_ini = os.path.join(snap_gtk3, "settings.ini")
            try:
                with open(snap_gtk3_ini, "w", encoding="utf-8") as f:
                    f.write("[Settings]\ngtk-theme-name=MacTahoe-Dark\ngtk-application-prefer-dark-theme=1\n")
            except Exception:
                pass

        # Update system_theme = 1 in all profiles under config_dir
        for prof_prefs in glob.glob(os.path.join(cfg, "*", "Preferences")):
            update_preferences_system_theme(prof_prefs, 1)

        updated_count += 1

    msg = f"Đã kết nối giao diện GTK MacTahoe cho Brave ({status['type_str']})!"
    if running:
        msg += " Hãy đóng và mở lại Brave để nạp giao diện mới."

    return {
        "success": True,
        "message": msg,
        "count": updated_count,
    }


def restore_brave_default():
    """Restore Brave to default Classic theme (system_theme = 0)."""
    status = detect_brave()
    if not status["is_installed"]:
        return {"success": False, "message": "Không tìm thấy Brave trên hệ thống!"}

    restored_count = 0
    for inst in status["installations"]:
        cfg = inst["config_dir"]
        for prof_prefs in glob.glob(os.path.join(cfg, "*", "Preferences")):
            update_preferences_system_theme(prof_prefs, 0)
        restored_count += 1

    return {
        "success": True,
        "message": f"Đã khôi phục Brave về giao diện mặc định ({status['type_str']})!",
        "count": restored_count,
    }
