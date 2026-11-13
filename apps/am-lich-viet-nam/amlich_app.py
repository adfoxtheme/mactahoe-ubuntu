#!/usr/bin/env python3
"""Vietnamese Lunar Calendar — a lunar calendar for GNOME/GTK4."""

from __future__ import annotations

from calendar import month_name, monthrange
from datetime import date, timedelta
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, Gtk, Pango

from holidays import get_holidays
from lunar import (
    LunarDate,
    can_chi_day,
    convert_solar_to_lunar,
)

APP_ID = "vn.ihoan.AmLich"
WEEKDAY_SHORT = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
WEEKDAYS_EN = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
HOLIDAY_NAMES_EN = {
    "Tết Dương lịch": "New Year's Day",
    "Quốc tế Phụ nữ": "International Women's Day",
    "Ngày Giải phóng miền Nam": "Reunification Day",
    "Quốc tế Lao động": "International Workers' Day",
    "Quốc tế Thiếu nhi": "International Children's Day",
    "Ngày Thương binh - Liệt sĩ": "Remembrance Day",
    "Quốc khánh": "National Day",
    "Ngày Phụ nữ Việt Nam": "Vietnamese Women's Day",
    "Ngày Nhà giáo Việt Nam": "Vietnamese Teachers' Day",
    "Ngày thành lập Quân đội nhân dân Việt Nam": "Vietnam People's Army Day",
    "Tết Nguyên Đán": "Lunar New Year",
    "Rằm tháng Giêng": "First Full Moon Festival",
    "Tết Hàn Thực": "Cold Food Festival",
    "Giỗ Tổ Hùng Vương": "Hung Kings' Commemoration",
    "Tết Đoan Ngọ": "Dragon Boat Festival",
    "Lễ Vu Lan": "Vu Lan Festival",
    "Tết Trung Thu": "Mid-Autumn Festival",
    "Ông Công - Ông Táo": "Kitchen Gods' Day",
    "Đêm Giao thừa": "Lunar New Year's Eve",
}
HOLIDAY_SHORT_EN = {
    "Tết DL": "New Year",
    "Tết": "Lunar New Year",
    "Rằm": "Full Moon",
    "Hàn Thực": "Cold Food",
    "Giỗ Tổ": "Hung Kings",
    "Đoan Ngọ": "Dragon Boat",
    "Vu Lan": "Vu Lan",
    "Trung Thu": "Mid-Autumn",
    "Ông Táo": "Kitchen Gods",
    "Giao thừa": "New Year's Eve",
}
MIN_YEAR = 1800
MAX_YEAR = 2199


def lunar_month_span(first: date, last: date) -> str:
    """Describe the lunar months covered by a Gregorian month."""
    l1 = convert_solar_to_lunar(first)
    l2 = convert_solar_to_lunar(last)

    def month_text(lunar: LunarDate) -> str:
        return f"month {lunar.month}{' (leap)' if lunar.leap else ''}"

    if l1.year == l2.year:
        if l1.month == l2.month and l1.leap == l2.leap:
            return f"{month_text(l1)}, year {l1.year_name}"
        return f"{month_text(l1)} – {l2.month}{' (leap)' if l2.leap else ''}, year {l1.year_name}"
    return (
        f"{month_text(l1)}, year {l1.year_name} – "
        f"{month_text(l2)}, year {l2.year_name}"
    )


def lunar_day_text(lunar: LunarDate) -> str:
    if lunar.day == 1:
        day = "First day"
    elif lunar.day == 15:
        day = "Full moon"
    elif lunar.day == 30:
        day = "Last day"
    else:
        day = f"Day {lunar.day}"
    return f"{day} of lunar month {lunar.month}{' (leap)' if lunar.leap else ''}"


def lunar_tooltip_text(lunar: LunarDate) -> str:
    return f"Lunar day {lunar.day}, month {lunar.month}{' (leap)' if lunar.leap else ''}, year {lunar.year_name}"


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Vietnamese Lunar Calendar")
        self.set_default_size(1120, 780)
        self.set_size_request(920, 640)
        self.set_icon_name(APP_ID)
        self.add_css_class("amlich-window")

        self.today = date.today()
        self.view_year = self.today.year
        self.view_month = self.today.month
        self.selected = self.today
        self._day_buttons: dict[date, Gtk.Widget] = {}

        self._build_ui()
        self._refresh_all()

    # ------------------------------------------------------------------ UI

    def _build_ui(self) -> None:
        header = Adw.HeaderBar()
        header.add_css_class("amlich-header")

        self._prev_button = Gtk.Button(icon_name="go-previous-symbolic")
        self._prev_button.set_tooltip_text("Previous month (←)")
        self._prev_button.connect("clicked", lambda *_: self.go_month(-1))

        self._next_button = Gtk.Button(icon_name="go-next-symbolic")
        self._next_button.set_tooltip_text("Next month (→)")
        self._next_button.connect("clicked", lambda *_: self.go_month(1))

        self._today_button = Gtk.Button(label="Today")
        self._today_button.set_tooltip_text("Go to today (Home)")
        self._today_button.connect("clicked", lambda *_: self.go_today())

        header.pack_start(self._prev_button)
        header.pack_start(self._next_button)
        header.pack_start(self._today_button)

        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        title_box.set_halign(Gtk.Align.CENTER)
        self._month_title = Gtk.Label()
        self._month_title.add_css_class("month-title")
        self._month_subtitle = Gtk.Label()
        self._month_subtitle.add_css_class("month-subtitle")
        title_box.append(self._month_title)
        title_box.append(self._month_subtitle)
        header.set_title_widget(title_box)

        about_button = Gtk.Button(icon_name="help-about-symbolic")
        about_button.set_tooltip_text("About")
        about_button.connect("clicked", self._show_about)
        header.pack_end(about_button)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)

        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        body.append(self._build_calendar_area())
        body.append(self._build_sidebar())
        toolbar.set_content(body)
        self.set_content(toolbar)

    def _build_calendar_area(self) -> Gtk.Widget:
        area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        area.set_margin_top(18)
        area.set_margin_bottom(18)
        area.set_margin_start(20)
        area.set_margin_end(20)
        area.set_hexpand(True)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9)
        card.add_css_class("calendar-card")
        card.set_hexpand(True)
        card.set_vexpand(True)

        weekday_grid = Gtk.Grid()
        weekday_grid.set_column_homogeneous(True)
        weekday_grid.set_column_spacing(6)
        weekday_grid.set_row_spacing(2)
        for column, label in enumerate(WEEKDAY_SHORT):
            widget = Gtk.Label(label=label)
            widget.add_css_class("weekday")
            if column >= 5:
                widget.add_css_class("weekend")
            widget.set_hexpand(True)
            weekday_grid.attach(widget, column, 0, 1, 1)
        card.append(weekday_grid)

        self._days_grid = Gtk.Grid()
        self._days_grid.set_column_homogeneous(True)
        self._days_grid.set_row_homogeneous(True)
        self._days_grid.set_column_spacing(6)
        self._days_grid.set_row_spacing(6)
        self._days_grid.set_hexpand(True)
        self._days_grid.set_vexpand(True)
        card.append(self._days_grid)

        area.append(card)

        note = Gtk.Label(
            label="Select a date to see details  ·  Use ← → to change months",
            xalign=0,
        )
        note.add_css_class("footer-note")
        note.set_margin_start(4)
        area.append(note)
        return area

    def _build_sidebar(self) -> Gtk.Widget:
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sidebar.add_css_class("sidebar")
        sidebar.set_size_request(320, -1)
        sidebar.set_hexpand(False)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_top(20)
        content.set_margin_bottom(20)
        content.set_margin_start(22)
        content.set_margin_end(22)
        content.set_size_request(276, -1)

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        top.set_valign(Gtk.Align.START)
        self._big_day = Gtk.Label()
        self._big_day.add_css_class("big-day")
        self._big_day.set_valign(Gtk.Align.START)
        top.append(self._big_day)

        meta = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        meta.set_valign(Gtk.Align.CENTER)
        meta.set_hexpand(True)
        self._weekday = Gtk.Label(xalign=0)
        self._weekday.add_css_class("sidebar-weekday")
        self._solar_month = Gtk.Label(xalign=0)
        self._solar_month.add_css_class("sidebar-month")
        self._today_pill = Gtk.Label(label="TODAY")
        self._today_pill.add_css_class("today-pill")
        self._today_pill.set_halign(Gtk.Align.START)
        meta.append(self._weekday)
        meta.append(self._solar_month)
        meta.append(self._today_pill)
        top.append(meta)
        content.append(top)

        lunar_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        lunar_card.add_css_class("lunar-card")
        lunar_title = Gtk.Label(label="LUNAR CALENDAR", xalign=0)
        lunar_title.add_css_class("card-title")
        self._lunar_main = Gtk.Label(xalign=0)
        self._lunar_main.add_css_class("lunar-main")
        self._lunar_sub = Gtk.Label(xalign=0)
        self._lunar_sub.add_css_class("lunar-sub")
        self._lunar_sub.set_wrap(True)
        lunar_card.append(lunar_title)
        lunar_card.append(self._lunar_main)
        lunar_card.append(self._lunar_sub)
        content.append(lunar_card)

        canchi_title = Gtk.Label(label="CAN CHI", xalign=0)
        canchi_title.add_css_class("section-title")
        content.append(canchi_title)

        canchi_grid = Gtk.Grid(column_spacing=14, row_spacing=5)
        canchi_grid.set_halign(Gtk.Align.FILL)
        self._canchi_values: dict[str, Gtk.Label] = {}
        for row, (key, label) in enumerate(
            (("year", "Year"), ("month", "Month"), ("day", "Day"))
        ):
            name = Gtk.Label(label=label, xalign=0)
            name.add_css_class("canchi-label")
            value = Gtk.Label(xalign=0)
            value.add_css_class("canchi-value")
            value.set_hexpand(True)
            canchi_grid.attach(name, 0, row, 1, 1)
            canchi_grid.attach(value, 1, row, 1, 1)
            self._canchi_values[key] = value
        content.append(canchi_grid)

        holiday_title = Gtk.Label(label="EVENTS", xalign=0)
        holiday_title.add_css_class("section-title")
        content.append(holiday_title)

        self._holiday_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        content.append(self._holiday_box)

        footer = Gtk.Label(
            label="Vietnam time zone · UTC+7\nHo Ngoc Duc algorithm",
            xalign=0,
        )
        footer.add_css_class("footer-note")
        footer.set_margin_top(4)
        content.append(footer)

        scroll.set_child(content)
        sidebar.append(scroll)
        return sidebar

    # -------------------------------------------------------------- actions

    def go_month(self, delta: int) -> None:
        year, month = self.view_year, self.view_month + delta
        while month < 1:
            month += 12
            year -= 1
        while month > 12:
            month -= 12
            year += 1
        if not MIN_YEAR <= year <= MAX_YEAR:
            return
        self.view_year = year
        self.view_month = month
        self.selected = date(year, month, 1)
        self._refresh_all()

    def go_today(self) -> None:
        self.view_year = self.today.year
        self.view_month = self.today.month
        self.selected = self.today
        self._refresh_all()

    def select_date(self, selected: date) -> None:
        if not MIN_YEAR <= selected.year <= MAX_YEAR:
            return
        if selected.year != self.view_year or selected.month != self.view_month:
            self.view_year = selected.year
            self.view_month = selected.month
            self.selected = selected
            self._refresh_all()
            return

        self.selected = selected
        for day, button in self._day_buttons.items():
            if day == selected:
                button.add_css_class("selected")
            else:
                button.remove_css_class("selected")
        self._update_details()

    # ------------------------------------------------------------- rendering

    def _refresh_all(self) -> None:
        self._refresh_header()
        self._build_month()
        self._update_details()

    def _refresh_header(self) -> None:
        self._month_title.set_text(
            f"{month_name[self.view_month]} {self.view_year}"
        )
        last_day = monthrange(self.view_year, self.view_month)[1]
        first = date(self.view_year, self.view_month, 1)
        last = date(self.view_year, self.view_month, last_day)
        self._month_subtitle.set_text(f"Lunar calendar: {lunar_month_span(first, last)}")

    def _build_month(self) -> None:
        child = self._days_grid.get_first_child()
        while child is not None:
            self._days_grid.remove(child)
            child = self._days_grid.get_first_child()
        self._day_buttons.clear()

        first = date(self.view_year, self.view_month, 1)
        start = first - timedelta(days=first.weekday())

        for index in range(42):
            day = start + timedelta(days=index)
            lunar = convert_solar_to_lunar(day)
            holidays = get_holidays(day, lunar)
            in_month = day.year == self.view_year and day.month == self.view_month
            cell = self._make_day_cell(day, lunar, holidays, in_month)
            self._days_grid.attach(cell, index % 7, index // 7, 1, 1)
            self._day_buttons[day] = cell

    def _make_day_cell(
        self,
        day: date,
        lunar: LunarDate,
        holidays,
        in_month: bool,
    ) -> Gtk.Widget:
        cell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        cell.add_css_class("day-cell")
        cell.set_hexpand(True)
        cell.set_vexpand(True)

        if not in_month:
            cell.add_css_class("outside")
        if day.weekday() >= 5:
            cell.add_css_class("weekend")
        if day == self.today:
            cell.add_css_class("today")
        if day == self.selected:
            cell.add_css_class("selected")

        tooltip = (
            f"{WEEKDAYS_EN[day.weekday()]}, {day.day:02d}/{day.month:02d}/{day.year}"
            f"\n{lunar_tooltip_text(lunar)}"
        )
        if holidays:
            tooltip += "\n" + "\n".join(HOLIDAY_NAMES_EN.get(holiday.name, holiday.name) for holiday in holidays)
        cell.set_tooltip_text(tooltip)

        click = Gtk.GestureClick.new()
        click.set_button(Gdk.BUTTON_PRIMARY)
        click.connect("released", lambda *_: self.select_date(day))
        cell.add_controller(click)

        motion = Gtk.EventControllerMotion.new()
        motion.connect("enter", lambda *_: cell.add_css_class("hover"))
        motion.connect("leave", lambda *_: cell.remove_css_class("hover"))
        cell.add_controller(motion)

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        solar = Gtk.Label(label=str(day.day))
        solar.add_css_class("solar-label")
        solar.set_xalign(0)
        solar.set_hexpand(True)
        lunar_label = Gtk.Label(label=str(lunar.day))
        lunar_label.add_css_class("lunar-label")
        lunar_label.set_xalign(1)
        top.append(solar)
        top.append(lunar_label)
        cell.append(top)

        holiday_label = Gtk.Label(
            label=HOLIDAY_SHORT_EN.get(holidays[0].short, holidays[0].short) if holidays and in_month else " "
        )
        holiday_label.add_css_class("holiday-label")
        holiday_label.set_xalign(0)
        holiday_label.set_ellipsize(Pango.EllipsizeMode.END)
        holiday_label.set_max_width_chars(13)
        holiday_label.set_single_line_mode(True)
        cell.append(holiday_label)

        return cell

    def _update_details(self) -> None:
        lunar = convert_solar_to_lunar(self.selected)
        holidays = get_holidays(self.selected, lunar)

        self._big_day.set_text(str(self.selected.day))
        self._weekday.set_text(WEEKDAYS_EN[self.selected.weekday()])
        self._solar_month.set_text(
            f"{month_name[self.selected.month]} {self.selected.year}"
        )
        self._today_pill.set_visible(self.selected == self.today)

        self._lunar_main.set_text(lunar_day_text(lunar))
        self._lunar_sub.set_text(f"Lunar year {lunar.year_name}")

        self._canchi_values["year"].set_text(lunar.year_name)
        self._canchi_values["month"].set_text(lunar.month_name)
        self._canchi_values["day"].set_text(can_chi_day(self.selected))

        child = self._holiday_box.get_first_child()
        while child is not None:
            self._holiday_box.remove(child)
            child = self._holiday_box.get_first_child()

        if not holidays:
            empty = Gtk.Label(label="No holidays", xalign=0)
            empty.add_css_class("muted")
            self._holiday_box.append(empty)
        else:
            for holiday in holidays:
                item = Gtk.Label(label=f"•  {HOLIDAY_NAMES_EN.get(holiday.name, holiday.name)}", xalign=0)
                item.add_css_class("holiday-item")
                item.set_wrap(True)
                self._holiday_box.append(item)

    # --------------------------------------------------------------- about

    def _show_about(self, _button: Gtk.Button) -> None:
        about = Gtk.AboutDialog()
        about.set_transient_for(self)
        about.set_modal(True)
        about.set_program_name("Vietnamese Lunar Calendar")
        about.set_version("1.0.0")
        about.set_comments(
            "Vietnamese solar and lunar calendar using the UTC+7 time zone."
        )
        about.set_logo_icon_name(APP_ID)
        about.set_authors(["iHoan"])
        about.present()


class AmLichApplication(Adw.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.window: MainWindow | None = None
        self.connect("activate", self._on_activate)

    def _on_activate(self, _app: Adw.Application) -> None:
        if self.window is None:
            self._load_resources()
            self.window = MainWindow(application=self)
            self._install_actions()
        self.window.present()

    def _load_resources(self) -> None:
        display = Gdk.Display.get_default()
        if display is not None:
            icon_theme = Gtk.IconTheme.get_for_display(display)
            icon_theme.add_search_path(str(Path(__file__).parent / "assets"))

            provider = Gtk.CssProvider()
            provider.load_from_path(str(Path(__file__).parent / "style.css"))
            Gtk.StyleContext.add_provider_for_display(
                display,
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )

        Gtk.Window.set_default_icon_name(APP_ID)

    def _install_actions(self) -> None:
        assert self.window is not None
        actions = {
            "prev-month": lambda *_: self.window.go_month(-1),
            "next-month": lambda *_: self.window.go_month(1),
            "today": lambda *_: self.window.go_today(),
        }
        for name, callback in actions.items():
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.window.add_action(action)

        self.set_accels_for_action(
            "win.prev-month", ["Left", "Page_Up", "<Alt>Left"]
        )
        self.set_accels_for_action(
            "win.next-month", ["Right", "Page_Down", "<Alt>Right"]
        )
        self.set_accels_for_action("win.today", ["Home", "<Primary>t"])


def main() -> int:
    app = AmLichApplication()
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
