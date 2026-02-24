"""
Detect potentially watermarked, blank, or duplicate images
among the 5 primary WebP files per era.

Flags:
  - DARK:   mean brightness < 60  (likely black watermark background)
  - TINY:   file size < 5KB       (placeholder / failed download)
  - DUP:    identical file size as another era's same-numbered image
  - FLAT:   pixel std-dev < 15    (very low-detail / solid colour)
"""
import os
from pathlib import Path
from PIL import Image, ImageStat
from collections import defaultdict

ASSETS = Path(__file__).parent / "assets"
WEBP_NAMES = [f"{n:06d}.webp" for n in range(1, 6)]

results = []
size_map = defaultdict(list)  # size_bytes -> list of (era, filename)

for era_dir in sorted(ASSETS.iterdir()):
    if not era_dir.is_dir() or era_dir.name == "thumbs":
        continue
    for fname in WEBP_NAMES:
        fpath = era_dir / fname
        if not fpath.exists():
            results.append((era_dir.name, fname, ["MISSING"], 0, 0, 0))
            continue

        size_bytes = fpath.stat().st_size
        size_map[size_bytes].append((era_dir.name, fname))

        with Image.open(fpath) as img:
            img_rgb = img.convert("RGB")
            stat = ImageStat.Stat(img_rgb)
            mean_brightness = sum(stat.mean) / 3
            std_dev = sum(stat.stddev) / 3

        flags = []
        if mean_brightness < 60:
            flags.append("DARK")
        if size_bytes < 5_000:
            flags.append("TINY")
        if std_dev < 15:
            flags.append("FLAT")

        results.append((era_dir.name, fname, flags, size_bytes, round(mean_brightness, 1), round(std_dev, 1)))

# Find duplicates (same file size across eras)
dup_sizes = {sz: paths for sz, paths in size_map.items() if len(paths) > 1}

print("=" * 70)
print("IMAGE AUDIT REPORT")
print("=" * 70)

issues = [r for r in results if r[2]]
clean  = [r for r in results if not r[2]]

print(f"\nTotal images checked : {len(results)}")
print(f"Issues flagged       : {len(issues)}")
print(f"Clean                : {len(clean)}")

if issues:
    print("\n--- FLAGGED IMAGES ---")
    for era, fname, flags, size, brightness, std in issues:
        flag_str = " | ".join(flags)
        print(f"  [{flag_str}]  {era}/{fname}")
        print(f"           size={size//1024}KB  brightness={brightness}/255  std={std}")

if dup_sizes:
    print("\n--- POTENTIAL DUPLICATES (identical file size) ---")
    for sz, paths in sorted(dup_sizes.items()):
        print(f"  {sz//1024}KB:")
        for era, fname in paths:
            print(f"    {era}/{fname}")

print("\n--- ALL RESULTS ---")
for era, fname, flags, size, brightness, std in results:
    flag_str = (" [" + " ".join(flags) + "]") if flags else ""
    print(f"  {era}/{fname}  {size//1024}KB  br={brightness}  std={std}{flag_str}")
