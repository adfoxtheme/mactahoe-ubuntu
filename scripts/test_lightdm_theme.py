import configparser
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from lightdm_theme import LightDMTheme, themed_config, validate_manager


class LightDMTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.manager = LightDMTheme(self.root)
        self.config = self.manager.targets["config"]
        self.config.parent.mkdir(parents=True)
        self.original = "[greeter]\nkeyboard=onboard\nbackground=old.jpg\n[monitor: HDMI-1]\nbackground=monitor.jpg\n"
        self.config.write_text(self.original)
        self.theme = self.root / "source/theme"
        self.assets = self.root / "source/assets"
        self.cursor = self.root / "source/cursor"
        for path, content in (
            (self.theme / "gtk.css", "* {color: white;}"),
            (self.assets / "wallpapers/MacTahoe-night.jpeg", "image"),
            (self.assets / "fonts/SF-Pro/SF-Pro-Display-Regular.otf", "font"),
            (self.assets / "fonts/SF-Pro/SF-Pro-Display-Bold.otf", "font"),
            (self.cursor / "index.theme", "[Icon Theme]\nName=Cursor"),
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)

    def test_config_preserves_accessibility_and_overrides_monitor(self):
        parser = configparser.ConfigParser(interpolation=None)
        parser.read_string(themed_config(self.original))
        self.assertEqual(parser["greeter"]["keyboard"], "onboard")
        self.assertEqual(parser["monitor: HDMI-1"]["background"], parser["greeter"]["background"])
        self.assertEqual(parser["greeter"]["user-background"], "false")

    def test_install_repeat_restore_original_and_existing_assets(self):
        old_theme = self.manager.targets["theme"]
        old_theme.mkdir(parents=True)
        (old_theme / "pre-existing").write_text("preserve me")
        self.manager.install(self.theme, self.assets, self.cursor)
        self.assertIn("MacTahoe-LightDM", self.config.read_text())
        self.manager.install(self.theme, self.assets, self.cursor)
        self.manager.restore()
        self.assertEqual(self.config.read_text(), self.original)
        self.assertEqual((old_theme / "pre-existing").read_text(), "preserve me")
        self.assertFalse(self.manager.targets["fonts"].exists())
        self.assertFalse(self.manager.state.exists())

    def test_failed_copy_rolls_back_config_and_assets(self):
        with patch("lightdm_theme.shutil.copytree", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.manager.install(self.theme, self.assets, self.cursor)
        self.assertEqual(self.config.read_text(), self.original)
        self.assertFalse(self.manager.targets["theme"].exists())
        self.assertFalse((self.manager.state / "installed").exists())

    def test_config_symlink_is_restored(self):
        vendor = self.root / "vendor.conf"
        vendor.write_text(self.original)
        self.config.unlink()
        self.config.symlink_to(vendor)
        self.manager.install(self.theme, self.assets, self.cursor)
        self.assertFalse(self.config.is_symlink())
        self.assertEqual(vendor.read_text(), self.original)
        self.manager.restore()
        self.assertTrue(self.config.is_symlink())

    def test_manager_and_greeter_checks(self):
        with self.assertRaises(ValueError):
            validate_manager(self.root, "")
        default = self.root / "etc/X11/default-display-manager"
        default.parent.mkdir(parents=True)
        default.write_text("/usr/sbin/lightdm\n")
        entry = self.root / "usr/share/xgreeters/lightdm-gtk-greeter.desktop"
        entry.parent.mkdir(parents=True)
        entry.write_text("[Desktop Entry]\nExec=lightdm-gtk-greeter\n")
        validate_manager(self.root, "A  greeter-session=lightdm-gtk-greeter\n")
        with self.assertRaises(ValueError):
            validate_manager(self.root, "B  greeter-session=slick-greeter\n")


if __name__ == "__main__":
    unittest.main()
