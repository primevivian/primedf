from pathlib import Path

import pymupdf
import pytest
from PIL import Image

from primedf.cli import main
from primedf.convert import (
    ConversionError,
    content_box,
    convert_pdf,
    page_filename,
    sanitize_name,
)


def make_pdf(path: Path, pages: int = 3, text_at=(200, 300)) -> Path:
    doc = pymupdf.open()
    for i in range(pages):
        page = doc.new_page(width=612, height=792)  # US Letter
        page.insert_text(text_at, f"Page {i + 1} of the test document", fontsize=12)
        page.draw_rect(pymupdf.Rect(150, 400, 450, 500), color=(0, 0, 0), width=1)
    doc.save(path)
    doc.close()
    return path


@pytest.mark.parametrize(
    "stem, expected",
    [
        ("My Thesis v2.final", "My_Thesis_v2_final"),
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


def test_content_box_finds_ink(tmp_path):
    with pymupdf.open(make_pdf(tmp_path / "a.pdf", pages=1)) as doc:
        box = content_box(doc[0])
    assert box is not None
    # ink spans roughly x 150..450, y ~290..500 (plus padding)
    assert 130 <= box.x0 <= 155
    assert 445 <= box.x1 <= 470
    assert 270 <= box.y0 <= 300
    assert 495 <= box.y1 <= 520


def test_content_box_blank_page(tmp_path):
    doc = pymupdf.open()
    doc.new_page()
    assert content_box(doc[0]) is None
    doc.close()


def test_convert_writes_grayscale_pages(tmp_path):
    pdf = make_pdf(tmp_path / "Sample Doc.pdf", pages=3)
    out = tmp_path / "out"
    result = convert_pdf(pdf, out, width=320)
    assert result.name == "Sample_Doc"
    assert result.pages == 3
    names = sorted(p.name for p in out.iterdir())
    assert names == ["Sample_Doc.001.png", "Sample_Doc.002.png", "Sample_Doc.003.png"]
    with Image.open(out / names[0]) as img:
        assert img.mode == "L"
        assert abs(img.width - 320) <= 2  # content width fitted to --width


def test_convert_no_trim_keeps_page_aspect(tmp_path):
    pdf = make_pdf(tmp_path / "x.pdf", pages=1)
    convert_pdf(pdf, tmp_path, width=306, trim=False, rgb=True)
    with Image.open(tmp_path / "x.001.png") as img:
        assert img.mode == "RGB"
        assert img.size == (306, 396)


def test_reconvert_removes_stale_pages(tmp_path):
    convert_pdf(make_pdf(tmp_path / "d.pdf", pages=3), tmp_path / "o")
    convert_pdf(make_pdf(tmp_path / "d.pdf", pages=1), tmp_path / "o")
    assert sorted(p.name for p in (tmp_path / "o").iterdir()) == ["d.001.png"]


def test_bad_input_raises(tmp_path):
    bogus = tmp_path / "nope.pdf"
    bogus.write_bytes(b"not a pdf")
    with pytest.raises(ConversionError):
        convert_pdf(bogus, tmp_path / "o")


def test_cli_end_to_end(tmp_path):
    pdf = make_pdf(tmp_path / "cli.pdf", pages=2)
    out = tmp_path / "out"
    assert main([str(pdf), "-o", str(out), "-n", "Manual", "-q"]) == 0
    assert sorted(p.name for p in out.iterdir()) == ["Manual.001.png", "Manual.002.png"]


def test_cli_rejects_name_with_multiple_inputs(tmp_path):
    a = make_pdf(tmp_path / "a.pdf", pages=1)
    b = make_pdf(tmp_path / "b.pdf", pages=1)
    assert main([str(a), str(b), "-n", "X"]) == 2
