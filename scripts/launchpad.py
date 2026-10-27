#!/usr/bin/env python3
"""Fullscreen Tahoe application grid, independent of Xfce's Apple/Whisker menu."""
import math
from pathlib import Path
import subprocess
import sys
import threading
import unicodedata

import gi
gi.require_foreign('cairo')
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk, Pango


def searchable(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value.casefold().replace('đ', 'd'))
                   if not unicodedata.combining(c))


class Launchpad(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='io.github.adfoxtheme.XfceLaunchpad',
                         flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.window = None
        self.page = 0
        self.apps = []
        self.matches = []
        self.columns, self.rows = 7, 3
        self.wallpaper = None
        self.search_source = None
        self.background_generation = 0

    def do_startup(self):
        Gtk.Application.do_startup(self)
        css = Gtk.CssProvider()
        css.load_from_path(str(Path(__file__).with_name('launchpad.css')))
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css,
                                                 Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.app_monitor = Gio.AppInfoMonitor.get()
        self.app_monitor.connect('changed', self.apps_changed)

    def do_command_line(self, command_line):
        args = command_line.get_arguments()[1:]
        if args == ['--stop']:
            self.quit()
            return 0
        if args not in ([], ['--center']):
            command_line.printerr_literal('Usage: mactahoe-xfce-menu [--center|--stop]\n')
            return 2
        self.activate()
        return 0

    def do_activate(self):
        if self.window and self.window.get_visible():
            self.window.hide()
            return
        if not self.window:
            self.build()
        self.load_apps()
        self.search.set_text('')
        self.page = 0
        display = Gdk.Display.get_default()
        _, x, y = display.get_default_seat().get_pointer().get_position()
        monitor = display.get_monitor_at_point(x, y)
        area = monitor.get_geometry()
        self.columns = max(3, min(10, (area.width-100)//140))
        self.rows = max(2, min(5, (area.height-240)//140))
        self.tile_width = max(90, min(132, (area.width-80)//self.columns))
        self.tile_height = max(90, min(138, (area.height-230)//self.rows))
        self.window.move(area.x, area.y)
        self.window.set_default_size(area.width, area.height)
        index = next((i for i in range(display.get_n_monitors())
                      if display.get_monitor(i) == monitor), 0)
        self.window.fullscreen_on_monitor(self.window.get_screen(), index)
        self.window.show_all()
        self.filter_apps()
        self.window.present()
        self.search.grab_focus()
        self.background_generation += 1
        threading.Thread(target=self.prepare_background,
                         args=(area.width, area.height, self.background_generation), daemon=True).start()

    def build(self):
        self.window = Gtk.ApplicationWindow(application=self, title='Launchpad')
        self.window.set_decorated(False)
        self.window.set_skip_taskbar_hint(True)
        self.window.get_style_context().add_class('tahoe-launchpad')
        self.window.connect('delete-event', lambda *_: self.dismiss())
        self.window.connect('key-press-event', self.key_pressed)
        self.window.add_events(Gdk.EventMask.SCROLL_MASK)
        self.window.connect('scroll-event', self.scrolled)
        overlay = Gtk.Overlay()
        self.window.add(overlay)
        backdrop = Gtk.EventBox()
        self.backdrop = Gtk.DrawingArea()
        self.backdrop.connect('draw', self.paint_background)
        backdrop.add(self.backdrop)
        backdrop.connect('button-press-event', lambda *_: self.dismiss())
        overlay.add(backdrop)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=22,
                          halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        overlay.add_overlay(content)
        search_row = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER)
        self.search = Gtk.SearchEntry(placeholder_text='Tìm kiếm ứng dụng')
        self.search.set_size_request(340, 38)
        self.search.connect('changed', self.schedule_filter)
        self.search.connect('activate', self.launch_first)
        search_row.pack_start(self.search, False, False, 0)
        close = Gtk.Button.new_from_icon_name('window-close-symbolic', Gtk.IconSize.BUTTON)
        close.set_tooltip_text('Đóng Launchpad (Esc)')
        close.connect('clicked', lambda *_: self.dismiss())
        search_row.pack_start(close, False, False, 0)
        content.pack_start(search_row, False, False, 0)
        self.grid = Gtk.Grid(column_homogeneous=True, row_homogeneous=True,
                             halign=Gtk.Align.CENTER)
        content.pack_start(self.grid, False, False, 0)
        self.status = Gtk.Label()
        self.status.get_style_context().add_class('launchpad-status')
        content.pack_start(self.status, False, False, 0)
        self.pager = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER)
        content.pack_start(self.pager, False, False, 0)
        self.hint = Gtk.Label(label='Vuốt cuộn để chuyển trang  ·  Esc để về desktop')
        self.hint.get_style_context().add_class('launchpad-hint')
        content.pack_start(self.hint, False, False, 0)

    def dismiss(self):
        self.window.hide()
        return True

    def apps_changed(self, *_):
        if self.window and self.window.get_visible():
            self.load_apps()
            self.filter_apps()

    def load_apps(self):
        # Gio honors desktop-file overrides, Hidden/NoDisplay, OnlyShowIn and TryExec.
        self.apps = sorted((app for app in Gio.AppInfo.get_all() if app.should_show()),
                           key=lambda app: searchable(app.get_display_name()))

    def schedule_filter(self, *_):
        if self.search_source:
            GLib.source_remove(self.search_source)
        self.search_source = GLib.timeout_add(100, self.filter_apps)

    def filter_apps(self):
        self.search_source = None
        query = searchable(self.search.get_text().strip()).split()
        self.matches = []
        for app in self.apps:
            haystack = searchable(' '.join((app.get_display_name(), app.get_description() or '',
                                             app.get_executable() or '')))
            if all(word in haystack for word in query):
                self.matches.append(app)
        self.page = 0
        self.render_page()
        return False

    def render_page(self):
        for child in self.grid.get_children():
            self.grid.remove(child)
        size = self.columns*self.rows
        pages = max(1, math.ceil(len(self.matches)/size))
        self.page = max(0, min(self.page, pages-1))
        self.grid.set_size_request(self.columns*self.tile_width, self.rows*self.tile_height)
        for index, app in enumerate(self.matches[self.page*size:(self.page+1)*size]):
            tile = Gtk.Button()
            tile.set_relief(Gtk.ReliefStyle.NONE)
            tile.set_size_request(self.tile_width, self.tile_height)
            tile.get_style_context().add_class('launchpad-tile')
            tile.set_tooltip_text(app.get_display_name())
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10,
                          halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
            icon = Gtk.Image.new_from_gicon(app.get_icon() or Gio.ThemedIcon.new('application-x-executable'),
                                            Gtk.IconSize.DIALOG)
            icon.set_pixel_size(64 if self.tile_height >= 120 else 52)
            box.pack_start(icon, False, False, 0)
            name = Gtk.Label(label=app.get_display_name())
            name.set_ellipsize(Pango.EllipsizeMode.END)
            name.set_max_width_chars(16)
            name.set_width_chars(12)
            box.pack_start(name, False, False, 0)
            tile.add(box)
            tile.connect('clicked', lambda _, selected=app: self.launch(selected))
            self.grid.attach(tile, index % self.columns, index//self.columns, 1, 1)
        for child in self.pager.get_children():
            self.pager.remove(child)
        # Numbered page buttons remain usable even with Kali's large app catalog.
        if pages > 1:
            previous = Gtk.Button.new_from_icon_name('go-previous-symbolic', Gtk.IconSize.MENU)
            previous.connect('clicked', lambda *_: self.change_page(-1))
            self.pager.pack_start(previous, False, False, 0)
            for page in range(max(0, self.page-3), min(pages, self.page+4)):
                dot = Gtk.Button(label='●' if page == self.page else '○')
                dot.set_tooltip_text(f'Trang {page+1} / {pages}')
                dot.get_style_context().add_class('page-dot')
                dot.connect('clicked', lambda _, number=page: self.go_page(number))
                self.pager.pack_start(dot, False, False, 0)
            next_button = Gtk.Button.new_from_icon_name('go-next-symbolic', Gtk.IconSize.MENU)
            next_button.connect('clicked', lambda *_: self.change_page(1))
            self.pager.pack_start(next_button, False, False, 0)
        self.status.set_text('Không tìm thấy ứng dụng' if not self.matches else '')
        self.grid.show_all()
        self.pager.show_all()

    def go_page(self, number):
        self.page = number
        self.render_page()

    def change_page(self, step):
        self.go_page(self.page+step)

    def scrolled(self, _, event):
        if self.search.has_focus() and self.search.get_text():
            return False
        if event.direction in (Gdk.ScrollDirection.DOWN, Gdk.ScrollDirection.RIGHT):
            self.change_page(1)
        elif event.direction in (Gdk.ScrollDirection.UP, Gdk.ScrollDirection.LEFT):
            self.change_page(-1)
        else:
            return False
        return True

    def key_pressed(self, _, event):
        if event.keyval == Gdk.KEY_Escape:
            return self.dismiss()
        if event.keyval in (Gdk.KEY_Page_Down, Gdk.KEY_Page_Up):
            self.change_page(1 if event.keyval == Gdk.KEY_Page_Down else -1)
            return True
        # Arrow keys and Tab retain native GTK focus navigation between app tiles.
        if not self.search.has_focus() and not (event.state & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.MOD1_MASK)):
            char = Gdk.keyval_to_unicode(event.keyval)
            if char and chr(char).isprintable() and not chr(char).isspace():
                self.search.grab_focus()
                self.search.set_text(self.search.get_text()+chr(char))
                self.search.set_position(-1)
                return True
        return False

    def launch_first(self, *_):
        if self.search_source:
            GLib.source_remove(self.search_source)
            self.search_source = None
            self.filter_apps()
        if self.matches:
            self.launch(self.matches[self.page*self.columns*self.rows])

    def launch(self, app):
        try:
            context = Gdk.Display.get_default().get_app_launch_context()
            context.set_timestamp(Gtk.get_current_event_time())
            if app.launch([], context):
                self.dismiss()
        except GLib.Error:
            self.status.set_text('Không mở được ứng dụng. Hãy kiểm tra ứng dụng đã được cài đặt.')

    def prepare_background(self, width, height, generation):
        # Blur the configured wallpaper, never a screenshot containing open windows.
        try:
            from PIL import Image, ImageFilter, ImageOps
            properties = subprocess.check_output(['xfconf-query', '-c', 'xfce4-desktop', '-l'],
                                                  text=True, timeout=3).splitlines()
            paths = []
            for prop in properties:
                if prop.endswith('/last-image'):
                    value = subprocess.check_output(['xfconf-query', '-c', 'xfce4-desktop', '-p', prop],
                                                     text=True, timeout=3).strip()
                    if Path(value).is_file():
                        paths.append(value)
            if not paths:
                return
            with Image.open(paths[0]) as source:
                image = ImageOps.fit(source.convert('RGB'), (max(1, width//3), max(1, height//3)))
                image = image.filter(ImageFilter.GaussianBlur(10))
                raw = image.tobytes()
                w, h = image.size
            GLib.idle_add(self.finish_background, raw, w, h, generation)
        except (OSError, ValueError, subprocess.SubprocessError):
            pass

    def finish_background(self, raw, width, height, generation):
        if generation == self.background_generation:
            self.wallpaper = GdkPixbuf.Pixbuf.new_from_bytes(GLib.Bytes.new(raw),
                GdkPixbuf.Colorspace.RGB, False, 8, width, height, width*3)
            self.backdrop.queue_draw()
        return False

    def paint_background(self, widget, cr):
        width, height = widget.get_allocated_width(), widget.get_allocated_height()
        cr.set_source_rgb(.08, .1, .16)
        cr.paint()
        if self.wallpaper:
            cr.save()
            cr.scale(width/self.wallpaper.get_width(), height/self.wallpaper.get_height())
            Gdk.cairo_set_source_pixbuf(cr, self.wallpaper, 0, 0)
            cr.paint()
            cr.restore()
        cr.set_source_rgba(.03, .04, .08, .36)
        cr.paint()
        return False


if __name__ == '__main__':
    raise SystemExit(Launchpad().run(sys.argv))
