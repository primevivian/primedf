# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed

- **Calculator app rebuilt step by step, each step tested on an HP Prime G2.**
  The 0.2.0 program never got past the Function screens on hardware.
  - Step 1 (verified): a boot-test app (`calculator/tests/boot.hpppl`) proved
    that the package, the icon and `START()` work.
  - Step 2: a pink file menu listing the app's PNG files (up/down, Enter,
    Esc), and a page view that fits the page to the screen.
  - Root cause found by single-feature hardware tests (`docs/HARDWARE_NOTES.md`):
    **`a != b` isn't not-equal in PPL.** It reads as `a! = b`, compiles,
    passes Check, and crashes at run time on strings, silently and past
    `IFERR`, leaving you on the Function screen.
- `tools/check_ppl.py` rejects `!=` (proven broken) and, until verified,
  `<>`/`≠`. It also keeps the precautions: no forward declarations, no
  `ELSE IF`, and no locals named like app variables.

## [0.2.0] - 2026-11-25 [WITHDRAWN]

The release was withdrawn: its calculator program didn't start on real
hardware. The converter and app-package work below carried over.

### Added

- **Converter window**: a small, friendly tkinter app. Drop PDFs
  (or folders) into it, or click to choose files. It has a progress bar, a
  "Sharper zoom" option and an "Open folder" button. On Windows, PDFs can also
  be dropped onto the `.exe` icon.
- Standalone executables on GitHub Releases, so you don't need Python. The
  Windows build is the windowed `PrimeDF-windows-x64.exe`. Linux and macOS get command-line builds.
- The CLI accepts folders, and opens the window when run without arguments.
- **Drag-and-drop calculator install**: `PrimeDF.hpappdir.zip`, an app package
  for Connectivity Kit with the program and a 38×38 pink HP Prime icon
  (`icon.png`). It's built in CI from an exported template and the current
  program.
- `docs/HPAPPDIR_FORMAT.md`: a reverse-engineered reference for HP Prime app
  packages, with real exports in `docs/format-samples/`.
  `tools/hpprime_tlv.py` inspects, checks and builds them. CI proves the
  writer by rebuilding a real Connectivity Kit export byte for byte.
- The mascot: a pink HP Prime G2 with a happy face, used for the window,
  the `.exe` and the calculator app.
- Build workflow that smoke-tests each binary (including a real window run on
  Windows) and attaches the binaries, `PrimeDF.hpappdir.zip` and
  `PrimeDF.hpppl` to tagged releases.

### Changed

- Rendering engine switched from PyMuPDF to PDFium (pypdfium2), and Pillow
  replaced by a built-in PNG encoder. The executable shrinks from ~111 MB to
  ~15 MB.
- Pages of `My Book.pdf` now go to a `My Book` folder next to the PDF.
- Python 3.10+ is required to run from source.

## [0.1.0] - 2026-11-25

### Added

- PrimeDF calculator app (`calculator/PrimeDF.hpppl`):
  - file menu built from the app's files, using the native `CHOOSE` menu
  - d-pad panning (tap to step, hold to scroll with acceleration)
  - <kbd>+</kbd>/<kbd>−</kbd> zoom, and <kbd>LN</kbd>/<kbd>LOG</kbd> for the previous/next page
  - one-finger drag, pinch zoom, and double-tap to reset the zoom
  - three-page GROB cache with idle prefetch of neighbor pages
  - page and zoom indicator
- `primedf` converter: PDF to cropped grayscale PNG pages at one scale for the
  whole document, with `--width`, `--no-trim`, `--rgb`, `--name` and `--password`
  options.
- Documentation, tests, and a CI workflow.

[Unreleased]: https://github.com/primevivian/primedf/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/primevivian/primedf/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/primevivian/primedf/releases/tag/v0.1.0
