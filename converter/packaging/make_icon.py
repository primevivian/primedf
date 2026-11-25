"""Render the PrimeDF mascot for packaging.

Usage:
    python make_icon.py [--ico OUT.ico] [--preview OUT.png] [--app-icon OUT.png]

--ico       multi-size Windows icon (PNG-compressed entries) for the .exe
--preview   256x256 PNG for humans and CI previews
--app-icon  38x38 PNG used as icon.png inside the calculator's .hpappdir
"""

import argparse
import struct
from pathlib import Path

from primedf.icon import icon_png

ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)
APP_ICON_SIZE = 38


def write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    print(f"wrote {path} ({len(data)} bytes)")


def make_ico() -> bytes:
    images = [icon_png(s, supersample=3 if s > 64 else 4) for s in ICO_SIZES]
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = len(header) + 16 * len(images)
    entries = b""
    for size, data in zip(ICO_SIZES, images, strict=True):
        dim = 0 if size >= 256 else size  # 0 means 256 in ICO entries
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    return header + entries + b"".join(images)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ico", type=Path)
    p.add_argument("--preview", type=Path)
    p.add_argument("--app-icon", type=Path)
    a = p.parse_args()
    if a.ico:
        write(a.ico, make_ico())
    if a.preview:
        write(a.preview, icon_png(256, supersample=3))
    if a.app_icon:
        write(a.app_icon, icon_png(APP_ICON_SIZE, supersample=6))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
