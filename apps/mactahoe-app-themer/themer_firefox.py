import os
import shutil
import glob

HOME = os.path.expanduser("~")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FIREFOX_SRC_ASSETS = os.path.join(SCRIPT_DIR, "assets", "firefox")

FIREFOX_SEARCH_PATHS = [
    {
        "type": "Snap (Ubuntu)",
        "base_dir": os.path.join(HOME, "snap", "firefox", "common", ".mozilla", "firefox"),
    },
    {
        "type": "Native (Debian / Fedora / CachyOS / Ubuntu PPA)",
        "base_dir": os.path.join(HOME, ".mozilla", "firefox"),
    },
    {
        "type": "Native Config (XDG)",
        "base_dir": os.path.join(HOME, ".config", "mozilla", "firefox"),
    },
    {
        "type": "Flatpak",
        "base_dir": os.path.join(HOME, ".var", "app", "org.mozilla.firefox", "config", "mozilla", "firefox"),
    },
    {
        "type": "Flatpak (Legacy Home)",
        "base_dir": os.path.join(HOME, ".var", "app", "org.mozilla.firefox", ".mozilla", "firefox"),
    },
]

REQUIRED_USER_JS_PREFS = [
    'user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);',
    'user_pref("browser.tabs.drawInTitlebar", true);',
    'user_pref("browser.uidensity", 0);',
    'user_pref("layers.acceleration.force-enabled", true);',
    'user_pref("mozilla.widget.use-argb-visuals", true);',
    'user_pref("widget.gtk.rounded-bottom-corners.enabled", true);',
    'user_pref("svg.context-properties.content.enabled", true);',
]


def find_profile_dirs(base_dir):
    """Find all valid profile directories inside a Firefox base dir."""
    if not os.path.isdir(base_dir):
        return []

    profiles = set()

    # 1. Parse profiles.ini if present
    profiles_ini = os.path.join(base_dir, "profiles.ini")
    if os.path.isfile(profiles_ini):
        try:
            with open(profiles_ini, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("Path="):
                        p_rel = line.split("=", 1)[1].strip()
                        p_abs = os.path.normpath(os.path.join(base_dir, p_rel))
                        if os.path.isdir(p_abs):
                            profiles.add(p_abs)
        except Exception as e:
            print(f"[Firefox Themer] Error reading profiles.ini: {e}")

    # 2. Also glob *default* and check for prefs.js
    for entry in os.listdir(base_dir):
        full_path = os.path.join(base_dir, entry)
        if os.path.isdir(full_path):
            if "default" in entry.lower() or os.path.isfile(os.path.join(full_path, "prefs.js")):
                profiles.add(full_path)

    # Exclude themes dir itself
    themes_dir = os.path.join(base_dir, "firefox-themes")
    if themes_dir in profiles:
        profiles.remove(themes_dir)

    return sorted(list(profiles))


def detect_firefox():
    """Detect Firefox installations, profiles, and theme status."""
    installations = []
    total_profiles = []
    is_themed = False

    for item in FIREFOX_SEARCH_PATHS:
        base_dir = item["base_dir"]
        if os.path.isdir(base_dir):
            profs = find_profile_dirs(base_dir)
            if profs:
                installations.append({
                    "type": item["type"],
                    "base_dir": base_dir,
                    "profiles": profs,
                })
                total_profiles.extend(profs)

                # Check if any profile has MacTahoe theme applied
                for p in profs:
                    chrome_dir = os.path.join(p, "chrome")
                    user_chrome = os.path.join(chrome_dir, "userChrome.css")
                    if os.path.exists(user_chrome):
                        try:
                            with open(user_chrome, "r", encoding="utf-8", errors="ignore") as f:
                                content = f.read(500)
                                if "MacTahoe" in content or "Tahoe" in content or "Safari" in content:
                                    is_themed = True
                        except Exception:
                            pass

    is_installed = len(installations) > 0 or shutil.which("firefox") is not None

    type_str = ", ".join(i["type"] for i in installations) if installations else ("System" if is_installed else "Not installed")

    return {
        "is_installed": is_installed,
        "installations": installations,
        "profiles": total_profiles,
        "is_themed": is_themed,
        "type_str": type_str,
    }


def apply_firefox_theme():
    """Apply the macOS Tahoe Safari theme to all detected Firefox profiles."""
    status = detect_firefox()
    if not status["is_installed"]:
        return {"success": False, "message": "Firefox was not found on this system."}

    if not os.path.isdir(FIREFOX_SRC_ASSETS):
        return {"success": False, "message": f"Theme assets were not found at {FIREFOX_SRC_ASSETS}."}

    updated_profiles = 0

    for inst in status["installations"]:
        base_dir = inst["base_dir"]
        target_theme_dir = os.path.join(base_dir, "firefox-themes")
        os.makedirs(target_theme_dir, exist_ok=True)

        # Copy theme files into target_theme_dir
        # MacTahoe/
        src_mactahoe = os.path.join(FIREFOX_SRC_ASSETS, "MacTahoe")
        dst_mactahoe = os.path.join(target_theme_dir, "MacTahoe")
        if os.path.isdir(src_mactahoe):
            if os.path.exists(dst_mactahoe):
                if os.path.islink(dst_mactahoe):
                    os.unlink(dst_mactahoe)
                else:
                    shutil.rmtree(dst_mactahoe)
            shutil.copytree(src_mactahoe, dst_mactahoe)

        # CSS files
        for fname in ["customChrome.css", "userChrome.css", "userContent.css"]:
            src_f = os.path.join(FIREFOX_SRC_ASSETS, fname)
            dst_f = os.path.join(target_theme_dir, fname)
            if os.path.isfile(src_f):
                shutil.copy2(src_f, dst_f)

        # For each profile, symlink chrome -> firefox-themes and setup user.js
        for p in inst["profiles"]:
            chrome_link = os.path.join(p, "chrome")
            if os.path.exists(chrome_link) or os.path.islink(chrome_link):
                if os.path.islink(chrome_link):
                    os.unlink(chrome_link)
                else:
                    shutil.rmtree(chrome_link)

            try:
                os.symlink(target_theme_dir, chrome_link)
            except Exception as e:
                print(f"[Firefox Themer] Failed to symlink chrome in {p}: {e}")
                # Fallback to copytree
                shutil.copytree(target_theme_dir, chrome_link)

            # Update user.js
            user_js = os.path.join(p, "user.js")
            existing_lines = []
            if os.path.isfile(user_js):
                try:
                    with open(user_js, "r", encoding="utf-8", errors="ignore") as f:
                        existing_lines = f.readlines()
                except Exception:
                    pass

            existing_text = "".join(existing_lines)
            with open(user_js, "a", encoding="utf-8") as f:
                f.write("\n// --- MacTahoe Safari Theme Preferences ---\n")
                for pref in REQUIRED_USER_JS_PREFS:
                    pref_key = pref.split('"')[1]
                    if pref_key not in existing_text:
                        f.write(pref + "\n")

            updated_profiles += 1

    return {
        "success": True,
        "message": f"Applied the macOS Tahoe Safari theme to {updated_profiles} Firefox profiles.",
        "count": updated_profiles,
    }


def restore_firefox_default():
    """Remove Safari theme from all Firefox profiles and restore defaults."""
    status = detect_firefox()
    if not status["is_installed"]:
        return {"success": False, "message": "Firefox was not found on this system."}

    restored_profiles = 0

    for inst in status["installations"]:
        base_dir = inst["base_dir"]
        target_theme_dir = os.path.join(base_dir, "firefox-themes")

        for p in inst["profiles"]:
            chrome_link = os.path.join(p, "chrome")
            if os.path.exists(chrome_link) or os.path.islink(chrome_link):
                if os.path.islink(chrome_link):
                    os.unlink(chrome_link)
                else:
                    shutil.rmtree(chrome_link)

            # Clean user.js MacTahoe preferences
            user_js = os.path.join(p, "user.js")
            if os.path.isfile(user_js):
                try:
                    with open(user_js, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                    filtered = [
                        l for l in lines
                        if "MacTahoe" not in l and "toolkit.legacyUserProfileCustomizations.stylesheets" not in l
                    ]
                    with open(user_js, "w", encoding="utf-8") as f:
                        f.writelines(filtered)
                except Exception as e:
                    print(f"[Firefox Themer] Error cleaning user.js: {e}")

            restored_profiles += 1

        # Optionally remove target_theme_dir
        if os.path.isdir(target_theme_dir):
            try:
                shutil.rmtree(target_theme_dir)
            except Exception:
                pass

    return {
        "success": True,
        "message": f"Restored {restored_profiles} Firefox profiles to the default appearance.",
        "count": restored_profiles,
    }
