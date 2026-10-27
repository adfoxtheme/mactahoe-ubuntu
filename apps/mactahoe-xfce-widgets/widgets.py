#!/usr/bin/env python3
"""Tahoe desktop widgets for Xfce/X11. One process per user D-Bus session."""
import datetime as dt
from pathlib import Path
import subprocess
import sys
import threading
import time

import gi
gi.require_foreign('cairo')
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gio, GLib, Gtk

from model import Metrics, RestTimer, fetch_weather, load_settings, save_settings
from render import WidgetCanvas

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
        self.weather_data = {}
        self.weather_status = 'Đang kết nối…'
        self.metric_data = {}
        self.metric_status = 'Đang đọc tài nguyên…'
        self.lunar_data = None
        self.rest_remaining = self.settings['rest_minutes'] * 60

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
        if args == ["--status"]:
            running = bool(self.windows)
            command_line.print_literal("MacTahoe widgets: " + ("running" if running else "not running") + "\n")
            return 0 if running else 1
        if args not in ([], ["--preferences"], ["--enable-all"]):
            command_line.printerr_literal("Usage: mactahoe-xfce-widgets [--preferences|--enable-all|--status|--stop]\n")
            return 2
        display = Gdk.Display.get_default()
        if display is None or "x11" not in display.__class__.__name__.lower():
            command_line.printerr_literal("MacTahoe Xfce widgets require an X11 desktop session.\n")
            return 1
        if args == ["--enable-all"]:
            self.settings = load_settings()
            for key in self.settings:
                if key.startswith("show_"):
                    self.settings[key] = True
            try:
                save_settings(self.settings)
            except OSError as error:
                command_line.printerr_literal(f"Cannot save widget settings: {error}\n")
                return 1
        self.activate()
        if args == ["--enable-all"]:
            self.apply_visibility()
            self.weather_due = 0
            command_line.print_literal("All MacTahoe desktop widgets are enabled.\n")
        if args == ["--preferences"]:
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
        clock = DesktopWindow(self, 'MacTahoe Clock')
        self.clock_canvas = WidgetCanvas(self, 'clock')
        clock.add(self.interactive(self.clock_canvas, 'clock'))
        stack = DesktopWindow(self, 'MacTahoe Widgets')
        self.column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroll.set_propagate_natural_height(True)
        self.scroll.add(self.column)
        stack.add(self.scroll)
        self.cards, self.canvases = {}, {}
        for key in ('weather', 'system', 'lunar', 'rest'):
            canvas = WidgetCanvas(self, key)
            self.canvases[key] = canvas
            self.cards[key] = self.interactive(canvas, key)
            self.column.pack_start(self.cards[key], False, False, 0)
        self.windows = [clock, stack]
        for window in self.windows:
            window.show_all()
            window.connect('size-allocate', lambda *_: self.position_windows())
        self.apply_visibility()
        self.position_windows()

    def interactive(self, child, kind):
        event_box = Gtk.EventBox()
        event_box.set_visible_window(False)
        event_box.add(child)
        event_box.set_tooltip_text('Chuột phải để chỉnh sửa widget và dock')

        def pressed(_, event):
            if event.button == 3:
                menu = Gtk.Menu()
                item = Gtk.MenuItem(label='Chỉnh sửa widget & dock…')
                item.connect('activate', lambda *_: self.show_preferences())
                menu.append(item)
                if kind != 'clock':
                    hide = Gtk.MenuItem(label='Ẩn widget này')
                    hide.connect('activate', lambda *_: self.hide_widget(kind))
                    menu.append(hide)
                menu.show_all()
                menu.popup_at_pointer(event)
                self.context_menu = menu
                return True
            if event.button == 1:
                if kind == 'weather':
                    self.weather_due = 0
                    self.tick()
                elif kind == 'rest':
                    self.toggle_rest()
                elif kind == 'lunar':
                    subprocess.Popen([str(Path.home()/'.local/bin/am-lich-viet-nam')])
                return True
            return False
        event_box.connect('button-press-event', pressed)
        return event_box

    def hide_widget(self, kind):
        updated = dict(self.settings, **{f'show_{kind}': False})
        try:
            save_settings(updated)
        except OSError:
            return
        self.settings = updated
        self.apply_visibility()

    def apply_visibility(self):
        self.windows[0].set_visible(self.settings['show_clock'])
        for key, widget in self.cards.items():
            widget.set_visible(self.settings[f'show_{key}'])
        self.windows[1].set_visible(any(self.settings[f'show_{key}'] for key in self.cards))
        self.position_windows()

    def position_windows(self):
        if not self.windows:
            return
        display = Gdk.Display.get_default()
        count = display.get_n_monitors()
        if not count:
            return
        monitor = display.get_monitor(min(self.settings['monitor'], count-1))
        area = monitor.get_workarea()
        scale = min(1.0, max(.72, (area.height-self.settings['stack_y']-90)/851))
        width = min(int(340*scale), max(160, area.width-32))
        for kind, canvas in self.canvases.items():
            canvas.set_size_request(width, int(canvas.HEIGHTS[kind]*scale))
        self.column.set_spacing(max(6, int(12*scale)))
        self.scroll.set_max_content_height(max(160, area.height-self.settings['stack_y']-90))
        clock_width = min(760, max(240, area.width-width-self.settings['clock_x']-60))
        self.clock_canvas.set_size_request(clock_width, int(clock_width*260/760))
        for window, side in zip(self.windows, ('clock', 'stack')):
            w, h = window.get_size()
            x = self.settings['clock_x'] if side == 'clock' else area.width-w-self.settings['stack_x']
            y = self.settings[f'{side}_y']
            window.move(area.x+max(0, min(x, max(0, area.width-w))),
                        area.y+max(0, min(y, max(0, area.height-h))))

    def toggle_rest(self, *_):
        if self.rest.on_break:
            self.rest.reset()
        else:
            self.rest.start_break()
        self.tick()

    def tick(self):
        now = dt.datetime.now(dt.timezone(dt.timedelta(hours=7)))
        self.lunar_data = convert_solar_to_lunar(now.date())
        if self.settings['show_rest']:
            self.rest_remaining, event = self.rest.tick(self.settings['rest_minutes'], self.settings['break_minutes'])
            if event:
                notification = Gio.Notification.new('Đến giờ nghỉ' if event == 'break' else 'Hết giờ nghỉ')
                notification.set_body('Đứng dậy, thư giãn mắt và uống nước.' if event == 'break' else 'Sẵn sàng cho một phiên tập trung mới.')
                self.send_notification('rest', notification)
        self.clock_canvas.queue_draw()
        for canvas in self.canvases.values():
            canvas.queue_draw()
        if self.settings['show_system'] and not self.metric_busy:
            self.metric_busy = True
            threading.Thread(target=self.read_metrics, daemon=True).start()
        if self.settings['show_weather'] and not self.weather_busy and time.monotonic() >= self.weather_due:
            self.weather_busy = True
            threading.Thread(target=self.read_weather,
                             args=(self.settings.copy(), self.weather_generation), daemon=True).start()
        return True

    def read_metrics(self):
        try:
            data = self.metrics.sample()
        except (OSError, ValueError):
            data = None
        GLib.idle_add(self.finish_metrics, data)

    def finish_metrics(self, data):
        if data is not None:
            self.metric_data = data
        else:
            self.metric_status = 'Không đọc được tài nguyên hệ thống'
        self.metric_busy = False
        self.canvases['system'].queue_draw()
        return False

    def read_weather(self, settings, generation):
        try:
            data = fetch_weather(settings)
        except Exception:
            # Never expose exception URLs containing the user's API key.
            data = None
        GLib.idle_add(self.finish_weather, generation, data)

    def finish_weather(self, generation, data):
        self.weather_busy = False
        if generation == self.weather_generation:
            if data is not None:
                self.weather_data = data
                self.weather_status = ''
            else:
                self.weather_status = 'Thời tiết ngoại tuyến'
                if self.weather_data:
                    self.weather_data['description'] = 'Ngoại tuyến · dữ liệu lần cập nhật trước'
            self.weather_due = time.monotonic()+self.settings['weather_interval']*60
            self.canvases['weather'].queue_draw()
        return False

    def show_preferences(self):
        if self.preferences:
            self.preferences.present()
            return
        dialog = Gtk.Dialog(title="MacTahoe · Widget & Dock", application=self)
        dialog.set_default_size(470, 640)
        dialog.add_buttons("Đóng", Gtk.ResponseType.CANCEL, "Bật tất cả", 100, "Áp dụng", Gtk.ResponseType.APPLY)
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
            if response_id == 100:
                for key, control in controls.items():
                    if key.startswith("show_"):
                        control.set_active(True)
                response_id = Gtk.ResponseType.APPLY
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
                self.weather_data = {}
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
