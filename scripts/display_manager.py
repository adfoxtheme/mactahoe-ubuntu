"""Detect the active/configured display manager independently of the desktop."""
from pathlib import Path
import subprocess


def manager_name(identity):
    name = Path(identity.strip()).name.removesuffix(".service")
    return {"gdm3": "gdm", "gdm": "gdm", "lightdm": "lightdm"}.get(name, "unknown")


def detect_manager(root=Path("/"), active_identity=None):
    if active_identity is None and root == Path("/"):
        try:
            active = subprocess.run(["systemctl", "is-active", "--quiet", "display-manager.service"],
                                    timeout=3, capture_output=True)
            if active.returncode == 0:
                active_identity = subprocess.check_output([
                    "systemctl", "show", "display-manager.service", "--property=FragmentPath", "--value",
                ], timeout=3, text=True, stderr=subprocess.DEVNULL)
        except (OSError, subprocess.SubprocessError):
            pass
    if active_identity:
        return manager_name(active_identity)
    service = root / "etc/systemd/system/display-manager.service"
    if service.is_symlink():
        # A configured alternative takes precedence over the Debian fallback file.
        return manager_name(str(service.resolve()))
    try:
        return manager_name((root / "etc/X11/default-display-manager").read_text())
    except OSError:
        return "unknown"


if __name__ == "__main__":
    print(detect_manager())
