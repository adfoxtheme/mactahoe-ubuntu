#!/usr/bin/env python3
"""
MacTahoe Icon Manager
---------------------
Ứng dụng GTK4/Adw để đổi icon MacTahoe cho các ứng dụng đã cài
(hệ thống, snap, flatpak, app local).

- Quét các file .desktop trong:
  ~/.local/share/applications
  ~/.local/share/flatpak/exports/share/applications
  /var/lib/flatpak/exports/share/applications
  /var/lib/snapd/desktop/applications
  các thư mục trong XDG_DATA_DIRS (thường /usr/local/share, /usr/share)

- Ghi đè an toàn vào ~/.local/share/applications/<tên>.desktop
- Backup file gốc vào ~/.local/share/mactahoe-icon-manager/backups/
- Có nút Khôi phục để trả lại icon gốc

Chạy: mactahoe-icon-manager
Kiểm tra dữ liệu: mactahoe-icon-manager --self-test
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Pango", "1.0")

from gi.repository import Adw, Gdk, Gio, GLib, Gtk, Pango


# ---------------------------------------------------------------------------
# Đường dẫn
# ---------------------------------------------------------------------------

HOME = Path.home()
DATA_HOME = Path(os.environ.get("XDG_DATA_HOME") or (HOME / ".local/share")).expanduser()

LOCAL_APPS = DATA_HOME / "applications"
BACKUP_DIR = DATA_HOME / "mactahoe-icon-manager" / "backups"
ICON_STORE_DIR = DATA_HOME / "mactahoe-icon-manager" / "icons"

_xdg_data_dirs = os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share"
XDG_DATA_DIRS = [Path(p).expanduser() for p in _xdg_data_dirs.split(":") if p]


def _unique_dirs(dirs: list[Path]) -> list[Path]:
    seen: set[str] = set()
    result: list[Path] = []
    for d in dirs:
        key = str(d)
        if key not in seen:
            seen.add(key)
            result.append(d)
    return result


APP_DIRS = _unique_dirs(
    [
        LOCAL_APPS,
        DATA_HOME / "flatpak/exports/share/applications",
        Path("/var/lib/flatpak/exports/share/applications"),
        Path("/var/lib/snapd/desktop/applications"),
        *[d / "applications" for d in XDG_DATA_DIRS],
    ]
)

ICON_THEME_ROOTS = _unique_dirs(
    [
        DATA_HOME / "icons",
        HOME / ".icons",
        Path("/usr/local/share/icons"),
        Path("/usr/share/icons"),
    ]
)


# ---------------------------------------------------------------------------
# Dữ liệu ứng dụng
# ---------------------------------------------------------------------------

@dataclass
class AppEntry:
    desktop_id: str
    name: str
    icon: str
    source_path: Path
    has_system: bool
    hidden: bool
    custom: bool
    source_label: str


def _unescape(value: str) -> str:
    return (
        value.replace("\\n", " ")
        .replace("\\t", " ")
        .replace("\\r", " ")
        .strip()
    )


def parse_desktop(path: Path) -> dict[str, str]:
    """Đọc các khóa cần thiết trong [Desktop Entry]."""
    info: dict[str, str] = {}
    section = ""
    keys = {
        "Name",
        "Name[vi]",
        "Icon",
        "Type",
        "NoDisplay",
        "Hidden",
        "OnlyShowIn",
        "NotShowIn",
        "Exec",
    }
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("[") and line.endswith("]"):
                    section = line[1:-1]
                    continue
                if section != "Desktop Entry" or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                if key in keys:
                    info[key] = _unescape(value)
    except OSError:
        return {}
    return info


def read_icon(path: Path) -> str:
    return parse_desktop(path).get("Icon", "")


def icon_is_mactahoe(value: str) -> bool:
    if not value:
        return False
    return "/icons/MacTahoe" in value or str(ICON_STORE_DIR) in value


def source_label(path: Path) -> str:
    s = str(path)
    if s.startswith(str(LOCAL_APPS)):
        return "cục bộ"
    if "snapd" in s:
        return "snap"
    if "flatpak" in s:
        return "flatpak"
    return "hệ thống"


def scan_apps(include_hidden: bool = True) -> list[AppEntry]:
    """Quét tất cả .desktop, ưu tiên file trong ~/.local/share/applications."""
    paths: dict[str, list[Path]] = {}
    for directory in APP_DIRS:
        try:
            candidates = list(directory.glob("*.desktop"))
        except OSError:
            continue
        for path in candidates:
            try:
                if not path.is_file():
                    continue
            except OSError:
                continue
            paths.setdefault(path.name, []).append(path)

    result: list[AppEntry] = []
    for desktop_id, candidates in paths.items():
        source = candidates[0]
        info = parse_desktop(source)
        if not info:
            continue
        if info.get("Type", "Application") != "Application":
            continue

        hidden = (
            info.get("NoDisplay", "").lower() == "true"
            or info.get("Hidden", "").lower() == "true"
        )
        if hidden and not include_hidden:
            continue

        name = info.get("Name[vi]") or info.get("Name") or Path(desktop_id).stem
        icon = info.get("Icon", "")
        local = LOCAL_APPS / desktop_id
        backup = BACKUP_DIR / (desktop_id + ".bak")
        custom = backup.exists() or (local.exists() and len(candidates) > 1)

        result.append(
            AppEntry(
                desktop_id=desktop_id,
                name=name,
                icon=icon,
                source_path=source,
                has_system=len(candidates) > 1,
                hidden=hidden,
                custom=custom,
                source_label=source_label(source),
            )
        )

    result.sort(key=lambda entry: entry.name.casefold())
    return result


def can_reset(entry: AppEntry) -> bool:
    local = LOCAL_APPS / entry.desktop_id
    backup = BACKUP_DIR / (entry.desktop_id + ".bak")
    if backup.exists():
        return True
    if local.exists() and entry.has_system:
        return icon_is_mactahoe(read_icon(local))
    return False


def set_icon_in_desktop(text: str, icon_value: str) -> str:
    """Thay Icon= trong [Desktop Entry]; thêm nếu chưa có."""
    lines = text.splitlines()
    out: list[str] = []
    in_entry = False
    replaced = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_entry = stripped == "[Desktop Entry]"
            out.append(line)
            continue
        if in_entry and stripped.startswith("Icon="):
            if not replaced:
                out.append(f"Icon={icon_value}")
                replaced = True
            continue
        out.append(line)

    if not replaced:
        result: list[str] = []
        inserted = False
        for line in out:
            result.append(line)
            if not inserted and line.strip() == "[Desktop Entry]":
                result.append(f"Icon={icon_value}")
                inserted = True
        if not inserted:
            result = ["[Desktop Entry]", f"Icon={icon_value}"] + out
        out = result

    return "\n".join(out).rstrip("\n") + "\n"


def update_desktop_database() -> None:
    try:
        LOCAL_APPS.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["update-desktop-database", str(LOCAL_APPS)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (FileNotFoundError, OSError):
        pass


def apply_icon(entry: AppEntry, icon_path: Path) -> str:
    LOCAL_APPS.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ICON_STORE_DIR.mkdir(parents=True, exist_ok=True)

    if not icon_path.is_file():
        raise OSError(f"Không tìm thấy file icon: {icon_path}")

    # Copy icon sang thư mục riêng để update/đổi theme không làm hỏng đường dẫn.
    stable_icon = ICON_STORE_DIR / (
        entry.desktop_id.removesuffix(".desktop") + icon_path.suffix.lower()
    )
    try:
        if icon_path.resolve() != stable_icon.resolve():
            shutil.copy2(icon_path, stable_icon)
    except OSError as exc:
        raise OSError(f"Không copy được icon: {exc}") from exc

    local = LOCAL_APPS / entry.desktop_id
    backup = BACKUP_DIR / (entry.desktop_id + ".bak")

    if local.is_symlink():
        if not backup.exists():
            shutil.copy2(local, backup)
        text = local.read_text(encoding="utf-8", errors="replace")
        local.unlink()
    elif local.exists():
        if not local.is_file():
            raise OSError(f"{local} không phải file thường")
        if not backup.exists():
            shutil.copy2(local, backup)
        text = local.read_text(encoding="utf-8", errors="replace")
    else:
        text = entry.source_path.read_text(encoding="utf-8", errors="replace")

    new_text = set_icon_in_desktop(text, str(stable_icon))
    local.write_text(new_text, encoding="utf-8")
    try:
        local.chmod(0o644)
    except OSError:
        pass

    update_desktop_database()
    return f"Đã đặt icon MacTahoe cho {entry.name}"


def reset_icon(entry: AppEntry) -> str:
    local = LOCAL_APPS / entry.desktop_id
    backup = BACKUP_DIR / (entry.desktop_id + ".bak")

    if backup.exists():
        if local.is_symlink():
            local.unlink()
        elif local.exists() and not local.is_file():
            raise OSError(f"{local} không phải file thường")
        shutil.copy2(backup, local)
        try:
            local.chmod(0o644)
        except OSError:
            pass
        backup.unlink()
        update_desktop_database()
        return f"Đã khôi phục icon gốc cho {entry.name}"

    if local.exists() and entry.has_system:
        if local.is_symlink() or local.is_file():
            local.unlink()
        else:
            raise OSError(f"{local} không phải file thường")
        update_desktop_database()
        return f"Đã bỏ ghi đè, {entry.name} dùng lại icon hệ thống"

    return "Không có ghi đè để khôi phục"


# ---------------------------------------------------------------------------
# Icon MacTahoe
# ---------------------------------------------------------------------------

def find_icon_theme() -> Path | None:
    names: list[str] = []
    try:
        result = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "icon-theme"],
            check=False,
            capture_output=True,
            text=True,
        )
        current = result.stdout.strip().strip("'\"")
        if current.startswith("MacTahoe"):
            names.append(current)
    except (FileNotFoundError, OSError):
        pass

    for fallback in ("MacTahoe-blue", "MacTahoe", "MacTahoe-dark", "MacTahoe-light"):
        if fallback not in names:
            names.append(fallback)

    for root in ICON_THEME_ROOTS:
        for name in names:
            path = root / name
            if (path / "index.theme").exists():
                return path
    return None


ICON_GROUPS: dict[str, list[str]] = {
    "apps": [
        "apps/scalable",
        "apps/32",
        "apps/22",
        "apps/16",
        "apps@2x/32",
    ],
    "places": [
        "places/scalable",
        "places/24",
        "places/22",
        "places/16",
        "places@2x/32",
    ],
    "categories": [
        "categories/32",
        "categories/22",
        "categories@2x/32",
    ],
    "devices": [
        "devices/scalable",
        "devices/32",
        "devices/24",
        "devices/22",
        "devices/16",
    ],
}

IMAGE_SUFFIXES = {".svg", ".png", ".xpm", ".jpg", ".jpeg"}


def build_icon_index(theme_dir: Path) -> dict[str, tuple[Path, str]]:
    index: dict[str, tuple[Path, str]] = {}
    for group, subdirs in ICON_GROUPS.items():
        for subdir in subdirs:
            directory = theme_dir / subdir
            if not directory.is_dir():
                continue
            try:
                entries = list(directory.iterdir())
            except OSError:
                continue
            for path in entries:
                if path.suffix.lower() not in IMAGE_SUFFIXES:
                    continue
                name = path.stem
                if not name or name.startswith(".") or name.endswith("-symbolic"):
                    continue
                if name in index:
                    continue
                try:
                    if not path.is_file():
                        continue
                except OSError:
                    continue
                index[name] = (path, group)
    return index


def make_icon_image(icon_value: str, size: int) -> Gtk.Image:
    if icon_value:
        expanded = os.path.expanduser(icon_value)
        path = Path(expanded)
        if path.is_absolute() and path.exists():
            image = Gtk.Image.new_from_file(str(path))
            image.set_pixel_size(size)
            return image

        name = icon_value
        if name.lower().endswith((".svg", ".png", ".xpm", ".jpg", ".jpeg")):
            name = Path(name).stem
        display = Gdk.Display.get_default()
        if display is not None:
            theme = Gtk.IconTheme.get_for_display(display)
            if theme.has_icon(name):
                image = Gtk.Image.new_from_icon_name(name)
                image.set_pixel_size(size)
                return image

    image = Gtk.Image.new_from_icon_name("application-x-executable")
    image.set_pixel_size(size)
    return image


# ---------------------------------------------------------------------------
# Giao diện
# ---------------------------------------------------------------------------

class IconManagerWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.set_default_size(1180, 760)
        self.set_title("MacTahoe Icon Manager")

        self.icon_theme_dir = find_icon_theme()
        self.icon_index = (
            build_icon_index(self.icon_theme_dir) if self.icon_theme_dir else {}
        )
        self.icon_paths: dict[str, Path] = {
            name: path for name, (path, _group) in self.icon_index.items()
        }
        self.icon_groups: dict[str, str] = {
            name: group for name, (_path, group) in self.icon_index.items()
        }

        self.selected_app: AppEntry | None = None
        self.selected_icon: str | None = None
        self.icon_query = ""
        self.group_mode = "apps"
        self.rows_by_id: dict[str, Gtk.ListBoxRow] = {}
        self.row_apps: dict[Gtk.ListBoxRow, AppEntry] = {}

        self._install_css()
        self._build_ui()
        self._build_icon_model()
        self.rebuild_app_list()

        if not self.icon_theme_dir:
            self._toast("Không tìm thấy icon theme MacTahoe trong ~/.local/share/icons")

    def _install_css(self) -> None:
        display = Gdk.Display.get_default()
        if display is None:
            return
        provider = Gtk.CssProvider()
        css = b"""
        .icon-cell {
            padding: 6px;
            border-radius: 10px;
        }
        .icon-cell:hover {
            background-color: rgba(128, 128, 128, 0.12);
        }
        """
        try:
            if hasattr(provider, "load_from_string"):
                provider.load_from_string(css.decode("utf-8"))
            else:
                provider.load_from_data(css)
        except GLib.Error:
            return
        Gtk.StyleContext.add_provider_for_display(
            display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _build_ui(self) -> None:
        header = Adw.HeaderBar()
        header.set_title_widget(
            Adw.WindowTitle(
                title="MacTahoe Icon Manager",
                subtitle="Đổi icon cho ứng dụng đã cài",
            )
        )
        self.refresh_button = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        self.refresh_button.set_tooltip_text("Quét lại ứng dụng")
        self.refresh_button.connect("clicked", lambda *_: self.rebuild_app_list())
        header.pack_end(self.refresh_button)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(440)
        paned.set_resize_start_child(False)
        paned.set_shrink_start_child(False)
        paned.set_vexpand(True)

        # --- Cột trái: ứng dụng ---
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        left.set_margin_start(12)
        left.set_margin_end(6)
        left.set_margin_top(8)
        left.set_margin_bottom(8)

        app_title = Gtk.Label(label="Ứng dụng", xalign=0)
        app_title.add_css_class("heading")
        left.append(app_title)

        self.app_search = Gtk.SearchEntry()
        self.app_search.set_placeholder_text("Tìm ứng dụng…")
        self.app_search.connect("search-changed", lambda *_: self._apply_app_filter())
        left.append(self.app_search)

        hidden_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        hidden_label = Gtk.Label(label="Hiện app ẩn", xalign=0)
        hidden_label.set_hexpand(True)
        self.hidden_switch = Gtk.Switch()
        self.hidden_switch.connect("notify::active", lambda *_: self.rebuild_app_list())
        hidden_box.append(hidden_label)
        hidden_box.append(self.hidden_switch)
        left.append(hidden_box)

        self.app_list = Gtk.ListBox()
        self.app_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.app_list.connect("row-selected", self._on_app_selected)

        app_scroller = Gtk.ScrolledWindow()
        app_scroller.set_vexpand(True)
        app_scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        if hasattr(app_scroller, "set_has_frame"):
            app_scroller.set_has_frame(True)
        app_scroller.set_child(self.app_list)
        left.append(app_scroller)

        # --- Cột phải: icon ---
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        right.set_margin_start(6)
        right.set_margin_end(12)
        right.set_margin_top(8)
        right.set_margin_bottom(8)

        right_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        icon_title = Gtk.Label(label="Icon MacTahoe", xalign=0)
        icon_title.add_css_class("heading")
        icon_title.set_hexpand(True)
        self.group_dropdown = Gtk.DropDown.new_from_strings(
            ["Ứng dụng", "Thư mục", "Tất cả"]
        )
        self.group_dropdown.connect("notify::selected", self._on_group_changed)
        right_header.append(icon_title)
        right_header.append(self.group_dropdown)
        right.append(right_header)

        self.target_label = Gtk.Label(label="Chưa chọn ứng dụng", xalign=0)
        self.target_label.add_css_class("dim-label")
        self.target_label.add_css_class("caption")
        self.target_label.set_ellipsize(Pango.EllipsizeMode.END)
        right.append(self.target_label)

        self.icon_search = Gtk.SearchEntry()
        self.icon_search.set_placeholder_text("Tìm icon… (ví dụ: firefox, terminal)")
        self.icon_search.connect("search-changed", self._on_icon_search)
        right.append(self.icon_search)

        self.icon_scroller = Gtk.ScrolledWindow()
        self.icon_scroller.set_vexpand(True)
        self.icon_scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        if hasattr(self.icon_scroller, "set_has_frame"):
            self.icon_scroller.set_has_frame(True)
        right.append(self.icon_scroller)

        paned.set_start_child(left)
        paned.set_end_child(right)
        root.append(paned)

        # --- Thanh hành động ---
        actionbar = Gtk.ActionBar()
        self.status_label = Gtk.Label(
            label="Chọn ứng dụng bên trái, rồi chọn icon MacTahoe bên phải."
        )
        self.status_label.set_xalign(0)
        self.status_label.set_hexpand(True)
        self.status_label.set_ellipsize(Pango.EllipsizeMode.END)
        actionbar.pack_start(self.status_label)

        self.reset_button = Gtk.Button(label="Khôi phục")
        self.reset_button.set_tooltip_text("Trả lại icon gốc / bỏ ghi đè")
        self.reset_button.connect("clicked", self._on_reset_clicked)
        self.reset_button.set_sensitive(False)
        actionbar.pack_end(self.reset_button)

        self.apply_button = Gtk.Button(label="Áp dụng")
        self.apply_button.add_css_class("suggested-action")
        self.apply_button.set_tooltip_text("Đặt icon đã chọn cho ứng dụng")
        self.apply_button.connect("clicked", self._on_apply_clicked)
        self.apply_button.set_sensitive(False)
        actionbar.pack_end(self.apply_button)

        root.append(actionbar)

        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(header)
        toolbar_view.set_content(root)

        self.toast_overlay = Adw.ToastOverlay()
        self.toast_overlay.set_child(toolbar_view)
        self.set_content(self.toast_overlay)

    def _build_icon_model(self) -> None:
        names = sorted(self.icon_paths.keys(), key=str.casefold)
        self.icon_model = Gtk.StringList.new(names)

        self.icon_filter = Gtk.CustomFilter.new(self._icon_filter)
        self.icon_filter_model = Gtk.FilterListModel(
            model=self.icon_model, filter=self.icon_filter
        )

        self.icon_selection = Gtk.SingleSelection(model=self.icon_filter_model)
        self.icon_selection.set_autoselect(False)
        self.icon_selection.set_can_unselect(True)
        self.icon_selection.connect("selection-changed", self._on_icon_selected)

        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._setup_icon_item)
        factory.connect("bind", self._bind_icon_item)

        self.icon_grid = Gtk.GridView(model=self.icon_selection, factory=factory)
        self.icon_grid.set_max_columns(8)
        self.icon_grid.set_min_columns(4)
        if hasattr(self.icon_grid, "set_single_click_activate"):
            self.icon_grid.set_single_click_activate(False)
        self.icon_scroller.set_child(self.icon_grid)

    def _icon_filter(self, item, *_args) -> bool:
        try:
            name = item.get_string()
        except AttributeError:
            return False
        if self.icon_query and self.icon_query not in name.casefold():
            return False
        group = self.icon_groups.get(name, "apps")
        if self.group_mode == "apps":
            return group == "apps"
        if self.group_mode == "places":
            return group == "places"
        return group in {"apps", "places", "categories", "devices"}

    def _on_icon_search(self, _entry) -> None:
        self.icon_query = self.icon_search.get_text().strip().casefold()
        if hasattr(self, "icon_selection"):
            self.icon_selection.unselect_all()
        self.icon_filter.changed(Gtk.FilterChange.DIFFERENT)

    def _on_group_changed(self, dropdown, _pspec) -> None:
        index = dropdown.get_selected()
        if index == 0:
            self.group_mode = "apps"
        elif index == 1:
            self.group_mode = "places"
        elif index == 2:
            self.group_mode = "all"
        else:
            self.group_mode = "apps"
        if hasattr(self, "icon_selection"):
            self.icon_selection.unselect_all()
        self.icon_filter.changed(Gtk.FilterChange.DIFFERENT)

    def _setup_icon_item(self, _factory, item) -> None:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        box.add_css_class("icon-cell")
        box.set_size_request(84, -1)

        image = Gtk.Image()
        image.set_from_icon_name("application-x-executable")
        image.set_pixel_size(40)

        label = Gtk.Label()
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_max_width_chars(12)
        label.set_justify(Gtk.Justification.CENTER)

        box.append(image)
        box.append(label)
        item.set_child(box)

    def _bind_icon_item(self, _factory, item) -> None:
        box = item.get_child()
        image = box.get_first_child()
        label = image.get_next_sibling()

        name = item.get_item().get_string()
        path = self.icon_paths.get(name)
        if path is not None:
            try:
                image.set_from_file(str(path))
            except GLib.Error:
                image.set_from_icon_name(name)
        else:
            image.set_from_icon_name(name)
        label.set_text(name)
        label.set_tooltip_text(name)

    def _on_icon_selected(self, _selection, _position, _n_items) -> None:
        selected = self.icon_selection.get_selected_item()
        if selected is None:
            self.selected_icon = None
            self.status_label.set_text("Chọn một icon MacTahoe ở bên phải.")
        else:
            self.selected_icon = selected.get_string()
            self.status_label.set_text(f"Icon đã chọn: {self.selected_icon}")
        self._update_buttons()

    def _on_app_selected(self, _listbox, row) -> None:
        if row is None:
            self.selected_app = None
            self.status_label.set_text("Chọn một ứng dụng ở bên trái.")
        else:
            self.selected_app = self.row_apps.get(row)
            if self.selected_app is not None:
                self.status_label.set_text(f"Đang chọn: {self.selected_app.name}")
        if self.selected_app is None:
            self.target_label.set_text("Chưa chọn ứng dụng")
        else:
            self.target_label.set_text(f"Đang sửa: {self.selected_app.name}")
        self._update_buttons()

    def _update_buttons(self) -> None:
        self.apply_button.set_sensitive(
            bool(self.selected_app and self.selected_icon and self.icon_paths)
        )
        self.reset_button.set_sensitive(
            bool(self.selected_app and can_reset(self.selected_app))
        )

    def _make_app_row(self, entry: AppEntry) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(8)
        box.set_margin_end(8)

        box.append(make_icon_image(entry.icon, 32))

        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        text.set_hexpand(True)

        name = Gtk.Label(xalign=0)
        name.set_markup(f"<b>{GLib.markup_escape_text(entry.name)}</b>")
        name.set_ellipsize(Pango.EllipsizeMode.END)

        subtitle = f"{entry.desktop_id} • {entry.source_label}"
        if entry.custom:
            subtitle += " • đã đổi"
        sub = Gtk.Label(label=subtitle, xalign=0)
        sub.add_css_class("dim-label")
        sub.add_css_class("caption")
        sub.set_ellipsize(Pango.EllipsizeMode.END)

        text.append(name)
        text.append(sub)
        box.append(text)
        row.set_child(box)
        return row

    def _apply_app_filter(self) -> None:
        query = self.app_search.get_text().strip().casefold()
        for row, entry in self.row_apps.items():
            haystack = f"{entry.name} {entry.desktop_id}".casefold()
            row.set_visible(not query or query in haystack)

    def rebuild_app_list(self, select_id: str | None = None) -> None:
        current = select_id
        if current is None and self.selected_app is not None:
            current = self.selected_app.desktop_id

        child = self.app_list.get_first_child()
        while child is not None:
            self.app_list.remove(child)
            child = self.app_list.get_first_child()

        self.rows_by_id = {}
        self.row_apps = {}

        apps = scan_apps(include_hidden=self.hidden_switch.get_active())
        if not apps:
            self.selected_app = None
            self.target_label.set_text("Chưa chọn ứng dụng")
            self.status_label.set_text("Không tìm thấy ứng dụng nào.")
            self._update_buttons()
            return

        for entry in apps:
            row = self._make_app_row(entry)
            self.app_list.append(row)
            self.rows_by_id[entry.desktop_id] = row
            self.row_apps[row] = entry

        self._apply_app_filter()

        target = self.rows_by_id.get(current) if current else None
        if target is None:
            child = self.app_list.get_first_child()
            while child is not None and not child.get_visible():
                child = child.get_next_sibling()
            target = child

        if target is not None:
            self.app_list.select_row(target)
        else:
            self.selected_app = None
            self.target_label.set_text("Chưa chọn ứng dụng")
            self._update_buttons()

    def _on_apply_clicked(self, _button) -> None:
        entry = self.selected_app
        icon_name = self.selected_icon
        if entry is None:
            self._toast("Chọn ứng dụng ở cột bên trái trước.")
            return
        if icon_name is None:
            self._toast("Chọn icon MacTahoe ở cột bên phải trước.")
            return
        icon_path = self.icon_paths.get(icon_name)
        if icon_path is None:
            self._toast("Không tìm thấy file icon đã chọn.")
            return

        desktop_id = entry.desktop_id
        try:
            message = apply_icon(entry, icon_path)
        except OSError as exc:
            self._toast(f"Lỗi: {exc}")
            return

        self._toast(message + " — có thể cần logout/login để icon cập nhật")
        self.rebuild_app_list(select_id=desktop_id)

    def _on_reset_clicked(self, _button) -> None:
        entry = self.selected_app
        if entry is None:
            return

        dialog = Adw.MessageDialog(transient_for=self)
        dialog.set_heading("Khôi phục icon gốc?")
        dialog.set_body(
            f"Ứng dụng: {entry.name}\n\n"
            "Thao tác này sẽ bỏ icon MacTahoe đã đặt và trả lại icon ban đầu."
        )
        dialog.add_response("cancel", "Hủy")
        dialog.add_response("reset", "Khôi phục")
        dialog.set_response_appearance(
            "reset", Adw.ResponseAppearance.DESTRUCTIVE
        )
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", self._on_reset_response, entry)
        dialog.present()

    def _on_reset_response(self, _dialog, response: str, entry: AppEntry) -> None:
        if response != "reset":
            return
        desktop_id = entry.desktop_id
        try:
            message = reset_icon(entry)
        except OSError as exc:
            self._toast(f"Lỗi: {exc}")
            return
        self._toast(message)
        self.rebuild_app_list(select_id=desktop_id)

    def _toast(self, message: str) -> None:
        toast = Adw.Toast.new(message)
        toast.set_timeout(4)
        self.toast_overlay.add_toast(toast)
        self.status_label.set_text(message)


class IconManagerApplication(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="io.github.mactahoe.IconManager",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )

    def do_activate(self):
        window = self.get_active_window()
        if window is None:
            window = IconManagerWindow(application=self)
        window.present()


# ---------------------------------------------------------------------------
# Self-test (không cần màn hình)
# ---------------------------------------------------------------------------

def self_test() -> int:
    print(f"DATA_HOME : {DATA_HOME}")
    print(f"LOCAL_APPS: {LOCAL_APPS}")
    print(f"BACKUP_DIR: {BACKUP_DIR}")
    print(f"ICON_STORE_DIR: {ICON_STORE_DIR}")

    apps = scan_apps(include_hidden=True)
    print(f"\nỨng dụng tìm thấy: {len(apps)}")
    for entry in apps[:8]:
        print(
            f"  - {entry.desktop_id} | {entry.name} | icon={entry.icon!r} "
            f"| {entry.source_label} | custom={entry.custom}"
        )

    theme = find_icon_theme()
    print(f"\nIcon theme: {theme}")
    if theme is not None:
        index = build_icon_index(theme)
        counts: dict[str, int] = {}
        for _path, group in index.values():
            counts[group] = counts.get(group, 0) + 1
        print(f"Icon tìm thấy: {len(index)} {counts}")

    # Test parser
    sample = "[Desktop Entry]\nType=Application\nName=Test\nIcon=old\n"
    parsed = set_icon_in_desktop(sample, "/tmp/new-icon.svg")
    assert "Icon=/tmp/new-icon.svg" in parsed
    assert "Icon=old" not in parsed

    sample_no_icon = "[Desktop Entry]\nType=Application\nName=Test\n"
    parsed_no_icon = set_icon_in_desktop(sample_no_icon, "/tmp/new-icon.svg")
    assert "Icon=/tmp/new-icon.svg" in parsed_no_icon

    sample_action = (
        "[Desktop Entry]\nType=Application\nName=Test\nIcon=old\n"
        "[Desktop Action new]\nName=New\nIcon=action-icon\n"
    )
    parsed_action = set_icon_in_desktop(sample_action, "/tmp/new-icon.svg")
    assert "Icon=/tmp/new-icon.svg" in parsed_action
    assert "Icon=action-icon" in parsed_action

    print("\nParser: OK")
    return 0


def print_help() -> None:
    print(
        """MacTahoe Icon Manager

Cách dùng:
  mactahoe-icon-manager              Mở giao diện
  mactahoe-icon-manager --self-test  Kiểm tra dữ liệu, không mở cửa sổ
  mactahoe-icon-manager --help       Hiện trợ giúp
  mactahoe-icon-manager --version    Hiện phiên bản

Trong giao diện:
  1. Chọn ứng dụng ở cột trái.
  2. Chọn icon MacTahoe ở cột phải.
  3. Bấm "Áp dụng".
  4. Bấm "Khôi phục" để trả lại icon gốc.

Ghi đè được lưu tại:
  ~/.local/share/applications/
Backup icon gốc:
  ~/.local/share/mactahoe-icon-manager/backups/
Icon đã chọn được copy vào:
  ~/.local/share/mactahoe-icon-manager/icons/
"""
    )


def main() -> int:
    if "--help" in sys.argv or "-h" in sys.argv:
        print_help()
        return 0
    if "--version" in sys.argv:
        print("MacTahoe Icon Manager 1.0")
        return 0
    if "--self-test" in sys.argv:
        return self_test()

    GLib.set_application_name("MacTahoe Icon Manager")
    GLib.set_prgname("mactahoe-icon-manager")
    Adw.init()

    app = IconManagerApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
