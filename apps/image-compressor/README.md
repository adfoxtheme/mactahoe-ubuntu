# Image Compressor

A GTK4/Libadwaita application for compressing one or more images with a Mac-style dark interface.

## Features

- Select multiple images or drag and drop them into the window.
- Supports **PNG, JPG/JPEG, and WebP** input.
- Export as **WebP, JPEG, or PNG**, or keep the original format.
- Set maximum width and height:
  - Both values `0`: keep the original dimensions.
  - One value `0`: use the other as a limit and calculate dimensions proportionally.
  - Both values greater than `0`: fit within the limits while preserving aspect ratio.
  - Images are never enlarged beyond their original dimensions.
- Adjust quality for JPG/WebP; PNG compression is lossless.
- Creates new output names and never overwrites the original image.
- Shows dimensions and file sizes before and after compression.
- Works offline; images are processed locally and never uploaded.

## Run

```bash
cd "$HOME/mactahoe-ubuntu/apps/image-compressor"
python3 app.py
```

Or launch **Image Compressor** from GNOME or run:

```bash
image-compressor
```

## Files

- `app.py` — GTK4 interface.
- `compressor.py` — image processing with Pillow.
- `style.css` — application styling.
- `assets/vn.ihoan.ImageCompressor.svg` — application icon.
- `test_compressor.py` — format, dimensions, alpha, and batch tests.

## Test

```bash
cd "$HOME/mactahoe-ubuntu/apps/image-compressor"
python3 -m unittest -v test_compressor.py
```

## Notes

- Images are processed sequentially in a background thread so the interface remains responsive.
- JPEG does not support alpha; transparent PNG/WebP pixels are placed on a white background when exported as JPEG.
- Animated WebP currently processes only its first frame.
- The default output folder is `~/Pictures/Ảnh đã nén`.
