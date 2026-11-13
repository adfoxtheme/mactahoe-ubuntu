"""Image compression core.
Supports PNG/JPEG/WebP input and WebP/JPEG/PNG output or the original format.
Images are resized proportionally and are never enlarged beyond their limits.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageOps

SUPPORTED_INPUT_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
OUTPUT_FORMATS = {
    "auto": "Keep original format",
    "webp": "WebP",
    "jpeg": "JPEG",
    "png": "PNG",
}


@dataclass(frozen=True)
class CompressionSettings:
    output_format: str = "webp"
    quality: int = 80
    max_width: int = 0
    max_height: int = 0
    output_dir: Path | None = None


@dataclass(frozen=True)
class CompressionResult:
    source: Path
    output: Path | None
    original_bytes: int
    output_bytes: int
    original_size: tuple[int, int]
    output_size: tuple[int, int]
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.output is not None

    @property
    def reduction(self) -> int:
        if self.original_bytes <= 0:
            return 0
        return round((1 - self.output_bytes / self.original_bytes) * 100)


def is_supported_image(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_INPUT_SUFFIXES


def format_label(key: str) -> str:
    return OUTPUT_FORMATS.get(key, key)


def target_dimensions(
    original_width: int,
    original_height: int,
    max_width: int,
    max_height: int,
) -> tuple[int, int]:
    """Calculate target dimensions.
    - Both limits are zero: keep the original dimensions.
    - One limit is zero: fit the other dimension proportionally.
    - Both limits are positive: fit inside max_width × max_height.
    - Never enlarge an image beyond its original dimensions.
    """
    if original_width <= 0 or original_height <= 0:
        raise ValueError("Invalid image dimensions")

    max_width = max(0, int(max_width))
    max_height = max(0, int(max_height))

    if max_width == 0 and max_height == 0:
        return original_width, original_height

    if max_width > 0 and max_height == 0:
        scale = min(1.0, max_width / original_width)
    elif max_height > 0 and max_width == 0:
        scale = min(1.0, max_height / original_height)
    else:
        scale = min(1.0, max_width / original_width, max_height / original_height)

    width = max(1, round(original_width * scale))
    height = max(1, round(original_height * scale))
    return width, height


def _format_for(source: Path, selected: str) -> str:
    if selected in ("webp", "jpeg", "png"):
        return selected

    suffix = source.suffix.lower()
    if suffix == ".png":
        return "png"
    if suffix in (".jpg", ".jpeg"):
        return "jpeg"
    if suffix == ".webp":
        return "webp"
    return "webp"


def _extension_for(fmt: str) -> str:
    return ".jpg" if fmt == "jpeg" else f".{fmt}"


def _unique_output_path(
    source: Path,
    output_dir: Path,
    fmt: str,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    base = f"{source.stem}-compressed"
    candidate = output_dir / f"{base}{_extension_for(fmt)}"
    if not candidate.exists():
        return candidate

    counter = 2
    while True:
        candidate = output_dir / f"{base}-{counter}{_extension_for(fmt)}"
        if not candidate.exists():
            return candidate
        counter += 1


def _flatten_for_jpeg(image: Image.Image) -> Image.Image:
    """JPEG has no alpha channel; composite transparent pixels over white."""
    if image.mode in ("RGBA", "LA") or (
        image.mode == "P" and "transparency" in image.info
    ):
        if image.mode == "P":
            image = image.convert("RGBA")
        background = Image.new("RGB", image.size, "white")
        alpha = image.getchannel("A") if "A" in image.getbands() else None
        background.paste(image.convert("RGB"), mask=alpha)
        return background
    if image.mode != "RGB":
        return image.convert("RGB")
    return image


def compress_image(
    source: Path,
    settings: CompressionSettings,
) -> CompressionResult:
    """Compress an image and return the result without propagating errors."""
    source = source.expanduser()
    original_bytes = source.stat().st_size if source.exists() else 0
    original_size: tuple[int, int] = (0, 0)
    output: Path | None = None

    try:
        with Image.open(source) as opened:
            opened.load()
            image = ImageOps.exif_transpose(opened)
            original_size = image.size

            new_width, new_height = target_dimensions(
                image.width,
                image.height,
                settings.max_width,
                settings.max_height,
            )
            if (new_width, new_height) != image.size:
                image = image.resize(
                    (new_width, new_height),
                    Image.Resampling.LANCZOS,
                )

            fmt = _format_for(source, settings.output_format)
            quality = max(1, min(100, int(settings.quality)))
            output_dir = (
                settings.output_dir.expanduser()
                if settings.output_dir is not None
                else source.parent
            )
            output = _unique_output_path(source, output_dir, fmt)

            if fmt == "jpeg":
                image = _flatten_for_jpeg(image)
                image.save(
                    output,
                    "JPEG",
                    quality=quality,
                    optimize=True,
                    progressive=True,
                )
            elif fmt == "webp":
                if image.mode not in ("RGB", "RGBA"):
                    image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
                image.save(
                    output,
                    "WEBP",
                    quality=quality,
                    method=4,
                )
            elif fmt == "png":
                if image.mode == "P":
                    image = image.convert("RGBA")
                image.save(
                    output,
                    "PNG",
                    optimize=True,
                    compress_level=9,
                )
            else:
                raise ValueError(f"Unsupported output format: {fmt}")

        output_bytes = output.stat().st_size
        with Image.open(output) as saved:
            output_size = saved.size

        return CompressionResult(
            source=source,
            output=output,
            original_bytes=original_bytes,
            output_bytes=output_bytes,
            original_size=original_size,
            output_size=output_size,
        )

    except Exception as exc:
        # Invalid file, permissions, codec, or dimensions.
        return CompressionResult(
            source=source,
            output=output if output and output.exists() else None,
            original_bytes=original_bytes,
            output_bytes=0,
            original_size=original_size,
            output_size=(0, 0),
            error=str(exc) or exc.__class__.__name__,
        )


def compress_images(
    sources: Iterable[Path],
    settings: CompressionSettings,
) -> list[CompressionResult]:
    """Compress multiple images sequentially for CLI use or tests."""
    return [compress_image(Path(source), settings) for source in sources]
