#!/usr/bin/env python3
"""Image Compressor — GTK4/Adw application for compressing images."""

from __future__ import annotations

import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GdkPixbuf", "2.0")

from gi.repository import Adw, Gdk, GdkPixbuf, Gio, GLib, Gtk, Pango
from PIL import Image

from compressor import (
    OUTPUT_FORMATS,
    CompressionResult,
    CompressionSettings,
    compress_image,
    is_supported_image,
    target_dimensions,
)

APP_ID = "vn.ihoan.ImageCompressor"
FORMAT_KEYS = ("auto", "webp", "jpeg", "png")
DEFAULT_OUTPUT = Path.home() / "Pictures" / "Ảnh đã nén"


def format_bytes(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def make_thumbnail(path: Path, size: int = 48) -> Gtk.Image:
    """Use Pillow to create consistent thumbnails for WebP, PNG, and JPG."""
    try:
        with Image.open(path) as opened:
            image = opened.convert("RGBA")
            image.thumbnail((size * 2, size * 2), Image.Resampling.LANCZOS)
            data = image.tobytes()
            pixbuf = GdkPixbuf.Pixbuf.new_from_bytes(
                GLib.Bytes.new(data),
                GdkPixbuf.Colorspace.RGB,
                True,
                8,
                image.width,
                image.height,
                image.width * 4,
            )
            texture = Gdk.Texture.new_for_pixbuf(pixbuf)
            widget = Gtk.Image.new_from_paintable(texture)
            widget.set_pixel_size(size)
            widget.set_size_request(size, size)
            return widget
    except Exception:
        fallback = Gtk.Image.new_from_icon_name("image-missing-symbolic")
        fallback.set_pixel_size(size)
        fallback.set_size_request(size, size)
        return fallback


class ImageRow:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.row.add_css_class("file-row")
        self.row.set_margin_top(8)
        self.row.set_margin_bottom(8)
        self.row.set_margin_start(12)
        self.row.set_margin_end(8)

        self.thumbnail = make_thumbnail(path)
        self.thumbnail.add_css_class("thumbnail")
        self.row.append(self.thumbnail)

        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text.set_hexpand(True)
        self.name = Gtk.Label(label=path.name, xalign=0)
        self.name.set_ellipsize(Pango.EllipsizeMode.END)
        self.name.add_css_class("file-name")
        self.meta = Gtk.Label(xalign=0)
        self.meta.add_css_class("muted")
        self.status = Gtk.Label(label="Ready", xalign=0)
        self.status.add_css_class("file-status")
        text.append(self.name)
        text.append(self.meta)
        text.append(self.status)
        self.row.append(text)

        self.remove = Gtk.Button(icon_name="window-close-symbolic")
        self.remove.set_tooltip_text("Remove this image")
        self.remove.add_css_class("flat")
        self.remove.add_css_class("row-remove")
        self.row.append(self.remove)

        self.original_size = (0, 0)
        self.original_bytes = 0
        self.update_meta()

    def update_meta(self) -> None:
        try:
            with Image.open(self.path) as image:
                width, height = image.size
            self.original_size = (width, height)
            self.original_bytes = self.path.stat().st_size
            self.meta.set_text(
                f"{width} × {height} px  ·  {format_bytes(self.original_bytes)}"
            )
        except Exception:
            self.original_size = (0, 0)
            self.original_bytes = self.path.stat().st_size
            self.meta.set_text(format_bytes(self.original_bytes))

    def update_projected_size(self, max_width: int, max_height: int) -> None:
        if self.original_size == (0, 0):
            return
        width, height = self.original_size
        try:
            new_width, new_height = target_dimensions(
                width, height, max_width, max_height
            )
        except ValueError:
            return
        if (new_width, new_height) == (width, height):
            self.meta.set_text(
                f"{width} × {height} px  ·  {format_bytes(self.original_bytes)}"
            )
        else:
            self.meta.set_text(
                f"{width} × {height} → {new_width} × {new_height} px"
                f"  ·  {format_bytes(self.original_bytes)}"
            )

    def set_status(self, text: str, kind: str = "") -> None:
        for css_class in ("processing", "success", "error"):
            self.status.remove_css_class(css_class)
        if kind:
            self.status.add_css_class(kind)
        self.status.set_text(text)

    def set_result(self, result: CompressionResult) -> None:
        if result.ok:
            self.meta.set_text(
                f"{result.original_size[0]} × {result.original_size[1]}"
                f"  →  {result.output_size[0]} × {result.output_size[1]} px"
                f"  ·  {format_bytes(result.output_bytes)}"
            )
            self.status.set_text("Done")
            self.status.remove_css_class("error")
            self.status.add_css_class("success")
            self.status.set_tooltip_text(str(result.output))
        else:
            self.status.set_text("Error")
            self.status.remove_css_class("success")
            self.status.add_css_class("error")
            self.status.set_tooltip_text(result.error or "Unknown error")


class CompressorWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Image Compressor")
        self.set_default_size(1120, 760)
        self.set_size_request(920, 620)
        self.set_icon_name(APP_ID)
        self.add_css_class("image-compressor-window")

        self.paths: list[Path] = []
        self.rows: dict[Path, ImageRow] = {}
        self.busy = False
        self._results: list[CompressionResult] = []
        self._total_original = 0

        self._build_ui()
        self._update_empty_state()
        self._update_size_preview()

    # ------------------------------------------------------------------ UI

    def _build_ui(self) -> None:
        header = Adw.HeaderBar()
        header.add_css_class("app-header")

        add_button = Gtk.Button()
        add_button.set_child(
            Gtk.Image.new_from_icon_name("list-add-symbolic")
        )
        add_button.set_tooltip_text("Add images (PNG, JPG, WebP)")
        add_button.add_css_class("add-button")
        add_button.connect("clicked", self._choose_files)
        header.pack_start(add_button)

        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        title_box.set_halign(Gtk.Align.CENTER)
        title = Gtk.Label(label="Image Compressor")
        title.add_css_class("app-title")
        subtitle = Gtk.Label(label="WebP · PNG · JPG")
        subtitle.add_css_class("app-subtitle")
        title_box.append(title)
        title_box.append(subtitle)
        header.set_title_widget(title_box)

        about = Gtk.Button(icon_name="help-about-symbolic")
        about.set_tooltip_text("About")
        about.connect("clicked", self._show_about)
        header.pack_end(about)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)

        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        body.append(self._build_main_panel())
        body.append(self._build_sidebar())
        toolbar.set_content(body)
        self.set_content(toolbar)

        drop = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        drop.connect("drop", self._on_drop)
        self.add_controller(drop)

    def _build_main_panel(self) -> Gtk.Widget:
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        panel.set_margin_top(20)
        panel.set_margin_bottom(20)
        panel.set_margin_start(20)
        panel.set_margin_end(20)
        panel.set_hexpand(True)

        heading = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title = Gtk.Label(label="Images to compress", xalign=0)
        title.add_css_class("section-heading")
        title.set_hexpand(True)
        self.count_label = Gtk.Label(label="0 images", xalign=1)
        self.count_label.add_css_class("muted")
        clear_button = Gtk.Button(label="Clear all")
        clear_button.add_css_class("flat")
        clear_button.connect("clicked", self._clear_files)
        heading.append(title)
        heading.append(self.count_label)
        heading.append(clear_button)
        panel.append(heading)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_vexpand(True)

        empty = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        empty.set_valign(Gtk.Align.CENTER)
        empty.set_halign(Gtk.Align.CENTER)
        empty.add_css_class("empty-state")
        icon = Gtk.Image.new_from_icon_name("folder-pictures-symbolic")
        icon.set_pixel_size(72)
        empty_title = Gtk.Label(label="Drop images here")
        empty_title.add_css_class("empty-title")
        empty_hint = Gtk.Label(
            label="or click “Add images” to select multiple files"
        )
        empty_hint.add_css_class("muted")
        empty_button = Gtk.Button(label="Choose images")
        empty_button.add_css_class("suggested-action")
        empty_button.set_halign(Gtk.Align.CENTER)
        empty_button.connect("clicked", self._choose_files)
        empty.append(icon)
        empty.append(empty_title)
        empty.append(empty_hint)
        empty.append(empty_button)
        self.stack.add_named(empty, "empty")

        list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        list_box.add_css_class("file-list")
        list_box.set_vexpand(True)
        self.list_box = list_box
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        scroll.set_child(list_box)
        list_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        list_card.add_css_class("file-list-card")
        list_card.set_overflow(Gtk.Overflow.HIDDEN)
        list_card.set_vexpand(True)
        list_card.append(scroll)
        self.stack.add_named(list_card, "list")

        panel.append(self.stack)
        return panel

    def _build_sidebar(self) -> Gtk.Widget:
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        sidebar.add_css_class("sidebar")
        sidebar.set_size_request(330, -1)
        sidebar.set_margin_top(20)
        sidebar.set_margin_bottom(20)
        sidebar.set_margin_start(4)
        sidebar.set_margin_end(20)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card.add_css_class("settings-card")

        title = Gtk.Label(label="COMPRESSION", xalign=0)
        title.add_css_class("settings-title")
        card.append(title)

        format_label = Gtk.Label(label="Output format", xalign=0)
        format_label.add_css_class("field-label")
        card.append(format_label)
        self.format_dropdown = Gtk.DropDown.new_from_strings(
            [OUTPUT_FORMATS[key] for key in FORMAT_KEYS]
        )
        self.format_dropdown.set_selected(1)  # WebP
        self.format_dropdown.set_hexpand(True)
        self.format_dropdown.connect("notify::selected", self._on_format_changed)
        card.append(self.format_dropdown)

        quality_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        quality_label = Gtk.Label(label="Quality", xalign=0)
        quality_label.add_css_class("field-label")
        quality_label.set_hexpand(True)
        self.quality_value = Gtk.Label(label="80", xalign=1)
        self.quality_value.add_css_class("quality-value")
        quality_row.append(quality_label)
        quality_row.append(self.quality_value)
        card.append(quality_row)
        self.quality_scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 1, 100, 1
        )
        self.quality_scale.set_value(80)
        self.quality_scale.set_draw_value(False)
        self.quality_scale.set_hexpand(True)
        self.quality_scale.connect("value-changed", self._on_quality_changed)
        card.append(self.quality_scale)
        self.quality_hint = Gtk.Label(
            label="JPG/WebP: lower quality creates smaller files. PNG is always lossless.",
            xalign=0,
        )
        self.quality_hint.add_css_class("muted")
        self.quality_hint.set_wrap(True)
        card.append(self.quality_hint)
        sidebar.append(card)

        size_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        size_card.add_css_class("settings-card")
        size_title = Gtk.Label(label="DIMENSIONS", xalign=0)
        size_title.add_css_class("settings-title")
        size_card.append(size_title)

        size_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        width_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        width_box.set_hexpand(True)
        width_label = Gtk.Label(label="Width (px)", xalign=0)
        width_label.add_css_class("field-label")
        self.width_spin = Gtk.SpinButton.new_with_range(0, 30000, 10)
        self.width_spin.set_value(0)
        self.width_spin.set_hexpand(True)
        self.width_spin.set_tooltip_text("0 = automatic")
        self.width_spin.connect("value-changed", self._update_size_preview)
        width_box.append(width_label)
        width_box.append(self.width_spin)

        height_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        height_box.set_hexpand(True)
        height_label = Gtk.Label(label="Height (px)", xalign=0)
        height_label.add_css_class("field-label")
        self.height_spin = Gtk.SpinButton.new_with_range(0, 30000, 10)
        self.height_spin.set_value(0)
        self.height_spin.set_hexpand(True)
        self.height_spin.set_tooltip_text("0 = automatic")
        self.height_spin.connect("value-changed", self._update_size_preview)
        height_box.append(height_label)
        height_box.append(self.height_spin)
        size_row.append(width_box)
        size_row.append(height_box)
        size_card.append(size_row)

        size_hint = Gtk.Label(
            label="Set one side to 0 to scale it proportionally. Set both limits to fit the image within the box.",
            xalign=0,
        )
        size_hint.add_css_class("muted")
        size_hint.set_wrap(True)
        size_card.append(size_hint)

        self.size_preview = Gtk.Label(xalign=0)
        self.size_preview.add_css_class("size-preview")
        self.size_preview.set_wrap(True)
        size_card.append(self.size_preview)
        sidebar.append(size_card)

        output_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        output_card.add_css_class("settings-card")
        output_title = Gtk.Label(label="OUTPUT FOLDER", xalign=0)
        output_title.add_css_class("settings-title")
        output_card.append(output_title)
        output_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.output_entry = Gtk.Entry()
        self.output_entry.set_text(str(DEFAULT_OUTPUT))
        self.output_entry.set_hexpand(True)
        self.output_entry.set_tooltip_text("Folder for compressed images")
        choose_folder = Gtk.Button(icon_name="folder-open-symbolic")
        choose_folder.set_tooltip_text("Choose a folder")
        choose_folder.connect("clicked", self._choose_output_folder)
        output_row.append(self.output_entry)
        output_row.append(choose_folder)
        output_card.append(output_row)
        sidebar.append(output_card)

        self.summary_label = Gtk.Label(label="No images selected", xalign=0)
        self.summary_label.add_css_class("summary")
        self.summary_label.set_wrap(True)
        sidebar.append(self.summary_label)

        self.progress = Gtk.ProgressBar()
        self.progress.set_show_text(False)
        sidebar.append(self.progress)

        self.compress_button = Gtk.Button(label="Compress")
        self.compress_button.add_css_class("suggested-action")
        self.compress_button.add_css_class("compress-button")
        self.compress_button.set_sensitive(False)
        self.compress_button.connect("clicked", self._start_compression)
        sidebar.append(self.compress_button)

        sidebar.set_valign(Gtk.Align.START)
        return sidebar

    # --------------------------------------------------------------- files

    def _choose_files(self, _button: Gtk.Button) -> None:
        dialog = Gtk.FileDialog()
        dialog.set_title("Choose images to compress")
        dialog.set_modal(True)

        filters = Gio.ListStore.new(Gtk.FileFilter)
        image_filter = Gtk.FileFilter()
        image_filter.set_name("PNG, JPG, and WebP images")
        for pattern in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
            image_filter.add_pattern(pattern)
        filters.append(image_filter)
        dialog.set_filters(filters)
        dialog.open_multiple(self, None, self._on_files_selected)

    def _on_files_selected(self, dialog: Gtk.FileDialog, result) -> None:
        try:
            files = dialog.open_multiple_finish(result)
        except GLib.Error:
            return
        if files is None:
            return
        found: list[Path] = []
        for index in range(files.get_n_items()):
            gfile = files.get_item(index)
            if isinstance(gfile, Gio.File):
                path = gfile.get_path()
                if path:
                    found.append(Path(path))
        self._add_paths(found)

    def _add_paths(self, paths: list[Path]) -> None:
        if self.busy:
            return
        added = 0
        for path in paths:
            path = path.expanduser()
            if path in self.rows or not path.is_file():
                continue
            if not is_supported_image(path):
                continue
            try:
                row = ImageRow(path)
            except Exception:
                continue
            self.rows[path] = row
            self.paths.append(path)
            self.list_box.append(row.row)
            row.remove.connect("clicked", self._remove_row, path)
            added += 1
        if added:
            self._recalculate_total()
            self._update_empty_state()
            self.stack.set_visible_child_name("list")

    def _remove_row(self, _button: Gtk.Button, path: Path) -> None:
        if self.busy:
            return
        row = self.rows.pop(path, None)
        if row is None:
            return
        self.list_box.remove(row.row)
        self.paths.remove(path)
        self._recalculate_total()
        self._update_empty_state()

    def _clear_files(self, _button: Gtk.Button) -> None:
        if self.busy:
            return
        self.paths.clear()
        self.rows.clear()
        child = self.list_box.get_first_child()
        while child is not None:
            self.list_box.remove(child)
            child = self.list_box.get_first_child()
        self._recalculate_total()
        self._update_empty_state()

    def _recalculate_total(self) -> None:
        self._total_original = sum(
            path.stat().st_size for path in self.paths if path.exists()
        )
        self.count_label.set_text(f"{len(self.paths)} images")
        if self.paths:
            self.summary_label.set_text(
                f"{len(self.paths)} images · {format_bytes(self._total_original)}"
            )
        else:
            self.summary_label.set_text("No images selected")
        self._update_size_preview()

    def _update_size_preview(self, *_args) -> None:
        """Show projected dimensions as soon as the user sets size limits."""
        if not hasattr(self, "size_preview"):
            return

        if not self.paths:
            self.size_preview.set_text("Add images to preview the compressed dimensions.")
            self.size_preview.set_tooltip_text(None)
            return

        max_width = int(self.width_spin.get_value())
        max_height = int(self.height_spin.get_value())
        previews: list[tuple[str, int, int, int, int]] = []

        for path in self.paths:
            row = self.rows.get(path)
            if row is None or row.original_size == (0, 0):
                continue
            row.update_projected_size(max_width, max_height)
            width, height = row.original_size
            try:
                new_width, new_height = target_dimensions(
                    width, height, max_width, max_height
                )
            except ValueError:
                continue
            previews.append(
                (path.name, width, height, new_width, new_height)
            )

        if not previews:
            self.size_preview.set_text("Could not read image dimensions.")
            self.size_preview.set_tooltip_text(None)
            return

        _, width, height, new_width, new_height = previews[0]
        if (new_width, new_height) == (width, height):
            first_text = f"Unchanged: {width} × {height} px"
        else:
            first_text = (
                f"After compression: {width} × {height} → {new_width} × {new_height} px"
            )

        if len(previews) == 1:
            self.size_preview.set_text(first_text)
            self.size_preview.set_tooltip_text(None)
        else:
            self.size_preview.set_text(
                f"First image: {width} × {height} → "
                f"{new_width} × {new_height} px"
            )
            lines = [
                f"{name}: {w} × {h} → {nw} × {nh} px"
                for name, w, h, nw, nh in previews[:10]
            ]
            if len(previews) > 10:
                lines.append(f"… and {len(previews) - 10} more images")
            self.size_preview.set_tooltip_text("\n".join(lines))

    def _update_empty_state(self) -> None:
        self.stack.set_visible_child_name("list" if self.paths else "empty")
        self.compress_button.set_sensitive(bool(self.paths) and not self.busy)

    def _on_drop(self, _target: Gtk.DropTarget, value, _x: float, _y: float) -> bool:
        if not isinstance(value, Gdk.FileList):
            return False
        paths: list[Path] = []
        for gfile in value.get_files():
            path = gfile.get_path()
            if path:
                paths.append(Path(path))
        self._add_paths(paths)
        return True

    # ------------------------------------------------------------- settings

    def _on_format_changed(self, *_args) -> None:
        selected = FORMAT_KEYS[self.format_dropdown.get_selected()]
        self.quality_scale.set_sensitive(selected != "png")
        self.quality_hint.set_text(
            "PNG is always lossless; the quality setting does not apply."
            if selected == "png"
            else "JPG/WebP: lower quality creates smaller files. PNG is always lossless."
        )

    def _on_quality_changed(self, scale: Gtk.Scale) -> None:
        self.quality_value.set_text(str(int(scale.get_value())))

    def _choose_output_folder(self, _button: Gtk.Button) -> None:
        dialog = Gtk.FileDialog()
        dialog.set_title("Choose an output folder")
        dialog.set_modal(True)
        dialog.select_folder(self, None, self._on_output_folder_selected)

    def _on_output_folder_selected(self, dialog: Gtk.FileDialog, result) -> None:
        try:
            folder = dialog.select_folder_finish(result)
        except GLib.Error:
            return
        if folder is not None:
            path = folder.get_path()
            if path:
                self.output_entry.set_text(path)

    # ------------------------------------------------------------- compress

    def _start_compression(self, _button: Gtk.Button) -> None:
        if self.busy or not self.paths:
            return

        output_text = self.output_entry.get_text().strip()
        output_dir = Path(output_text).expanduser() if output_text else DEFAULT_OUTPUT
        settings = CompressionSettings(
            output_format=FORMAT_KEYS[self.format_dropdown.get_selected()],
            quality=int(self.quality_scale.get_value()),
            max_width=int(self.width_spin.get_value()),
            max_height=int(self.height_spin.get_value()),
            output_dir=output_dir,
        )

        self.busy = True
        self._results = []
        self.progress.set_fraction(0)
        self.summary_label.set_text("Compressing…")
        self._set_controls_sensitive(False)
        self.compress_button.set_sensitive(False)

        paths = list(self.paths)
        thread = threading.Thread(
            target=self._compress_worker,
            args=(paths, settings),
            daemon=True,
        )
        thread.start()

    def _compress_worker(
        self,
        paths: list[Path],
        settings: CompressionSettings,
    ) -> None:
        total = len(paths)
        for index, path in enumerate(paths, start=1):
            GLib.idle_add(self._mark_processing, path)
            result = compress_image(path, settings)
            GLib.idle_add(self._show_result, result)
            GLib.idle_add(self._update_progress, index / total)
        GLib.idle_add(self._finish_compression)

    def _mark_processing(self, path: Path) -> bool:
        row = self.rows.get(path)
        if row is not None:
            row.set_status("Compressing…", "processing")
        return False

    def _update_progress(self, fraction: float) -> bool:
        self.progress.set_fraction(fraction)
        return False

    def _show_result(self, result: CompressionResult) -> bool:
        self._results.append(result)
        row = self.rows.get(result.source)
        if row is not None:
            row.set_result(result)
        return False

    def _finish_compression(self) -> bool:
        self.busy = False
        self._set_controls_sensitive(True)
        self._update_empty_state()
        self.progress.set_fraction(1)

        successes = [result for result in self._results if result.ok]
        failures = [result for result in self._results if not result.ok]
        if not successes:
            self.summary_label.set_text(
                f"No images compressed · {len(failures)} errors"
            )
            return False

        total_input = sum(result.original_bytes for result in successes)
        total_output = sum(result.output_bytes for result in successes)
        reduction = (
            round((1 - total_output / total_input) * 100) if total_input else 0
        )
        if reduction >= 0:
            save_text = f"saved {reduction}%"
        else:
            save_text = f"increased by {abs(reduction)}%"
        extra = f" · {len(failures)} errors" if failures else ""
        self.summary_label.set_text(
            f"{len(successes)}/{len(self._results)} images · "
            f"{format_bytes(total_output)} · {save_text}{extra}"
        )
        return False

    def _set_controls_sensitive(self, sensitive: bool) -> None:
        self.width_spin.set_sensitive(sensitive)
        self.height_spin.set_sensitive(sensitive)
        self.format_dropdown.set_sensitive(sensitive)
        self.quality_scale.set_sensitive(
            sensitive
            and FORMAT_KEYS[self.format_dropdown.get_selected()] != "png"
        )
        self.output_entry.set_sensitive(sensitive)
        self.compress_button.set_sensitive(sensitive and bool(self.paths))

    # --------------------------------------------------------------- about

    def _show_about(self, _button: Gtk.Button) -> None:
        about = Gtk.AboutDialog()
        about.set_transient_for(self)
        about.set_modal(True)
        about.set_program_name("Image Compressor")
        about.set_version("1.0.0")
        about.set_comments(
            "Batch-compress images to WebP, PNG, or JPG while preserving aspect ratio."
        )
        about.set_logo_icon_name(APP_ID)
        about.set_authors(["iHoan"])
        about.present()


class CompressorApplication(Adw.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.window: CompressorWindow | None = None
        self.connect("activate", self._on_activate)

    def _on_activate(self, _app: Adw.Application) -> None:
        if self.window is None:
            self._load_resources()
            self.window = CompressorWindow(application=self)
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


def main() -> int:
    return CompressorApplication().run()


if __name__ == "__main__":
    raise SystemExit(main())
