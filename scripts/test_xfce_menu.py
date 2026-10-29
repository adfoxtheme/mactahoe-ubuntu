import unittest
from xfce_menu import IMPORT, add_import, update_rc


class MenuFilesTests(unittest.TestCase):
    def test_rc_preserves_favorites_kali_menu_and_search_actions(self):
        original = ("# user configuration\nfavorites=kali-tools.desktop,firefox-esr.desktop\n"
                    "custom-menu-file=/etc/xdg/menus/kali-applications.menu\nmenu-width=450\n"
                    "[search-action0]\nname=Search files\ncommand=catfish %s\n")
        result = update_rc(original, {"menu-width": "740", "view-as-icons": "true"})
        self.assertIn("favorites=kali-tools.desktop,firefox-esr.desktop", result)
        self.assertIn("custom-menu-file=/etc/xdg/menus/kali-applications.menu", result)
        self.assertIn("[search-action0]\nname=Search files\ncommand=catfish %s", result)
        self.assertEqual(result.count("menu-width="), 1)
        self.assertLess(result.index("view-as-icons=true"), result.index("[search-action0]"))
        self.assertEqual(update_rc(result, {"menu-width": "740", "view-as-icons": "true"}), result)

    def test_css_reinstall_keeps_user_rules_and_single_import(self):
        original = "/* custom */\nwindow { color: red; }\n"
        result = add_import(original)
        self.assertEqual(add_import(result), result)
        self.assertEqual(result.count(IMPORT), 1)
        self.assertIn(original.strip(), result)


if __name__ == "__main__":
    unittest.main()
