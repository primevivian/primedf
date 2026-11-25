"""Smoke-test a built executable by converting a generated PDF.

Usage: python smoke_test.py EXE [ARGS...]

Runs ``EXE ARGS... <generated.pdf>`` and checks that the pages land in a
folder named after the PDF. Examples::

    python smoke_test.py dist/primedf                      # CLI build
    python smoke_test.py dist/PrimeDF.exe --cli            # windowed build, CLI mode
    python smoke_test.py dist/PrimeDF.exe --gui-selftest   # windowed build, real window
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import pymupdf


def main() -> int:
    exe = Path(sys.argv[1]).resolve()
    extra = sys.argv[2:]
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        pdf = tmp_path / "Smoke Test.pdf"
        doc = pymupdf.open()
        for i in range(3):
            doc.new_page().insert_text((72, 100), f"Smoke test page {i + 1}", fontsize=14)
        doc.save(pdf)
        doc.close()

        proc = subprocess.run([str(exe), *extra, str(pdf)], timeout=180)
        pages = sorted(p.name for p in (tmp_path / "Smoke Test").glob("*.png"))
        expected = [f"Smoke_Test.00{i}.png" for i in (1, 2, 3)]
        if proc.returncode != 0 or pages != expected:
            print(f"FAILED: exit code {proc.returncode}, output {pages}", file=sys.stderr)
            return 1
    print(f"smoke test passed: {exe.name} {' '.join(extra)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
