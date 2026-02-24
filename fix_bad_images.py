"""
Fix known-bad (dark/watermarked/duplicate) WebP images by promoting
better images from later positions within the same era.
Also regenerates thumbs/ for any replaced positions.

Swaps performed (all positions are 1-indexed):
  Era 03 (Middle Ages):        pos 3 is dark → overwrite with pos 4
  Era 06 (Victorian):          pos 1,2 dark  → overwrite with pos 3,4
  Era 08 (1920s Flapper):      pos 2 dark    → overwrite with pos 3
  Era 09 (1940s/New Look):     pos 1,2,3 are
                                era-06 duplicates → overwrite with pos 4,5,4
  Era 12 (21st Century):       pos 2 tiny/flat → overwrite with pos 3
"""
import shutil
from pathlib import Path
from PIL import Image

ASSETS = Path(__file__).parent / "assets"
THUMB_MAX = 380
THUMB_QUALITY = 75

# (era_folder, dest_position, source_position)
SWAPS = [
    ("03_the_middle_ages",                        3, 4),
    ("06_victorian_era_crinolines",               1, 3),
    ("06_victorian_era_crinolines",               2, 4),
    ("08_1920s_flapper",                          2, 3),
    ("09_1940s_rationing_and_new_look",           1, 4),
    ("09_1940s_rationing_and_new_look",           2, 5),
    ("09_1940s_rationing_and_new_look",           3, 4),
    ("12_21st_century_and_gender_neutrality",     2, 3),
]


def stem(n: int) -> str:
    return f"{n:06d}"


def regen_thumb(full_path: Path, thumb_path: Path) -> None:
    thumb_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(full_path) as img:
        img = img.convert("RGB")
        img.thumbnail((THUMB_MAX, THUMB_MAX * 2), Image.LANCZOS)
        img.save(thumb_path, "WEBP", quality=THUMB_QUALITY, method=6)


for era_name, dest_n, src_n in SWAPS:
    era_dir = ASSETS / era_name
    src_full  = era_dir / f"{stem(src_n)}.webp"
    dest_full = era_dir / f"{stem(dest_n)}.webp"
    dest_thumb = era_dir / "thumbs" / f"{stem(dest_n)}.webp"

    if not src_full.exists():
        print(f"  SKIP  {era_name}: source {src_full.name} missing")
        continue

    # Copy full WebP
    shutil.copy2(src_full, dest_full)
    # Regenerate thumbnail from the full WebP
    regen_thumb(dest_full, dest_thumb)

    src_kb  = src_full.stat().st_size // 1024
    dest_kb = dest_full.stat().st_size // 1024
    print(f"  FIXED  {era_name}/{stem(dest_n)}.webp  ← {stem(src_n)}.webp  ({src_kb}KB)")

print("\nDone.")
