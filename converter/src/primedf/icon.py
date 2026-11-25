"""The PrimeDF mascot: a tiny smiling calculator, drawn procedurally.

Used for the window icon and, through ``packaging/make_icon.py``, for the
Windows .exe icon. Drawing it in code keeps binary assets out of the repo.
"""

from __future__ import annotations

from .png import PNG_RGBA, encode_png

Color = tuple[int, int, int]

PINK: Color = (255, 143, 171)
PINK_RIM: Color = (232, 96, 140)
SCREEN: Color = (255, 246, 236)
INK: Color = (62, 50, 72)
BLUSH: Color = (255, 190, 206)
KEY: Color = (255, 255, 255)
KEY_ACCENT: Color = (178, 160, 255)


def _in_rrect(u: float, v: float, x0: float, y0: float, x1: float, y1: float,
              r: float) -> bool:
    if u < x0 or u > x1 or v < y0 or v > y1:
        return False
    cx = min(max(u, x0 + r), x1 - r)
    cy = min(max(v, y0 + r), y1 - r)
    return (u - cx) ** 2 + (v - cy) ** 2 <= r * r


def _color_at(u: float, v: float) -> Color | None:
    """Color of the mascot at normalized coordinates (0..1), None = clear."""
    if not _in_rrect(u, v, 0.16, 0.05, 0.84, 0.95, 0.14):
        return None
    if _in_rrect(u, v, 0.25, 0.13, 0.75, 0.43, 0.06):  # screen with a face
        for ex in (0.40, 0.60):
            if (u - ex) ** 2 + (v - 0.25) ** 2 <= 0.036**2:
                return INK
        d = ((u - 0.5) ** 2 + (v - 0.27) ** 2) ** 0.5
        if 0.066 <= d <= 0.094 and v > 0.305:
            return INK
        for bx in (0.32, 0.68):
            if ((u - bx) / 0.04) ** 2 + ((v - 0.335) / 0.022) ** 2 <= 1:
                return BLUSH
        return SCREEN
    for i, kx in enumerate((0.335, 0.5, 0.665)):
        for j, ky in enumerate((0.56, 0.69, 0.82)):
            if (u - kx) ** 2 + (v - ky) ** 2 <= 0.05**2:
                return KEY_ACCENT if (i, j) == (2, 2) else KEY
    if not _in_rrect(u, v, 0.185, 0.075, 0.815, 0.925, 0.115):
        return PINK_RIM
    return PINK


def icon_rows(size: int, supersample: int = 4) -> list[bytes]:
    """RGBA rows of the mascot at ``size`` x ``size``, anti-aliased."""
    ss = supersample
    n = ss * ss
    rows = []
    for y in range(size):
        row = bytearray()
        for x in range(size):
            r = g = b = hits = 0
            for sy in range(ss):
                for sx in range(ss):
                    c = _color_at((x + (sx + 0.5) / ss) / size, (y + (sy + 0.5) / ss) / size)
                    if c is not None:
                        r += c[0]
                        g += c[1]
                        b += c[2]
                        hits += 1
            if hits:
                row += bytes((r // hits, g // hits, b // hits, 255 * hits // n))
            else:
                row += b"\x00\x00\x00\x00"
        rows.append(bytes(row))
    return rows


def icon_png(size: int, supersample: int = 4) -> bytes:
    return encode_png(icon_rows(size, supersample), size, size, PNG_RGBA)
