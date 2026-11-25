"""Write the PrimeDF icon as a multi-size Windows .ico (PNG-compressed).

Usage: python make_icon.py OUT.ico [PREVIEW.png]
"""

import struct
import sys
from pathlib import Path

from primedf.icon import icon_png

SIZES = (16, 24, 32, 48, 64, 128, 256)


def main() -> int:
    out = Path(sys.argv[1])
    images = [icon_png(s, supersample=3 if s > 64 else 4) for s in SIZES]
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = len(header) + 16 * len(images)
    entries = b""
    for size, data in zip(SIZES, images, strict=True):
        dim = 0 if size >= 256 else size  # 0 means 256 in ICO entries
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(header + entries + b"".join(images))
    print(f"wrote {out} ({out.stat().st_size} bytes)")
    if len(sys.argv) > 2:  # optional large preview for humans
        preview = Path(sys.argv[2])
        preview.parent.mkdir(parents=True, exist_ok=True)
        preview.write_bytes(images[-1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
