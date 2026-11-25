"""The PrimeDF mascot: a pink HP Prime G2-style calculator with a happy face.

Used for the window icon and, through ``packaging/make_icon.py``, for the
Windows .exe icon. Drawing it in code keeps binary assets out of the repo.
It's a generic likeness of the device and carries no logos or trademarks.
"""

from __future__ import annotations

from .png import PNG_RGBA, encode_png

Color = tuple[int, int, int]

BODY: Color = (255, 143, 171)
RIM: Color = (232, 96, 140)
BEZEL: Color = (122, 52, 88)
SCREEN_BAR: Color = (178, 160, 255)
SCREEN_BG: Color = (255, 246, 236)
INK: Color = (62, 50, 72)
BLUSH: Color = (255, 190, 206)
DPAD: Color = (255, 255, 255)
DPAD_CENTER: Color = (232, 96, 140)
KEY_DARK: Color = (226, 98, 140)
KEY_LIGHT: Color = (255, 255, 255)
KEY_BLUE: Color = (178, 160, 255)  # Shift, pastel
KEY_ORANGE: Color = (255, 196, 140)  # Alpha, pastel

_KEY_W, _KEY_H, _KEY_R = 0.075, 0.045, 0.008
_KEY_COLS = [0.2765 + i * 0.093 for i in range(5)]
_KEY_ROWS = [0.635 + j * 0.062 for j in range(5)]


def _in_rrect(u: float, v: float, x0: float, y0: float, x1: float, y1: float,
              r: float = 0.0) -> bool:
    if u < x0 or u > x1 or v < y0 or v > y1:
        return False
    if r <= 0:
        return True
    cx = min(max(u, x0 + r), x1 - r)
    cy = min(max(v, y0 + r), y1 - r)
    return (u - cx) ** 2 + (v - cy) ** 2 <= r * r


def _screen(u: float, v: float) -> Color:
    if v < 0.125:
        return SCREEN_BAR  # the Prime's title bar
    for ex in (0.42, 0.58):  # eyes
        if (u - ex) ** 2 + (v - 0.225) ** 2 <= 0.03**2:
            return INK
    d = ((u - 0.5) ** 2 + (v - 0.245) ** 2) ** 0.5  # smile
    if 0.058 <= d <= 0.082 and v > 0.275:
        return INK
    for bx in (0.355, 0.645):  # blush
        if ((u - bx) / 0.036) ** 2 + ((v - 0.3) / 0.02) ** 2 <= 1:
            return BLUSH
    return SCREEN_BG


def _color_at(u: float, v: float) -> Color | None:
    """Color of the icon at normalized coordinates (0..1), None = clear."""
    if not _in_rrect(u, v, 0.22, 0.03, 0.78, 0.97, 0.04):
        return None
    if not _in_rrect(u, v, 0.235, 0.045, 0.765, 0.955, 0.03):
        return RIM
    if v < 0.45:  # display
        if _in_rrect(u, v, 0.285, 0.095, 0.715, 0.405, 0.006):
            return _screen(u, v)
        if _in_rrect(u, v, 0.27, 0.08, 0.73, 0.42, 0.012):
            return BEZEL
        return BODY
    if v < 0.61:  # navigation: round d-pad between two pairs of menu keys
        d2 = (u - 0.5) ** 2 + (v - 0.53) ** 2
        if d2 <= 0.058**2:
            return DPAD_CENTER if d2 <= 0.022**2 else DPAD
        for x0, x1 in ((0.27, 0.39), (0.61, 0.73)):
            for y0 in (0.475, 0.545):
                if _in_rrect(u, v, x0, y0, x1, y0 + 0.04, _KEY_R):
                    return KEY_DARK
        return BODY
    for j, ky in enumerate(_KEY_ROWS):  # keypad, 5 x 5
        if ky <= v <= ky + _KEY_H:
            for i, kx in enumerate(_KEY_COLS):
                if _in_rrect(u, v, kx, ky, kx + _KEY_W, ky + _KEY_H, _KEY_R):
                    if (i, j) == (0, 0):
                        return KEY_BLUE
                    if (i, j) == (1, 0):
                        return KEY_ORANGE
                    if j >= 2 and 1 <= i <= 3:
                        return KEY_LIGHT  # number keys
                    return KEY_DARK
    return BODY


def icon_rows(size: int, supersample: int = 4) -> list[bytes]:
    """RGBA rows of the icon at ``size`` x ``size``, anti-aliased."""
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
