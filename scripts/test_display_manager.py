from pathlib import Path
import tempfile
import unittest

from display_manager import detect_manager
from wallpaper_properties import wallpaper_properties


class ManagerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def test_unknown_does_not_guess_from_installed_desktop(self):
        self.assertEqual(detect_manager(self.root), "unknown")

    def test_debian_configured_managers(self):
        default = self.root / "etc/X11/default-display-manager"
        default.parent.mkdir(parents=True)
        for name, expected in (("gdm3", "gdm"), ("gdm", "gdm"), ("lightdm", "lightdm"), ("sddm", "unknown")):
            default.write_text(f"/usr/sbin/{name}\n")
            self.assertEqual(detect_manager(self.root), expected)

    def test_service_and_active_manager_take_precedence(self):
        default = self.root / "etc/X11/default-display-manager"
        default.parent.mkdir(parents=True)
        default.write_text("/usr/sbin/lightdm")
        service = self.root / "etc/systemd/system/display-manager.service"
        service.parent.mkdir(parents=True)
        service.symlink_to("/usr/lib/systemd/system/gdm.service")
        self.assertEqual(detect_manager(self.root), "gdm")
        self.assertEqual(detect_manager(self.root, "/usr/lib/systemd/system/lightdm.service"), "lightdm")
        self.assertEqual(detect_manager(self.root, "/usr/lib/systemd/system/sddm.service"), "unknown")


class WallpaperTests(unittest.TestCase):
    def test_existing_monitors_and_workspaces(self):
        raw = "\n".join(("/backdrop/screen0/monitorVirtual1/workspace0/last-image",
                         "/backdrop/screen0/monitorHDMI-1/workspace2/image-style",
                         "/desktop-icons/style"))
        self.assertEqual(wallpaper_properties(raw), [
            "/backdrop/screen0/monitorHDMI-1/workspace2/last-image",
            "/backdrop/screen0/monitorVirtual1/workspace0/last-image",
        ])

    def test_fresh_profile_generates_real_monitor_paths(self):
        found = wallpaper_properties("", ["Virtual1", "HDMI-1"], 4)
        self.assertEqual(len(found), 8)
        self.assertIn("/backdrop/screen0/monitorVirtual1/workspace3/last-image", found)


if __name__ == "__main__":
    unittest.main()
