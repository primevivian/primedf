"""Smoke-test a built ``primedf`` executable: convert a generated PDF.

Usage: python smoke_test.py path/to/primedf[.exe]
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import pymupdf


def main() -> int:
    exe = Path(sys.argv[1]).resolve()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        pdf = tmp_path / "Smoke Test.pdf"
        doc = pymupdf.open()
        for i in range(3):
            doc.new_page().insert_text((72, 100), f"Smoke test page {i + 1}", fontsize=14)
        doc.save(pdf)
        doc.close()

        version = subprocess.run([exe, "--version"], capture_output=True, text=True, check=True)
        print(version.stdout.strip())
        subprocess.run([exe, str(pdf)], check=True, timeout=120)

        pages = sorted(p.name for p in (tmp_path / "primedf_out").glob("*.png"))
        expected = [f"Smoke_Test.00{i}.png" for i in (1, 2, 3)]
        if pages != expected:
            print(f"unexpected output: {pages}", file=sys.stderr)
            return 1
    print("smoke test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
