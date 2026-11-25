"""Command-line interface.

Typical uses::

    primedf book.pdf notes.pdf          # pages go to ./primedf_out next to each PDF
    primedf book.pdf -o D:/calc/out     # explicit output folder
    primedf                             # no arguments: pick PDFs in a file dialog

The standalone executable is also meant to be used without a terminal.
Drag PDFs onto ``primedf.exe``, or double-click it to choose files. In
that case the window stays open at the end and the output folder opens
in Explorer.
"""

from __future__ import annotations

import argparse
import os
import sys
import traceback
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .convert import DEFAULT_WIDTH, ConversionError, convert_pdf

OUT_DIR_NAME = "primedf_out"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="primedf",
        description="Convert PDF files into page images for the PrimeDF "
        "reader app on the HP Prime G2. With no PDF arguments a file "
        "picker opens.",
    )
    p.add_argument("pdfs", nargs="*", type=Path, metavar="PDF",
                   help="PDF file(s) to convert")
    p.add_argument("-o", "--out", type=Path, default=None,
                   help=f"output folder (default: {OUT_DIR_NAME} next to each PDF)")
    p.add_argument("-n", "--name",
                   help="document name shown on the calculator "
                   "(single input only; default: the file name)")
    p.add_argument("-w", "--width", type=int, default=DEFAULT_WIDTH,
                   help=f"page content width in pixels (default: {DEFAULT_WIDTH}; "
                   "larger = sharper zoom, bigger files)")
    p.add_argument("--no-trim", action="store_true",
                   help="keep the page margins instead of cropping to content")
    p.add_argument("--rgb", action="store_true",
                   help="write color PNGs instead of grayscale")
    p.add_argument("--password", help="password for encrypted PDFs")
    p.add_argument("-q", "--quiet", action="store_true", help="only print errors")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def owns_console() -> bool:
    """True when we were launched from Explorer (double-click or drag-and-drop).

    In that case Windows created a console just for us. It vanishes when
    we exit, so the caller should pause before closing.
    """
    if sys.platform != "win32":
        return False
    try:
        import ctypes

        procs = (ctypes.c_uint * 8)()
        count = ctypes.windll.kernel32.GetConsoleProcessList(procs, 8)
    except Exception:
        return False
    # A PyInstaller one-file build runs as a bootloader plus a child process.
    return 0 < count <= (2 if getattr(sys, "frozen", False) else 1)


def pick_pdfs() -> list[Path]:
    """Ask for PDF files with a native file dialog. Returns [] if unavailable."""
    try:
        import tkinter
        from tkinter import filedialog

        root = tkinter.Tk()
    except Exception:
        return []
    try:
        root.withdraw()
        root.attributes("-topmost", True)
        names = filedialog.askopenfilenames(
            parent=root,
            title="PrimeDF - choose PDF files to convert",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
    finally:
        root.destroy()
    return [Path(n) for n in names]


def open_folder(path: Path) -> None:
    try:
        os.startfile(path)  # type: ignore[attr-defined]  # Windows only
    except Exception:
        pass


def run(argv: Sequence[str] | None, standalone: bool) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    pdfs: list[Path] = list(args.pdfs) or pick_pdfs()
    if not pdfs:
        parser.print_help()
        return 2
    if args.name and len(pdfs) > 1:
        print("primedf: --name only works with a single input file", file=sys.stderr)
        return 2

    failures = 0
    out_dirs: list[Path] = []
    for pdf in pdfs:
        out_dir = args.out if args.out is not None else pdf.parent / OUT_DIR_NAME

        def progress(done: int, total: int, _pdf: Path = pdf) -> None:
            if not args.quiet:
                print(f"\r{_pdf.name}: page {done}/{total}", end="", flush=True)

        try:
            result = convert_pdf(
                pdf, out_dir, name=args.name, width=args.width,
                trim=not args.no_trim, rgb=args.rgb, password=args.password,
                progress=progress,
            )
        except ConversionError as exc:
            if not args.quiet:
                print()
            print(f"primedf: {exc}", file=sys.stderr)
            failures += 1
            continue
        if out_dir not in out_dirs:
            out_dirs.append(out_dir)
        if not args.quiet:
            print(f"\r{pdf.name}: {result.pages} pages -> "
                  f"{out_dir / (result.name + '.*.png')} "
                  f"({result.total_bytes / 1024:.0f} KiB)")

    if out_dirs and not args.quiet:
        print("\nNext: drag the .png files onto the PrimeDF app in HP Connectivity Kit.")
    if standalone:
        for d in out_dirs:
            open_folder(d)
    return 1 if failures else 0


def main(argv: Sequence[str] | None = None) -> int:
    standalone = owns_console()
    try:
        return run(argv, standalone)
    except SystemExit as exc:  # argparse --help / usage errors
        return exc.code if isinstance(exc.code, int) else 0
    except Exception:
        traceback.print_exc()
        return 1
    finally:
        if standalone:
            try:
                input("\nPress Enter to close...")
            except EOFError:
                pass


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
