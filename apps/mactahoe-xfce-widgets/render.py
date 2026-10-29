"""Cairo rendering of the bundled GNOME Tahoe widget design for GTK3/X11."""
import datetime as dt
import math

import cairo
from gi.repository import Gtk, Pango, PangoCairo

WHITE = (0.96, 0.98, 1, 1)
SUB = (0.76, 0.82, 0.93, 1)
MUTED = (0.53, 0.61, 0.76, 1)
GOLD = (1, 0.85, 0.25, 1)


def text(cr, x, y, value, size=12, color=WHITE, bold=False, width=None):
    layout = PangoCairo.create_layout(cr)
    font = Pango.FontDescription.from_string('SF Pro Display ' + ('Bold' if bold else 'Regular'))
    font.set_absolute_size(size * Pango.SCALE)
    layout.set_font_description(font)
    layout.set_text(str(value), -1)
    if width:
        layout.set_width(int(width * Pango.SCALE))
        layout.set_ellipsize(Pango.EllipsizeMode.END)
    cr.move_to(x, y)
    cr.set_source_rgba(*color)
    PangoCairo.show_layout(cr, layout)


def rounded(cr, x, y, w, h, radius):
    cr.new_sub_path()
    for cx, cy, start in ((x+w-radius, y+radius, -90), (x+w-radius, y+h-radius, 0),
                          (x+radius, y+h-radius, 90), (x+radius, y+radius, 180)):
        cr.arc(cx, cy, radius, math.radians(start), math.radians(start+90))
    cr.close_path()


def background(cr, w, h, top, bottom):
    rounded(cr, .5, .5, w-1, h-1, 25)
    gradient = cairo.LinearGradient(0, 0, w*.3, h)
    gradient.add_color_stop_rgba(0, *top)
    gradient.add_color_stop_rgba(1, *bottom)
    cr.set_source(gradient)
    cr.fill_preserve()
    cr.set_source_rgba(1, 1, 1, .17)
    cr.set_line_width(1)
    cr.stroke()


def bar(cr, y, fraction, color, x=22, width=296):
    rounded(cr, x, y, width, 6, 3)
    cr.set_source_rgba(1, 1, 1, .16)
    cr.fill()
    fill = max(0, min(1, fraction)) * width
    if fill > 0:
        rounded(cr, x, y, max(6, fill), 6, 3)
        cr.set_source_rgba(*color)
        cr.fill()


def weather_symbol(cr, condition, night):
    cr.save()
    cr.translate(263, 65)
    cr.set_source_rgba(1, 1, 1, .07)
    cr.arc(0, 0, 51, 0, math.tau)
    cr.fill()
    if condition is None:
        text(cr, -22, -33, '…', 50, SUB)
        cr.restore()
        return
    cloudy = condition not in ('clear',)
    if night:
        cr.set_source_rgba(.94, .95, 1, 1)
        cr.arc(-5, -6, 27, 0, math.tau)
        cr.arc(7, -15, 25, 0, math.tau)
        cr.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
        cr.fill()
        cr.set_fill_rule(cairo.FILL_RULE_WINDING)
    else:
        cr.set_source_rgba(1, .86, .12, 1)
        cr.arc(-4, -8, 26, 0, math.tau)
        cr.fill()
        cr.set_line_width(5)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        for i in range(8):
            a = i*math.tau/8
            cr.move_to(-4+34*math.cos(a), -8+34*math.sin(a))
            cr.line_to(-4+40*math.cos(a), -8+40*math.sin(a))
        cr.stroke()
    if cloudy:
        cr.set_source_rgba(.94, .97, 1, 1)
        for x, y, radius in ((-16, 17, 17), (4, 8, 23), (24, 20, 16)):
            cr.arc(x, y, radius, 0, math.tau)
            cr.fill()
        cr.rectangle(-16, 14, 40, 21)
        cr.fill()
    if condition in ('rain', 'storm', 'snow'):
        cr.set_source_rgba(.65, .85, 1, 1)
        cr.set_line_width(3)
        for x in (-14, 4, 22):
            cr.move_to(x, 42)
            cr.line_to(x-3, 49)
        cr.stroke()
    cr.restore()


class WidgetCanvas(Gtk.DrawingArea):
    HEIGHTS = {'clock': 260, 'weather': 210, 'system': 290, 'lunar': 150, 'rest': 165}

    def __init__(self, owner, kind):
        super().__init__()
        self.owner, self.kind = owner, kind
        self.set_size_request(760 if kind == 'clock' else 340, self.HEIGHTS[kind])
        self.connect('draw', self.paint)

    def paint(self, widget, cr):
        width, height = self.get_allocated_width(), self.get_allocated_height()
        cr.save()
        if self.kind == 'clock':
            self.clock(cr, width, height)
        else:
            cr.scale(width/340, height/self.HEIGHTS[self.kind])
            getattr(self, self.kind)(cr)
        cr.restore()
        return False

    def clock(self, cr, width, height):
        layout = PangoCairo.create_layout(cr)
        font = Pango.FontDescription.from_string('SF Pro Rounded Semibold')
        font.set_absolute_size(min(200, width/3.15, height*.85)*Pango.SCALE)
        layout.set_font_description(font)
        layout.set_text(dt.datetime.now().strftime('%H:%M'), -1)
        cr.move_to(8, 5)
        PangoCairo.layout_path(cr, layout)
        cr.set_source_rgba(.95, .98, 1, .12)
        cr.fill_preserve()
        cr.set_source_rgba(1, 1, 1, .76)
        cr.set_line_width(1.2)
        cr.stroke()

    def weather(self, cr):
        background(cr, 340, 210, (.10, .30, .62, .96), (.34, .63, .96, .94))
        data = self.owner.weather_data
        now = dt.datetime.now()
        text(cr, 22, 20, data.get('city', self.owner.settings['city'] or 'Thời tiết'), 14, bold=True, width=190)
        text(cr, 22, 43, now.strftime('%d/%m/%Y'), 9, SUB)
        text(cr, 22, 66, f"{data['temp']:.0f}°" if 'temp' in data else '--°', 52, bold=True)
        text(cr, 22, 128, data.get('description', self.owner.weather_status), 12, SUB, width=290)
        hi, lo = data.get('high'), data.get('low')
        high = f'{hi:.0f}' if hi is not None else '--'
        low = f'{lo:.0f}' if lo is not None else '--'
        text(cr, 22, 152, f'H:{high}°    L:{low}°', 10, SUB)
        if data:
            text(cr, 22, 177, f"Độ ẩm {data['humidity']}%  ·  Gió {data['wind']:.0f} km/h", 9, SUB)
        else:
            text(cr, 22, 177, 'Bấm để thử kết nối lại', 9, SUB)
        weather_symbol(cr, data.get('condition'), data.get('night', False))

    def system(self, cr):
        background(cr, 340, 290, (.19, .20, .24, .92), (.045, .055, .08, .96))
        text(cr, 22, 20, 'Hệ thống', 14, bold=True)
        d = self.owner.metric_data
        if not d:
            text(cr, 22, 65, self.owner.metric_status, 11, SUB, width=296)
            return
        uptime = d.get('uptime', 0)
        text(cr, 244, 24, f'{int(uptime//3600)}h {int(uptime%3600//60):02d}m', 9, MUTED)
        rows = [('CPU', d['cpu'], d['cpu_name'], (.14, .67, 1, 1)),
                ('GPU', d.get('gpu_percent'), d['gpu'], (.15, .85, .4, 1)),
                ('RAM', d['ram'], f"{d['ram_used']:.1f} / {d['ram_total']:.1f} GiB", (.69, .36, 1, 1)),
                ('SSD', d['disk'], f"Còn trống {d['disk_free']:.1f} GiB", (1, .62, .05, 1))]
        y = 52
        for name, value, detail, color in rows:
            if value is None:
                continue
            text(cr, 22, y, name, 10, color, True)
            text(cr, 274, y, f'{value:.0f}%', 10, WHITE, True)
            bar(cr, y+20, value/100, color)
            text(cr, 22, y+29, detail, 8, MUTED, width=296)
            y += 43
        # Network stays at the bottom, leaving GPU space empty when telemetry is absent.
        cr.set_source_rgba(1, 1, 1, .08)
        cr.rectangle(22, 231, 296, 1)
        cr.fill()
        text(cr, 22, 244, 'Mạng', 10, (.2, .8, 1, 1))
        text(cr, 130, 244, f"↓ {d['down']:.0f} KB/s   ↑ {d['up']:.0f} KB/s", 10, width=188)
        text(cr, 22, 266, 'Theo dõi tài nguyên trực tiếp', 8, MUTED)

    def lunar(self, cr):
        background(cr, 340, 150, (.25, .20, .37, .95), (.075, .065, .12, .97))
        cr.set_source_rgba(1, .88, .4, .10)
        cr.arc(308, 37, 28, .6, 5.2)
        cr.arc(321, 25, 27, 4.7, 1.7)
        cr.fill()
        text(cr, 22, 18, 'Âm lịch', 14, bold=True)
        text(cr, 275, 24, 'Hôm nay', 9, MUTED)
        lunar = self.owner.lunar_data
        if not lunar:
            return
        text(cr, 22, 45, str(lunar.day), 44, GOLD, True)
        text(cr, 94, 52, f"Tháng {lunar.month}{' nhuận' if lunar.leap else ''} · {lunar.year_name}", 13, bold=True, width=222)
        text(cr, 94, 75, lunar.day_name, 9, SUB)
        cr.set_source_rgba(1, 1, 1, .1)
        cr.rectangle(22, 99, 296, 1)
        cr.fill()
        now = dt.datetime.now(dt.timezone(dt.timedelta(hours=7)))
        text(cr, 22, 114, 'Dương lịch', 9, MUTED)
        text(cr, 94, 114, now.strftime('%d/%m/%Y') + ' · UTC+7', 10, SUB)

    def rest(self, cr):
        on_break = self.owner.rest.on_break
        background(cr, 340, 165, (.12, .35, .29, .94) if on_break else (.35, .29, .12, .95), (.07, .12, .12, .97))
        color = (.35, .92, .65, 1) if on_break else GOLD
        cr.set_source_rgba(1, 1, 1, .1)
        cr.set_line_width(6)
        cr.arc(298, 43, 28, 0, math.tau)
        cr.stroke()
        cr.move_to(298, 26)
        cr.line_to(298, 43)
        cr.line_to(311, 51)
        cr.stroke()
        text(cr, 22, 18, 'Nhắc nghỉ', 14, bold=True)
        seconds = self.owner.rest_remaining
        text(cr, 22, 47, f'{seconds//60:02d}:{seconds%60:02d}', 29, color, True)
        text(cr, 22, 84, 'Đang nghỉ ngơi' if on_break else 'Phiên tập trung', 9, SUB)
        duration = self.owner.settings['break_minutes' if on_break else 'rest_minutes']*60
        bar(cr, 106, 1-seconds/max(1, duration), color)
        text(cr, 22, 123, 'Bấm để tiếp tục làm việc' if on_break else 'Bấm để nghỉ ngay', 10, bold=True)
        text(cr, 22, 144, 'Đổi tư thế, chớp mắt và nhìn xa.', 8, SUB)
