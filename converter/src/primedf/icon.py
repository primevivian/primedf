"""The PrimeDF icon: an HP Prime G2-style calculator showing a PDF page.

Used for the window icon and, through ``packaging/make_icon.py``, for the
Windows .exe icon. Drawing it in code keeps binary assets out of the repo.
It's a generic likeness of the device and carries no logos or trademarks.
"""

from __future__ import annotations

from .png import PNG_RGBA, encode_png

Color = tuple[int, int, int]

BODY: Color = (38, 40, 45)
RIM: Color = (150, 156, 166)
BEZEL: Color = (12, 12, 14)
SCREEN_BAR: Color = (52, 84, 150)
SCREEN_BG: Color = (214, 224, 238)
PAGE: Color = (255, 255, 255)
PAGE_TEXT: Color = (150, 156, 170)
PAGE_TITLE: Color = (255, 126, 166)  # the converter's accent color
DPAD: Color = (196, 200, 208)
DPAD_CENTER: Color = (120, 124, 134)
KEY_DARK: Color = (74, 77, 84)
KEY_LIGHT: Color = (226, 228, 233)
KEY_BLUE: Color = (70, 130, 220)
KEY_ORANGE: Color = (240, 150, 60)

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
    if v < 0.13:
        return SCREEN_BAR  # the Prime's title bar
    if 0.33 <= u <= 0.67 and 0.15 <= v <= 0.39:  # a document page
        if 0.37 <= u <= 0.55 and 0.18 <= v <= 0.205:
            return PAGE_TITLE
        for i, ly in enumerate((0.235, 0.27, 0.305, 0.34)):
            if 0.37 <= u <= (0.57 if i == 3 else 0.63) and ly <= v <= ly + 0.015:
                return PAGE_TEXT
        return PAGE
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
