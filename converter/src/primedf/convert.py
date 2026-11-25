"""Rasterize PDF pages into PrimeDF page images for the HP Prime.

Pages are rendered with PDFium (via pypdfium2), the PDF engine inside
Chrome, which ships as a single small native library. Each page is
cropped to its content box (unless trimming is disabled) and rendered at
one scale for the whole document, so text size stays constant between
pages. The result is a grayscale PNG named ``<doc>.<NNN>.png``. The HP
Prime decodes PNG natively, which is far faster than anything a PPL
program could do with a raw PDF.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

import pypdfium2 as pdfium

from .png import PNG_GRAY, PNG_RGB, encode_png

MAX_PAGES = 999
MAX_NAME_LEN = 16
DEFAULT_WIDTH = 640
SHARP_WIDTH = 960
WHITE_THRESHOLD = 245  # gray values at or above this count as paper
SCAN_SCALE = 0.5  # resolution of the content-box scan (36 dpi)
TRIM_PADDING = 6.0  # points of white kept around the content box

_LUT = bytes(0 if v >= WHITE_THRESHOLD else 1 for v in range(256))

Box = tuple[float, float, float, float]  # x0, y0, x1, y1 in points, top-left origin


class ConversionError(Exception):
    """Raised when a document cannot be converted."""


@dataclass(frozen=True)
class ConvertedDocument:
    name: str
    pages: int
    files: list[Path]
    total_bytes: int
    out_dir: Path


@dataclass(frozen=True)
class Raster:
    """An 8-bit image as a list of row byte strings (1 or 3 channels)."""

    width: int
    height: int
    channels: int
    rows: list[bytes]


def sanitize_name(stem: str, max_len: int = MAX_NAME_LEN) -> str:
    """Turn a file stem into a short calculator-safe document name.

    Only ASCII letters, digits and underscores survive. Dots are removed
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


def default_output_dir(pdf: Path) -> Path:
    """Pages of ``My Book.pdf`` go to a ``My Book`` folder next to it."""
    return pdf.parent / pdf.stem


def find_pdfs(paths: Iterable[str | Path]) -> list[Path]:
    """Expand files/folders into a de-duplicated list of PDF files."""
    found: list[Path] = []
    for p in map(Path, paths):
        if p.is_dir():
            candidates = sorted(c for c in p.iterdir() if c.is_file())
        else:
            candidates = [p]
        for c in candidates:
            if c.suffix.lower() == ".pdf" and c not in found:
                found.append(c)
    return found


def render(page: pdfium.PdfPage, scale: float, rgb: bool = False) -> Raster:
    """Render ``page`` at ``scale`` (1.0 = 72 dpi) to gray or RGB rows."""
    bitmap = page.render(scale=scale, grayscale=not rgb, rev_byteorder=rgb)
    try:
        w, h = bitmap.width, bitmap.height
        stride, n = bitmap.stride, bitmap.n_channels
        buf = bytes(bitmap.buffer)
    finally:
        bitmap.close()
    if not rgb:
        # Grayscale rendering puts the same value in every channel; take one.
        first = 1 if n >= 3 else 0
        rows = [buf[y * stride + first : y * stride + n * w : n] for y in range(h)]
        return Raster(w, h, 1, rows)
    if n == 3:
        rows = [buf[y * stride : y * stride + 3 * w] for y in range(h)]
    else:  # RGBx / RGBA: drop the 4th byte
        rows = []
        for y in range(h):
            src = buf[y * stride : y * stride + n * w]
            row = bytearray(3 * w)
            row[0::3], row[1::3], row[2::3] = src[0::n], src[1::n], src[2::n]
            rows.append(bytes(row))
    return Raster(w, h, 3, rows)


def content_box(scan: Raster, scale: float = SCAN_SCALE) -> Box | None:
    """Bounding box of non-white pixels of a gray ``scan``, in points.

    Returns None for a blank page.
    """
    top = bottom = -1
    left, right = scan.width, -1
    for y, row in enumerate(scan.rows):
        marked = row.translate(_LUT)
        x0 = marked.find(1)
        if x0 < 0:
            continue
        if top < 0:
            top = y
        bottom = y
        left = min(left, x0)
        right = max(right, marked.rfind(1))
    if top < 0:
        return None
    s = 1.0 / scale
    page_w, page_h = scan.width * s, scan.height * s
    return (
        max(0.0, left * s - TRIM_PADDING),
        max(0.0, top * s - TRIM_PADDING),
        min(page_w, (right + 1) * s + TRIM_PADDING),
        min(page_h, (bottom + 1) * s + TRIM_PADDING),
    )


def _median(values: list[float]) -> float:
    v = sorted(values)
    mid = len(v) // 2
    return v[mid] if len(v) % 2 else (v[mid - 1] + v[mid]) / 2


def _crop(img: Raster, box: Box | None, scale: float) -> Raster:
    if box is None:
        return img
    x0 = max(0, int(box[0] * scale))
    y0 = max(0, int(box[1] * scale))
    x1 = min(img.width, int(round(box[2] * scale)))
    y1 = min(img.height, int(round(box[3] * scale)))
    if x1 <= x0 or y1 <= y0:
        return img
    c = img.channels
    rows = [r[x0 * c : x1 * c] for r in img.rows[y0:y1]]
    return Raster(x1 - x0, y1 - y0, c, rows)


def convert_pdf(
    pdf_path: Path,
    out_dir: Path | None = None,
    *,
    name: str | None = None,
    width: int = DEFAULT_WIDTH,
    trim: bool = True,
    rgb: bool = False,
    password: str | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> ConvertedDocument:
    """Convert ``pdf_path`` into PrimeDF page images inside ``out_dir``.

    ``out_dir`` defaults to a folder named after the PDF, next to it.
    ``width`` is the pixel width the typical page's content is rendered
    at. With 640, text is readable at 2x fit-width on the 320 px screen.
    """
    pdf_path = Path(pdf_path)
    if width < 160 or width > 2000:
        raise ConversionError("width must be between 160 and 2000 pixels")
    out_dir = Path(out_dir) if out_dir is not None else default_output_dir(pdf_path)
    if out_dir.exists() and not out_dir.is_dir():
        raise ConversionError(f"{out_dir} exists and is not a folder; pass another output folder")
    doc_name = sanitize_name(name if name else pdf_path.stem)

    try:
        pdf = pdfium.PdfDocument(str(pdf_path), password=password)
    except (pdfium.PdfiumError, OSError) as exc:
        hint = " (wrong or missing password?)" if "password" in str(exc).lower() else ""
        raise ConversionError(f"cannot open {pdf_path.name}: {exc}{hint}") from exc

    try:
        count = len(pdf)
        if count == 0:
            raise ConversionError(f"{pdf_path.name} has no pages")
        if count > MAX_PAGES:
            raise ConversionError(f"{pdf_path.name} has {count} pages; the limit is {MAX_PAGES}")

        # Pass 1: a cheap low-resolution scan of every page finds content boxes.
        boxes: list[Box | None] = []
        widths: list[float] = []
        for i in range(count):
            page = pdf[i]
            try:
                scan = render(page, SCAN_SCALE)
            finally:
                page.close()
            box = content_box(scan) if trim else None
            boxes.append(box)
            widths.append(box[2] - box[0] if box else scan.width / SCAN_SCALE)

        # One scale for the whole document so text size is stable when
        # turning pages: fit the median content width to `width` px.
        scale = width / max(1.0, _median(widths))

        out_dir.mkdir(parents=True, exist_ok=True)
        for stale in out_dir.glob(f"{doc_name}.[0-9][0-9][0-9].png"):
            stale.unlink()

        # Pass 2: render, crop and encode.
        files: list[Path] = []
        total = 0
        for i in range(count):
            page = pdf[i]
            try:
                img = _crop(render(page, scale, rgb), boxes[i], scale)
            finally:
                page.close()
            data = encode_png(img.rows, img.width, img.height, PNG_RGB if rgb else PNG_GRAY)
            target = out_dir / page_filename(doc_name, i + 1)
            target.write_bytes(data)
            files.append(target)
            total += len(data)
            if progress:
                progress(i + 1, count)
    finally:
        pdf.close()

    return ConvertedDocument(doc_name, len(files), files, total, out_dir)
