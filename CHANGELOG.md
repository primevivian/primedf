# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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

[Unreleased]: https://github.com/primevivian/primedf/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/primevivian/primedf/releases/tag/v0.1.0
