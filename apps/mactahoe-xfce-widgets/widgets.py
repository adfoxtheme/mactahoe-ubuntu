#!/usr/bin/env python3
"""Tahoe desktop widgets for Xfce/X11. One process per user D-Bus session."""
import datetime as dt
from pathlib import Path
import subprocess
import sys
import threading
import time

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gio, GLib, Gtk

from model import Metrics, RestTimer, fetch_weather, load_settings, save_settings

# Use the same Vietnamese calendar algorithm as the bundled calendar app.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "am-lich-viet-nam"))
from lunar import convert_solar_to_lunar


class DesktopWindow(Gtk.ApplicationWindow):
    def __init__(self, app, title):
        super().__init__(application=app, title=title)
        self.set_decorated(False)
        self.set_resizable(False)
        # Xfdesktop owns the DESKTOP layer and can repaint over peer desktop windows.
        # A utility window kept below stays above it and beneath application windows.
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_below(True)
        self.set_accept_focus(False)
        self.stick()
        self.set_app_paintable(True)
        visual = self.get_screen().get_rgba_visual()
        if visual:
            self.set_visual(visual)
        self.get_style_context().add_class("tahoe-desktop")


def label(text="", style=None):
    widget = Gtk.Label(label=text, xalign=0)
    widget.set_line_wrap(True)
    widget.set_max_width_chars(36)
    if style:
        widget.get_style_context().add_class(style)
    return widget


def card(title):
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    box.get_style_context().add_class("tahoe-card")
    box.pack_start(label(title, "eyebrow"), False, False, 0)
    return box


class Widgets(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="io.github.adfoxtheme.XfceWidgets",
                         flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.settings = load_settings()
        self.windows = []
        self.preferences = None
        self.weather_due = 0
        self.weather_busy = False
        self.metric_busy = False
        self.weather_generation = 0
        self.rest = RestTimer()

    def do_startup(self):
        Gtk.Application.do_startup(self)
        provider = Gtk.CssProvider()
        provider.load_from_path(str(Path(__file__).with_name("style.css")))
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def do_command_line(self, command_line):
        args = command_line.get_arguments()[1:]
        if args == ["--stop"]:
            self.quit()
            return 0
        if args not in ([], ["--preferences"]):
            command_line.printerr("Usage: mactahoe-xfce-widgets [--preferences|--stop]\n")
            return 2
        display = Gdk.Display.get_default()
        if display is None or "x11" not in display.__class__.__name__.lower():
            command_line.printerr("MacTahoe Xfce widgets require an X11 desktop session.\n")
            return 1
        self.activate()
        if args:
            self.show_preferences()
        return 0

    def do_activate(self):
        if self.windows:
            return
        self.metrics = Metrics()
        self.build_windows()
        display = Gdk.Display.get_default()
        display.connect("monitor-added", lambda *_: self.position_windows())
        display.connect("monitor-removed", lambda *_: self.position_windows())
        GLib.timeout_add_seconds(1, self.tick)
        self.tick()

    def build_windows(self):
        clock = DesktopWindow(self, "MacTahoe Clock")
        box = card("TODAY")
        self.date_label = label(style="date")
        self.clock_label = label(style="clock")
        box.pack_start(self.date_label, False, False, 0)
        box.pack_start(self.clock_label, False, False, 0)
        clock.add(box)

        stack = DesktopWindow(self, "MacTahoe Widgets")
        column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        column.set_size_request(300, -1)
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroll.set_propagate_natural_height(True)
        self.scroll.add(column)
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        outer.pack_start(self.scroll, True, True, 0)
        stack.add(outer)
        self.cards = {}
        for key, title in (("weather", "WEATHER"), ("system", "SYSTEM"),
                           ("lunar", "ÂM LỊCH VIỆT NAM"), ("rest", "FOCUS & REST")):
            self.cards[key] = card(title)
            column.pack_start(self.cards[key], False, False, 0)
        self.weather_title = label("Đang tải…", "temperature")
        self.weather_detail = label("", "detail")
        self.cards["weather"].pack_start(self.weather_title, False, False, 0)
        self.cards["weather"].pack_start(self.weather_detail, False, False, 0)
        self.system_label = label("Đang đọc tài nguyên…", "detail")
        self.cards["system"].pack_start(self.system_label, False, False, 0)
        self.lunar_label = label(style="lunar")
        self.lunar_detail = label(style="detail")
        self.cards["lunar"].pack_start(self.lunar_label, False, False, 0)
        self.cards["lunar"].pack_start(self.lunar_detail, False, False, 0)
        self.rest_label = label(style="lunar")
        self.cards["rest"].pack_start(self.rest_label, False, False, 0)
        self.rest_button = Gtk.Button(label="Nghỉ ngay")
        self.rest_button.connect("clicked", self.toggle_rest)
        self.cards["rest"].pack_start(self.rest_button, False, False, 0)
        settings_button = Gtk.Button(label="⚙  Cài đặt widget & dock")
        settings_button.connect("clicked", lambda *_: self.show_preferences())
        outer.pack_start(settings_button, False, False, 0)
        self.windows = [clock, stack]
        for window in self.windows:
            window.show_all()
            window.connect("size-allocate", lambda *_: self.position_windows())
        self.apply_visibility()
        self.position_windows()

    def apply_visibility(self):
        self.windows[0].set_visible(self.settings["show_clock"])
        for key, widget in self.cards.items():
            widget.set_visible(self.settings[f"show_{key}"])

    def position_windows(self):
        if not self.windows:
            return
        display = Gdk.Display.get_default()
        count = display.get_n_monitors()
        if not count:
            return
        monitor = display.get_monitor(min(self.settings["monitor"], count - 1))
        area = monitor.get_workarea()
        for window in self.windows:
            context = window.get_style_context()
            if area.height < 850 and not context.has_class("compact"):
                context.add_class("compact")
            elif area.height >= 850 and context.has_class("compact"):
                context.remove_class("compact")
        self.scroll.set_max_content_height(max(180, area.height - self.settings["stack_y"] - 125))
        for window, side in zip(self.windows, ("clock", "stack")):
            width, height = window.get_size()
            x = self.settings[f"{side}_x"] if side == "clock" else area.width - width - self.settings["stack_x"]
            x = max(0, min(x, max(0, area.width - width)))
            y = max(0, min(self.settings[f"{side}_y"], max(0, area.height - height)))
            window.move(area.x + x, area.y + y)

    def toggle_rest(self, *_):
        if self.rest.on_break:
            self.rest.reset()
        else:
            self.rest.start_break()

    def tick(self):
        now = dt.datetime.now()
        self.date_label.set_text(now.strftime("%A, %d %B"))
        self.clock_label.set_text(now.strftime("%H:%M"))
        lunar = convert_solar_to_lunar(now.date())
        self.lunar_label.set_text(f"{lunar.day:02d} / {lunar.month:02d}" + (" · Nhuận" if lunar.leap else ""))
        self.lunar_detail.set_text(f"Năm {lunar.year_name}\n{lunar.day_name}\n{now:%d/%m/%Y} dương lịch · UTC+7")
        if self.settings["show_rest"]:
            seconds, event = self.rest.tick(self.settings["rest_minutes"], self.settings["break_minutes"])
            self.rest_label.set_text(f"{'Nghỉ ngơi' if self.rest.on_break else 'Tập trung'}  {seconds // 60:02d}:{seconds % 60:02d}")
            self.rest_button.set_label("Tiếp tục làm việc" if self.rest.on_break else "Nghỉ ngay")
            if event:
                notification = Gio.Notification.new("Đến giờ nghỉ" if event == "break" else "Hết giờ nghỉ")
                notification.set_body("Đứng dậy, thư giãn mắt và uống nước." if event == "break" else "Sẵn sàng cho một phiên tập trung mới.")
                self.send_notification("rest", notification)
        if self.settings["show_system"] and not self.metric_busy:
            self.metric_busy = True
            threading.Thread(target=self.read_metrics, daemon=True).start()
        if self.settings["show_weather"] and not self.weather_busy and time.monotonic() >= self.weather_due:
            self.weather_busy = True
            threading.Thread(target=self.read_weather,
                             args=(self.settings.copy(), self.weather_generation), daemon=True).start()
        return True

    def read_metrics(self):
        try:
            data = self.metrics.sample()
            text = (f"{data['cpu_name']}\nCPU  {data['cpu']:.0f}%    RAM  {data['ram']:.0f}%\n"
                    f"{data['ram_used']:.1f} / {data['ram_total']:.1f} GB RAM\n"
                    f"Ổ đĩa  {data['disk']:.0f}% · Trống {data['disk_free']:.0f} GB\n"
                    f"↓ {data['down']:.0f} KB/s    ↑ {data['up']:.0f} KB/s")
            if data["gpu"]:
                text += "\n" + data["gpu"]
        except (OSError, ValueError) as error:
            text = f"Không đọc được tài nguyên: {type(error).__name__}"
        GLib.idle_add(self.finish_metrics, text)

    def finish_metrics(self, text):
        self.system_label.set_text(text)
        self.metric_busy = False
        return False

    def read_weather(self, settings, generation):
        try:
            data = fetch_weather(settings)
            title = f"{data['temp']:.0f}°  {data['city']}"
            detail = (f"{data['description']}\nĐộ ẩm {data['humidity']}% · Gió {data['wind']:.0f} km/h\n"
                      f"{data['source']} · {dt.datetime.now():%H:%M}")
        except Exception:
            # Do not display exception URLs: OpenWeather URLs contain the user's key.
            title, detail = "Thời tiết ngoại tuyến", "Kiểm tra mạng, thành phố hoặc API key."
        GLib.idle_add(self.finish_weather, generation, title, detail)

    def finish_weather(self, generation, title, detail):
        self.weather_busy = False
        if generation == self.weather_generation:
            self.weather_title.set_text(title)
            self.weather_detail.set_text(detail)
            self.weather_due = time.monotonic() + self.settings["weather_interval"] * 60
        return False

    def show_preferences(self):
        if self.preferences:
            self.preferences.present()
            return
        dialog = Gtk.Dialog(title="MacTahoe · Widget & Dock", application=self)
        dialog.set_default_size(470, 640)
        dialog.add_buttons("Đóng", Gtk.ResponseType.CANCEL, "Áp dụng", Gtk.ResponseType.APPLY)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        dialog.get_content_area().pack_start(scroll, True, True, 0)
        grid = Gtk.Grid(column_spacing=18, row_spacing=12, margin=20)
        scroll.add(grid)
        controls = {}
        fields = [
            ("show_clock", "Đồng hồ"), ("show_weather", "Thời tiết"),
            ("show_system", "Tài nguyên hệ thống"), ("show_lunar", "Âm lịch"),
            ("show_rest", "Nhắc nghỉ"), ("city", "Thành phố (trống = tọa độ)"),
            ("latitude", "Vĩ độ"), ("longitude", "Kinh độ"),
            ("weather_api_key", "OpenWeather key (tùy chọn)"),
            ("weather_interval", "Cập nhật thời tiết (phút)"),
            ("rest_minutes", "Tập trung (phút)"), ("break_minutes", "Nghỉ (phút)"),
            ("monitor", "Màn hình (đánh số từ 0)"),
            ("clock_x", "Đồng hồ · lề trái"), ("clock_y", "Đồng hồ · lề trên"),
            ("stack_x", "Cụm widget · lề phải"), ("stack_y", "Cụm widget · lề trên"),
        ]
        for row, (key, title) in enumerate(fields):
            value = self.settings[key]
            grid.attach(label(title), 0, row, 1, 1)
            if isinstance(value, bool):
                control = Gtk.Switch(active=value, halign=Gtk.Align.END)
            elif isinstance(value, str):
                control = Gtk.Entry(text=value)
                control.set_visibility(key != "weather_api_key")
            else:
                low, high = {"latitude": (-90, 90), "longitude": (-180, 180),
                             "weather_interval": (5, 120), "rest_minutes": (1, 180),
                             "break_minutes": (1, 60), "monitor": (0, 32)}.get(key, (0, 4096))
                control = Gtk.SpinButton.new_with_range(low, high, 0.01 if isinstance(value, float) else 1)
                control.set_digits(4 if isinstance(value, float) else 0)
                control.set_value(value)
            controls[key] = control
            grid.attach(control, 1, row, 1, 1)
        dock = Gtk.Button(label="Cài đặt Dock · kích thước, tự ẩn, vị trí")
        dock.connect("clicked", lambda *_: subprocess.Popen(["plank", "--name=mactahoe", "--preferences"]))
        grid.attach(dock, 0, len(fields), 2, 1)
        credit = label("Thời tiết: Open-Meteo (mặc định), OpenWeather (có key).\nÂm lịch dùng múi giờ Việt Nam UTC+7.", "detail")
        grid.attach(credit, 0, len(fields) + 1, 2, 1)

        def response(_, response_id):
            if response_id == Gtk.ResponseType.APPLY:
                new = {}
                for key, control in controls.items():
                    old = self.settings[key]
                    if isinstance(old, bool):
                        new[key] = control.get_active()
                    elif isinstance(old, str):
                        new[key] = control.get_text()
                    else:
                        new[key] = type(old)(control.get_value())
                try:
                    save_settings(new)
                except OSError as error:
                    warning = Gtk.MessageDialog(transient_for=dialog, modal=True,
                        message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.CLOSE,
                        text="Không lưu được cài đặt")
                    warning.format_secondary_text(str(error))
                    warning.run()
                    warning.destroy()
                    return
                self.settings = load_settings()
                self.weather_generation += 1
                self.weather_due = 0
                self.rest.reset()
                self.apply_visibility()
                self.position_windows()
            else:
                dialog.destroy()
        dialog.connect("response", response)
        dialog.connect("destroy", lambda *_: setattr(self, "preferences", None))
        self.preferences = dialog
        dialog.show_all()
        dialog.present()


if __name__ == "__main__":
    raise SystemExit(Widgets().run(sys.argv))
