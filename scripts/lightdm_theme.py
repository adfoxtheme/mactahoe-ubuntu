#!/usr/bin/env python3
"""Install a GTK Greeter theme without changing the display manager or login policy.

All system targets are fixed; the root override exists only for isolated unit tests.
"""
import argparse
import configparser
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

TARGETS = {
    "config": "etc/lightdm/lightdm-gtk-greeter.conf",
    "theme": "usr/share/themes/MacTahoe-LightDM",
    "cursor": "usr/share/icons/MacTahoe-LightDM-cursors",
    "fonts": "usr/share/fonts/truetype/mactahoe-lightdm",
    "background": "usr/share/backgrounds/mactahoe-lightdm",
}


def themed_config(text):
    config = configparser.ConfigParser(interpolation=None, strict=False)
    config.read_string(text)
    if not config.has_section("greeter"):
        config.add_section("greeter")
    config["greeter"].update({
        "theme-name": "MacTahoe-LightDM", "icon-theme-name": "Adwaita",
        "cursor-theme-name": "MacTahoe-LightDM-cursors", "cursor-theme-size": "24",
        "font-name": "SF Pro Display 11", "user-background": "false",
        "background": "/usr/share/backgrounds/mactahoe-lightdm/background.jpeg",
        "position": "50%,center 50%,center", "round-user-image": "true",
        "clock-format": "%H:%M  ·  %A %d %B",
    })
    # Per-monitor backgrounds take precedence over the greeter section.
    for section in config.sections():
        if section.startswith("monitor:"):
            config[section]["background"] = config["greeter"]["background"]
            config[section]["user-background"] = "false"
    output = io.StringIO()
    config.write(output)
    return output.getvalue()


def validate_manager(root=Path("/"), show_config=None):
    default = root / "etc/X11/default-display-manager"
    service = root / "etc/systemd/system/display-manager.service"
    is_lightdm = default.exists() and Path(default.read_text().strip()).name == "lightdm"
    is_lightdm = is_lightdm or (service.is_symlink() and service.resolve().name == "lightdm.service")
    if not is_lightdm:
        raise ValueError("LightDM is not the configured display manager; no changes made.")
    if show_config is None:
        show_config = subprocess.check_output(["lightdm", "--show-config"], text=True, stderr=subprocess.STDOUT)
    # --show-config emits optional source letters before each effective option.
    greeters = re.findall(r"^\s*(?:[A-Z]\s+)?greeter-session\s*=\s*(\S+)", show_config, re.M)
    for greeter in greeters or ["lightdm-greeter"]:
        entry = root / "usr/share/xgreeters" / (greeter + ".desktop")
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(entry)
        command = parser.get("Desktop Entry", "Exec", fallback="").split()
        if not command or Path(command[0]).name != "lightdm-gtk-greeter":
            raise ValueError(f"Unsupported LightDM greeter: {greeter}. GTK Greeter is required.")


def remove(path):
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir() and not source.is_symlink():
        shutil.copytree(source, destination, symlinks=True)
    else:
        shutil.copy2(source, destination, follow_symlinks=False)


def atomic_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".mactahoe-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.chmod(name, 0o644)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class LightDMTheme:
    def __init__(self, root=Path("/")):
        self.root = root
        self.state = root / "var/lib/mactahoe-lightdm"
        self.targets = {key: root / value for key, value in TARGETS.items()}

    def snapshot(self):
        if (self.state / "snapshot.json").exists():
            return
        self.state.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix="mactahoe-lightdm-", dir=self.state.parent))
        stage.chmod(0o700)
        try:
            present = []
            for key, path in self.targets.items():
                if path.exists() or path.is_symlink():
                    copy(path, stage / key)
                    present.append(key)
            (stage / "snapshot.json").write_text(json.dumps(present))
            if self.state.exists():
                raise ValueError("Incomplete LightDM backup; inspect /var/lib/mactahoe-lightdm first.")
            stage.rename(self.state)
        finally:
            if stage.exists():
                shutil.rmtree(stage)

    def restore(self, discard=True):
        manifest = self.state / "snapshot.json"
        if not manifest.exists():
            raise ValueError("No MacTahoe LightDM backup was found.")
        present = json.loads(manifest.read_text())
        # Restore configuration before removing the resources it references.
        for key, path in self.targets.items():
            remove(path)
            if key in present:
                copy(self.state / key, path)
        if discard:
            shutil.rmtree(self.state)

    def install(self, theme, assets, cursor):
        for required in (theme / "gtk.css", assets / "wallpapers/MacTahoe-night.jpeg",
                         assets / "fonts/SF-Pro/SF-Pro-Display-Regular.otf", cursor / "index.theme"):
            if not required.is_file():
                raise ValueError(f"Required theme asset is missing: {required}")
        config = self.targets["config"]
        # Parse before any write. Preserve unrelated settings such as keyboard and accessibility.
        rendered = themed_config(config.read_text() if config.exists() else "")
        self.snapshot()
        try:
            for key in ("theme", "cursor", "fonts", "background"):
                remove(self.targets[key])
                self.targets[key].mkdir(parents=True, mode=0o755)
            shutil.copytree(theme, self.targets["theme"] / "gtk-3.0", symlinks=False)
            css = self.targets["theme"] / "gtk-3.0/gtk.css"
            with css.open("a") as stream:
                stream.write("\n#login_window { border-radius: 24px; padding: 24px; }\n")
            shutil.copytree(cursor, self.targets["cursor"], dirs_exist_ok=True, symlinks=False)
            shutil.copy2(assets / "wallpapers/MacTahoe-night.jpeg", self.targets["background"] / "background.jpeg")
            for weight in ("Regular", "Bold"):
                shutil.copy2(assets / f"fonts/SF-Pro/SF-Pro-Display-{weight}.otf", self.targets["fonts"])
            # Greeter must be able to traverse/read files regardless of the user's umask.
            for key in ("theme", "cursor", "fonts", "background"):
                for path in [self.targets[key], *self.targets[key].rglob("*")]:
                    path.chmod(0o755 if path.is_dir() else 0o644)
            atomic_text(config, rendered)
            (self.state / "installed").touch()
        except Exception:
            self.restore(discard=False)
            (self.state / "installed").unlink(missing_ok=True)
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "uninstall"))
    parser.add_argument("--theme", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--cursor", type=Path, required=True)
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error("Use install-lightdm.sh, which requests sudo.")
    manager = LightDMTheme()
    try:
        if args.action == "install":
            validate_manager()
            manager.install(args.theme, args.assets, args.cursor)
        else:
            manager.restore()
        subprocess.run(["fc-cache", "-f", "/usr/share/fonts"], check=False, stdout=subprocess.DEVNULL)
    except (OSError, ValueError, configparser.Error, subprocess.SubprocessError) as error:
        parser.exit(1, f"LightDM theme: {error}\n")
    print("LightDM theme " + ("installed" if args.action == "install" else "restored") + ". Reboot when ready; the current session was not restarted.")


if __name__ == "__main__":
    main()
