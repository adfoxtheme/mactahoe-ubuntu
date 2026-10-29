#!/usr/bin/env python3
import sys
import os
import platform

# Ensure local imports work
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib

import themer_firefox
import themer_brave
import themer_chrome

APP_ID = "io.github.adfoxtheme.MacTahoeAppThemer"


class AppThemerWindow(Adw.PreferencesWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("Giao diện ứng dụng")
        self.set_default_size(720, 580)

        self.page = Adw.PreferencesPage()
        self.page.set_title("Ứng dụng hỗ trợ")
        self.page.set_icon_name("preferences-desktop-theme-applications")
        self.add(self.page)

        # Build groups
        self._build_firefox_group()
        self._build_brave_group()
        self._build_chrome_group()
        self._build_system_info_group()

        # Initial data refresh
        self.refresh_status()

    def _build_firefox_group(self):
        self.ff_group = Adw.PreferencesGroup()
        self.ff_group.set_title("Mozilla Firefox (Safari macOS Tahoe)")
        self.ff_group.set_description(
            "Nạp giao diện Safari chuẩn macOS Tahoe: nút tròn đỏ vàng xanh, thanh địa chỉ bo tròn giữa, thiết kế tab phẳng Safari"
        )
        self.page.add(self.ff_group)

        # Status row
        self.ff_status_row = Adw.ActionRow()
        self.ff_status_row.set_title("Trạng thái")
        self.ff_status_row.set_subtitle("Đang kiểm tra...")
        self.ff_status_row.set_icon_name("firefox")
        self.ff_group.add(self.ff_status_row)

        # Action row with Apply and Restore buttons
        self.ff_action_row = Adw.ActionRow()
        self.ff_action_row.set_title("Giao diện Safari")
        self.ff_action_row.set_subtitle("Áp dụng skin Safari Tahoe hoặc khôi phục về giao diện gốc của Firefox")

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_valign(Gtk.Align.CENTER)

        self.ff_apply_btn = Gtk.Button(label="Áp dụng")
        self.ff_apply_btn.add_css_class("suggested-action")
        self.ff_apply_btn.connect("clicked", self.on_firefox_apply)
        btn_box.append(self.ff_apply_btn)

        self.ff_restore_btn = Gtk.Button(label="Khôi phục")
        self.ff_restore_btn.add_css_class("destructive-action")
        self.ff_restore_btn.connect("clicked", self.on_firefox_restore)
        btn_box.append(self.ff_restore_btn)

        self.ff_action_row.add_suffix(btn_box)
        self.ff_group.add(self.ff_action_row)

    def _build_brave_group(self):
        self.brave_group = Adw.PreferencesGroup()
        self.brave_group.set_title("Brave Browser (Đồng bộ GTK & MacTahoe)")
        self.brave_group.set_description(
            "Đồng bộ bộ theme MacTahoe và con trỏ chuột vào môi trường của Brave (hỗ trợ cả Snap, Flatpak và Native)"
        )
        self.page.add(self.brave_group)

        # Status row
        self.brave_status_row = Adw.ActionRow()
        self.brave_status_row.set_title("Trạng thái")
        self.brave_status_row.set_subtitle("Đang kiểm tra...")
        self.brave_status_row.set_icon_name("brave")
        self.brave_group.add(self.brave_status_row)

        # Action row
        self.brave_action_row = Adw.ActionRow()
        self.brave_action_row.set_title("Giao diện GTK")
        self.brave_action_row.set_subtitle("Kết nối theme MacTahoe vào vùng cách ly hoặc đặt lại giao diện mặc định")

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_valign(Gtk.Align.CENTER)

        self.brave_apply_btn = Gtk.Button(label="Áp dụng")
        self.brave_apply_btn.add_css_class("suggested-action")
        self.brave_apply_btn.connect("clicked", self.on_brave_apply)
        btn_box.append(self.brave_apply_btn)

        self.brave_restore_btn = Gtk.Button(label="Khôi phục")
        self.brave_restore_btn.add_css_class("destructive-action")
        self.brave_restore_btn.connect("clicked", self.on_brave_restore)
        btn_box.append(self.brave_restore_btn)

        self.brave_action_row.add_suffix(btn_box)
        self.brave_group.add(self.brave_action_row)

    def _build_chrome_group(self):
        self.chrome_group = Adw.PreferencesGroup()
        self.chrome_group.set_title("Google Chrome (Đồng bộ GTK & MacTahoe)")
        self.chrome_group.set_description(
            "Đồng bộ theme GTK MacTahoe vào Google Chrome để giao diện trình duyệt "
            "(tab, thanh công cụ, New Tab) theo đúng màu tối của MacTahoe"
        )
        self.page.add(self.chrome_group)

        # Status row
        self.chrome_status_row = Adw.ActionRow()
        self.chrome_status_row.set_title("Trạng thái")
        self.chrome_status_row.set_subtitle("Đang kiểm tra...")
        self.chrome_status_row.set_icon_name("google-chrome")
        self.chrome_group.add(self.chrome_status_row)

        # Action row
        self.chrome_action_row = Adw.ActionRow()
        self.chrome_action_row.set_title("Giao diện GTK")
        self.chrome_action_row.set_subtitle("Kết nối theme GTK MacTahoe hoặc đặt lại giao diện mặc định")

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_valign(Gtk.Align.CENTER)

        self.chrome_apply_btn = Gtk.Button(label="Áp dụng")
        self.chrome_apply_btn.add_css_class("suggested-action")
        self.chrome_apply_btn.connect("clicked", self.on_chrome_apply)
        btn_box.append(self.chrome_apply_btn)

        self.chrome_restore_btn = Gtk.Button(label="Khôi phục")
        self.chrome_restore_btn.add_css_class("destructive-action")
        self.chrome_restore_btn.connect("clicked", self.on_chrome_restore)
        btn_box.append(self.chrome_restore_btn)

        self.chrome_action_row.add_suffix(btn_box)
        self.chrome_group.add(self.chrome_action_row)

    def _build_system_info_group(self):
        sys_group = Adw.PreferencesGroup()
        sys_group.set_title("Thông tin môi trường")
        sys_group.set_description("Thông tin hệ điều hành và giao diện đang chạy")
        self.page.add(sys_group)

        # OS info
        os_row = Adw.ActionRow()
        os_row.set_title("Hệ điều hành")
        os_info = "Linux"
        try:
            if os.path.isfile("/etc/os-release"):
                with open("/etc/os-release") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="):
                            os_info = line.split("=", 1)[1].strip().strip('"')
                            break
        except Exception:
            pass
        os_row.set_subtitle(os_info)
        os_row.set_icon_name("system-software-install-symbolic")
        sys_group.add(os_row)

        # Active GTK theme
        theme_row = Adw.ActionRow()
        theme_row.set_title("Giao diện hệ thống hiện tại")
        current_theme = "Mặc định"
        try:
            settings = Gio.Settings.new("org.gnome.desktop.interface")
            current_theme = settings.get_string("gtk-theme")
        except Exception:
            pass
        theme_row.set_subtitle(current_theme)
        theme_row.set_icon_name("preferences-desktop-theme-symbolic")
        sys_group.add(theme_row)

    def refresh_status(self):
        # 1. Check Firefox
        ff_info = themer_firefox.detect_firefox()
        if not ff_info["is_installed"]:
            self.ff_status_row.set_subtitle("Chưa cài đặt trên máy")
            self.ff_apply_btn.set_sensitive(False)
            self.ff_restore_btn.set_sensitive(False)
        else:
            status_text = f"Đã cài đặt: {ff_info['type_str']} ({len(ff_info['profiles'])} hồ sơ)"
            if ff_info["is_themed"]:
                status_text += " • [Đang dùng skin Safari Tahoe]"
            else:
                status_text += " • [Giao diện mặc định của Mozilla]"
            self.ff_status_row.set_subtitle(status_text)
            self.ff_apply_btn.set_sensitive(True)
            self.ff_restore_btn.set_sensitive(ff_info["is_themed"])

        # 2. Check Brave
        br_info = themer_brave.detect_brave()
        if not br_info["is_installed"]:
            self.brave_status_row.set_subtitle("Chưa cài đặt trên máy")
            self.brave_apply_btn.set_sensitive(False)
            self.brave_restore_btn.set_sensitive(False)
        else:
            status_text = f"Đã cài đặt: {br_info['type_str']}"
            if br_info["is_themed"]:
                status_text += " • [Đã kết nối GTK MacTahoe]"
            else:
                status_text += " • [Giao diện mặc định của Brave]"
            self.brave_status_row.set_subtitle(status_text)
            self.brave_apply_btn.set_sensitive(True)
            self.brave_restore_btn.set_sensitive(br_info["is_themed"])

        # 3. Check Chrome
        ch_info = themer_chrome.detect_chrome()
        if not ch_info["is_installed"]:
            self.chrome_status_row.set_subtitle("Chưa cài đặt trên máy")
            self.chrome_apply_btn.set_sensitive(False)
            self.chrome_restore_btn.set_sensitive(False)
        else:
            status_text = f"Đã cài đặt: {ch_info['type_str']}"
            if ch_info["is_themed"]:
                status_text += " • [Đã kết nối GTK MacTahoe]"
            else:
                status_text += " • [Giao diện mặc định của Chrome]"
            self.chrome_status_row.set_subtitle(status_text)
            self.chrome_apply_btn.set_sensitive(True)
            self.chrome_restore_btn.set_sensitive(ch_info["is_themed"])

    def on_firefox_apply(self, btn):
        res = themer_firefox.apply_firefox_theme()
        self.refresh_status()
        self.add_toast(Adw.Toast(title=res["message"], timeout=3))

    def on_firefox_restore(self, btn):
        res = themer_firefox.restore_firefox_default()
        self.refresh_status()
        self.add_toast(Adw.Toast(title=res["message"], timeout=3))

    def on_brave_apply(self, btn):
        res = themer_brave.apply_brave_theme()
        self.refresh_status()
        self.add_toast(Adw.Toast(title=res["message"], timeout=3))

    def on_brave_restore(self, btn):
        res = themer_brave.restore_brave_default()
        self.refresh_status()
        self.add_toast(Adw.Toast(title=res["message"], timeout=3))

    def on_chrome_apply(self, btn):
        res = themer_chrome.apply_chrome_theme()
        self.refresh_status()
        self.add_toast(Adw.Toast(title=res["message"], timeout=3))

    def on_chrome_restore(self, btn):
        res = themer_chrome.restore_chrome_default()
        self.refresh_status()
        self.add_toast(Adw.Toast(title=res["message"], timeout=3))


class AppThemerApplication(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = AppThemerWindow(self)
        win.present()


def main():
    GLib.set_prgname(APP_ID)
    GLib.set_application_name("Giao diện ứng dụng")
    app = AppThemerApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
