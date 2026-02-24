"""
Convert the first 5 images of each era folder to WebP.

Outputs:
  assets/<era>/000001.webp  (full, max 1000px wide, quality 82)
  assets/<era>/thumbs/000001.webp  (thumbnail, max 380px wide, quality 75)
"""
import os
import sys
from pathlib import Path
from PIL import Image

ASSETS_DIR = Path(__file__).parent / "assets"
FULL_MAX = 1000       # px — longest edge cap for full image
THUMB_MAX = 380       # px — longest edge cap for thumbnail
FULL_QUALITY = 82
THUMB_QUALITY = 75
IMAGES_PER_ERA = 5    # only convert 000001–000005


def convert(src: Path, dest: Path, max_px: int, quality: int) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as img:
        img = img.convert("RGB")
        img.thumbnail((max_px, max_px * 2), Image.LANCZOS)
        img.save(dest, "WEBP", quality=quality, method=6)
    orig_kb = src.stat().st_size // 1024
    new_kb = dest.stat().st_size // 1024
    print(f"  {src.name} → {dest.relative_to(ASSETS_DIR.parent)}  ({orig_kb}KB → {new_kb}KB)")


def find_source(folder: Path, n: int) -> Path | None:
    """Return the source image path for image number n (tries .jpg then .jpeg)."""
    stem = f"{n:06d}"
    for ext in ("jpg", "jpeg", "png"):
        candidate = folder / f"{stem}.{ext}"
        if candidate.exists():
            return candidate
    return None


total_converted = 0
total_skipped = 0

for era_dir in sorted(ASSETS_DIR.iterdir()):
    if not era_dir.is_dir():
        continue
    print(f"\n[{era_dir.name}]")
    thumbs_dir = era_dir / "thumbs"

    for n in range(1, IMAGES_PER_ERA + 1):
        src = find_source(era_dir, n)
        if src is None:
            print(f"  {n:06d}: NOT FOUND — skipping")
            total_skipped += 1
            continue

        full_dest = era_dir / f"{n:06d}.webp"
        thumb_dest = thumbs_dir / f"{n:06d}.webp"

        try:
            convert(src, full_dest, FULL_MAX, FULL_QUALITY)
            convert(src, thumb_dest, THUMB_MAX, THUMB_QUALITY)
            total_converted += 1
        except Exception as e:
            print(f"  ERROR on {src}: {e}", file=sys.stderr)
            total_skipped += 1

print(f"\nDone. Converted: {total_converted}  Skipped/errored: {total_skipped}")
