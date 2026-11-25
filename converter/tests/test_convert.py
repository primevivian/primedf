from pathlib import Path

import pymupdf  # test-only: used to generate input PDFs
import pypdfium2 as pdfium
import pytest

from primedf.cli import main
from primedf.convert import (
    SCAN_SCALE,
    ConversionError,
    content_box,
    convert_pdf,
    default_output_dir,
    find_pdfs,
    page_filename,
    render,
    sanitize_name,
)
from primedf.icon import icon_png
from primedf.png import PNG_GRAY, PNG_RGB, PNG_RGBA, encode_png, read_png_header


def make_pdf(path: Path, pages: int = 3, text_at=(200, 300)) -> Path:
    doc = pymupdf.open()
    for i in range(pages):
        page = doc.new_page(width=612, height=792)  # US Letter
        page.insert_text(text_at, f"Page {i + 1} of the test document", fontsize=12)
        page.draw_rect(pymupdf.Rect(150, 400, 450, 500), color=(0, 0, 0), width=1)
    doc.save(path)
    doc.close()
    return path


def png_info(path: Path) -> tuple[int, int, int]:
    return read_png_header(path.read_bytes())


# ------------------------------------------------------------------ naming
@pytest.mark.parametrize(
    "stem, expected",
    [
        ("My Thesis v2.final", "My_Thesis_v2_fin"),  # cut to 16 chars
        ("Notes v2.1", "Notes_v2_1"),
        ("   ", "doc"),
        ("résumé", "r_sum"),
        ("a" * 40, "a" * 16),
        ("chapter__3__", "chapter_3"),
    ],
)
def test_sanitize_name(stem, expected):
    assert sanitize_name(stem) == expected


def test_page_filename():
    assert page_filename("book", 1) == "book.001.png"
    assert page_filename("book", 999) == "book.999.png"
    with pytest.raises(ValueError):
        page_filename("book", 0)
    with pytest.raises(ValueError):
        page_filename("book", 1000)


def test_default_output_dir_is_named_after_pdf(tmp_path):
    assert default_output_dir(tmp_path / "My Book.pdf") == tmp_path / "My Book"


def test_find_pdfs_expands_folders_and_dedupes(tmp_path):
    a = make_pdf(tmp_path / "a.pdf", pages=1)
    b = make_pdf(tmp_path / "B.PDF", pages=1)
    (tmp_path / "notes.txt").write_text("x")
    found = find_pdfs([tmp_path, a, tmp_path / "notes.txt"])
    assert sorted(found) == sorted([a, b])


# --------------------------------------------------------------------- png
def test_png_encoder_roundtrip_header():
    rows = [bytes([0, 128, 255]), bytes([255, 128, 0])]
    data = encode_png(rows, 3, 2, PNG_GRAY)
    assert read_png_header(data) == (3, 2, PNG_GRAY)
    with pytest.raises(ValueError):
        encode_png(rows, 4, 2, PNG_GRAY)


def test_icon_is_valid_rgba_png():
    assert read_png_header(icon_png(32)) == (32, 32, PNG_RGBA)


# ----------------------------------------------------------------- raster
def test_content_box_finds_ink(tmp_path):
    pdf = pdfium.PdfDocument(str(make_pdf(tmp_path / "a.pdf", pages=1)))
    try:
        box = content_box(render(pdf[0], SCAN_SCALE))
    finally:
        pdf.close()
    assert box is not None
    x0, y0, x1, y1 = box
    # ink spans roughly x 150..450, y ~290..500 (plus padding)
    assert 130 <= x0 <= 155
    assert 445 <= x1 <= 470
    assert 270 <= y0 <= 300
    assert 495 <= y1 <= 520


def test_content_box_blank_page(tmp_path):
    doc = pymupdf.open()
    doc.new_page()
    doc.save(tmp_path / "blank.pdf")
    doc.close()
    pdf = pdfium.PdfDocument(str(tmp_path / "blank.pdf"))
    try:
        assert content_box(render(pdf[0], SCAN_SCALE)) is None
    finally:
        pdf.close()


# ----------------------------------------------------------------- convert
def test_convert_writes_grayscale_pages_next_to_pdf(tmp_path):
    pdf = make_pdf(tmp_path / "Sample Doc.pdf", pages=3)
    result = convert_pdf(pdf, width=320)
    out = tmp_path / "Sample Doc"
    assert result.out_dir == out
    assert result.name == "Sample_Doc"
    assert result.pages == 3
    names = sorted(p.name for p in out.iterdir())
    assert names == ["Sample_Doc.001.png", "Sample_Doc.002.png", "Sample_Doc.003.png"]
    w, _h, color = png_info(out / names[0])
    assert color == PNG_GRAY
    assert abs(w - 320) <= 2  # content width fitted to --width


def test_convert_no_trim_keeps_page_aspect(tmp_path):
    pdf = make_pdf(tmp_path / "x.pdf", pages=1)
    convert_pdf(pdf, tmp_path / "o", width=306, trim=False, rgb=True)
    w, h, color = png_info(tmp_path / "o" / "x.001.png")
    assert color == PNG_RGB
    assert abs(w - 306) <= 1 and abs(h - 396) <= 1


def test_reconvert_removes_stale_pages(tmp_path):
    convert_pdf(make_pdf(tmp_path / "d.pdf", pages=3), tmp_path / "o")
    convert_pdf(make_pdf(tmp_path / "d.pdf", pages=1), tmp_path / "o")
    assert sorted(p.name for p in (tmp_path / "o").iterdir()) == ["d.001.png"]


def test_bad_input_raises(tmp_path):
    bogus = tmp_path / "nope.pdf"
    bogus.write_bytes(b"not a pdf")
    with pytest.raises(ConversionError):
        convert_pdf(bogus, tmp_path / "o")


def test_output_path_that_is_a_file_raises(tmp_path):
    pdf = make_pdf(tmp_path / "book.pdf", pages=1)
    (tmp_path / "book").write_text("in the way")
    with pytest.raises(ConversionError):
        convert_pdf(pdf)


# --------------------------------------------------------------------- cli
def test_cli_end_to_end(tmp_path):
    pdf = make_pdf(tmp_path / "cli.pdf", pages=2)
    out = tmp_path / "out"
    assert main([str(pdf), "-o", str(out), "-n", "Manual", "-q"]) == 0
    assert sorted(p.name for p in out.iterdir()) == ["Manual.001.png", "Manual.002.png"]


def test_cli_rejects_name_with_multiple_inputs(tmp_path):
    a = make_pdf(tmp_path / "a.pdf", pages=1)
    b = make_pdf(tmp_path / "b.pdf", pages=1)
    assert main([str(a), str(b), "-n", "X"]) == 2


def test_cli_default_output_is_named_after_each_pdf(tmp_path):
    a = make_pdf(tmp_path / "Alpha Book.pdf", pages=1)
    b = make_pdf(tmp_path / "beta.pdf", pages=2)
    assert main([str(a), str(b), "-q"]) == 0
    assert [p.name for p in (tmp_path / "Alpha Book").iterdir()] == ["Alpha_Book.001.png"]
    assert sorted(p.name for p in (tmp_path / "beta").iterdir()) == [
        "beta.001.png", "beta.002.png",
    ]


def test_cli_accepts_a_folder(tmp_path):
    make_pdf(tmp_path / "one.pdf", pages=1)
    make_pdf(tmp_path / "two.pdf", pages=1)
    assert main([str(tmp_path), "-q"]) == 0
    assert (tmp_path / "one" / "one.001.png").exists()
    assert (tmp_path / "two" / "two.001.png").exists()


def test_cli_no_pdfs_found(tmp_path):
    (tmp_path / "readme.txt").write_text("x")
    assert main([str(tmp_path)]) == 2


def test_cli_help_exits_cleanly(capsys):
    assert main(["--help"]) == 0
    assert "PDF" in capsys.readouterr().out
