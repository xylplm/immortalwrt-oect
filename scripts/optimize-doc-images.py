#!/usr/bin/env python3
"""Convert documentation PNG images to optimized JPEG files."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


def convert_png_to_jpeg(source: Path, quality: int, remove_original: bool) -> tuple[Path, int, int]:
    target = source.with_suffix(".jpg")
    before = source.stat().st_size

    with Image.open(source) as image:
        if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
            canvas = Image.new("RGB", image.size, "white")
            rgba = image.convert("RGBA")
            canvas.paste(rgba, mask=rgba.getchannel("A"))
            output = canvas
        else:
            output = image.convert("RGB")

        output.save(
            target,
            "JPEG",
            quality=quality,
            optimize=True,
            progressive=True,
            subsampling=0,
        )

    after = target.stat().st_size
    if remove_original:
        source.unlink()

    return target, before, after


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, default=[Path("docs/images")])
    parser.add_argument("--quality", type=int, default=90, help="JPEG quality, 1-95. Default: 90")
    parser.add_argument("--remove-original", action="store_true", help="Delete PNG files after successful conversion")
    args = parser.parse_args()

    if not 1 <= args.quality <= 95:
        parser.error("--quality must be between 1 and 95")

    sources: list[Path] = []
    for path in args.paths:
        if path.is_dir():
            sources.extend(sorted(path.glob("*.png")))
        elif path.suffix.lower() == ".png":
            sources.append(path)

    if not sources:
        print("No PNG images found.")
        return 0

    total_before = 0
    total_after = 0
    for source in sources:
        target, before, after = convert_png_to_jpeg(source, args.quality, args.remove_original)
        total_before += before
        total_after += after
        saved = before - after
        ratio = saved / before * 100 if before else 0
        print(f"{source} -> {target} ({before} -> {after} bytes, saved {ratio:.1f}%)")

    saved = total_before - total_after
    ratio = saved / total_before * 100 if total_before else 0
    print(f"Total: {total_before} -> {total_after} bytes, saved {ratio:.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
