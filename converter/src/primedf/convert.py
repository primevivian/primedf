"""Rasterize PDF pages into PrimeDF page images for the HP Prime.

Each page is cropped to its content box (unless trimming is disabled),
rendered at a document-wide scale so text size stays constant between
pages, and saved as a grayscale PNG named ``<doc>.<NNN>.png``. The HP
Prime decodes PNG natively, which is far faster than anything a PPL
program could do with a raw PDF.
"""

from __future__ import annotations

import io
import re
import statistics
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pymupdf
from PIL import Image

MAX_PAGES = 999
MAX_NAME_LEN = 16
DEFAULT_WIDTH = 640
WHITE_THRESHOLD = 245  # gray values at or above this count as paper
SCAN_ZOOM = 0.5  # resolution of the content-box scan (36 dpi)
TRIM_PADDING = 6.0  # points of white kept around the content box

_LUT = bytes(0 if v >= WHITE_THRESHOLD else 1 for v in range(256))


class ConversionError(Exception):
    """Raised when a document cannot be converted."""


@dataclass(frozen=True)
class ConvertedDocument:
    name: str
    pages: int
    files: list[Path]
    total_bytes: int


def sanitize_name(stem: str, max_len: int = MAX_NAME_LEN) -> str:
    """Turn a file stem into a short calculator-safe document name.

    Only ASCII letters, digits and underscores survive; dots are removed
    because the app uses them to split ``<doc>.<NNN>.png``.
    """
    name = re.sub(r"[^A-Za-z0-9]+", "_", stem).strip("_")
    name = name[:max_len].rstrip("_")
    return name or "doc"


def page_filename(doc: str, page: int) -> str:
    """File name the calculator app expects for 1-based ``page``."""
    if not 1 <= page <= MAX_PAGES:
        raise ValueError(f"page must be in 1..{MAX_PAGES}, got {page}")
    return f"{doc}.{page:03d}.png"


def content_box(page: pymupdf.Page) -> pymupdf.Rect | None:
    """Bounding box of non-white pixels, in page.rect coordinates.

    Returns None for a blank page.
    """
    pix = page.get_pixmap(
        matrix=pymupdf.Matrix(SCAN_ZOOM, SCAN_ZOOM),
        colorspace=pymupdf.csGRAY,
        alpha=False,
    )
    w, h, stride = pix.width, pix.height, pix.stride
    marked = pix.samples.translate(_LUT)
    top = bottom = -1
    left, right = w, -1
    for y in range(h):
        row = marked[y * stride : y * stride + w]
        x0 = row.find(1)
        if x0 < 0:
            continue
        if top < 0:
            top = y
        bottom = y
        left = min(left, x0)
        right = max(right, row.rfind(1))
    if top < 0:
        return None
    s = 1.0 / SCAN_ZOOM
    r = page.rect
    box = pymupdf.Rect(left * s, top * s, (right + 1) * s, (bottom + 1) * s)
    box = pymupdf.Rect(
        box.x0 - TRIM_PADDING, box.y0 - TRIM_PADDING,
        box.x1 + TRIM_PADDING, box.y1 + TRIM_PADDING,
    )
    # page.rect is anchored at (0, 0) after rotation; intersect to stay on-page
    return box & pymupdf.Rect(0, 0, r.width, r.height)


def _render_page(page: pymupdf.Page, zoom: float, box: pymupdf.Rect | None,
                 rgb: bool) -> bytes:
    pix = page.get_pixmap(
        matrix=pymupdf.Matrix(zoom, zoom),
        colorspace=pymupdf.csRGB if rgb else pymupdf.csGRAY,
        alpha=False,
    )
    img = Image.frombytes("RGB" if rgb else "L", (pix.width, pix.height), pix.samples)
    if box is not None:
        crop = (
            max(0, int(box.x0 * zoom)),
            max(0, int(box.y0 * zoom)),
            min(pix.width, int(round(box.x1 * zoom))),
            min(pix.height, int(round(box.y1 * zoom))),
        )
        if crop[2] > crop[0] and crop[3] > crop[1]:
            img = img.crop(crop)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def convert_pdf(
    pdf_path: Path,
    out_dir: Path,
    *,
    name: str | None = None,
    width: int = DEFAULT_WIDTH,
    trim: bool = True,
    rgb: bool = False,
    password: str | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> ConvertedDocument:
    """Convert ``pdf_path`` into PrimeDF page images inside ``out_dir``.

    ``width`` is the pixel width the typical page's content is rendered
    at; 640 means text is readable at 2x fit-width on the 320 px screen.
    """
    if width < 160 or width > 2000:
        raise ConversionError("width must be between 160 and 2000 pixels")
    doc_name = sanitize_name(name if name else pdf_path.stem)

    try:
        doc = pymupdf.open(pdf_path)
    except Exception as exc:  # PyMuPDF raises several exception types
        raise ConversionError(f"cannot open {pdf_path}: {exc}") from exc

    with doc:
        if doc.needs_pass and not doc.authenticate(password or ""):
            raise ConversionError(f"{pdf_path} is encrypted; pass --password")
        if doc.page_count == 0:
            raise ConversionError(f"{pdf_path} has no pages")
        if doc.page_count > MAX_PAGES:
            raise ConversionError(
                f"{pdf_path} has {doc.page_count} pages; the limit is {MAX_PAGES}"
            )

        boxes: list[pymupdf.Rect | None] = []
        for page in doc:
            boxes.append(content_box(page) if trim else None)

        # One scale for the whole document so text size is stable when
        # turning pages: fit the median content width to `width` px.
        widths = [
            (b.width if b is not None else page.rect.width)
            for b, page in zip(boxes, doc)
        ]
        zoom = width / max(1.0, statistics.median(widths))

        out_dir.mkdir(parents=True, exist_ok=True)
        for stale in out_dir.glob(f"{doc_name}.[0-9][0-9][0-9].png"):
            stale.unlink()

        files: list[Path] = []
        total = 0
        for i, page in enumerate(doc, start=1):
            data = _render_page(page, zoom, boxes[i - 1], rgb)
            target = out_dir / page_filename(doc_name, i)
            target.write_bytes(data)
            files.append(target)
            total += len(data)
            if progress:
                progress(i, doc.page_count)

    return ConvertedDocument(doc_name, len(files), files, total)
