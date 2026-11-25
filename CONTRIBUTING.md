# Contributing to PrimeDF

Thanks for helping. PrimeDF is meant to stay small, so before you work on a new
feature, please open an issue to discuss it.

## Most wanted: hardware reports

If you run PrimeDF on a real calculator, please open an issue with:

- the model (G1/G2) and firmware version (*Help → About*),
- what worked and what didn't (menu, page load, pan, zoom, pinch, double-tap),
- how long a page takes to load, and the converter `-w` you used.

## Calculator program (`calculator/PrimeDF.hpppl`)

- Plain HP PPL, in a single file, with no external libraries.
- Program-level names start with `pd` so they can't collide with built-ins or
  user variables. PPL command names aren't case-sensitive.
- Don't use `STRING()` for numbers. Its output depends on the user's number
  format, so use `IToS()` instead.
- Test in the HP Prime Virtual Calculator and on hardware if you can.

## Converter (`converter/`)

```sh
cd converter
pip install -e ".[dev]"
ruff check .
pytest
```

CI runs the same checks on every push and pull request.

## Commits and pull requests

- Keep each pull request focused, and describe how you tested it.
- Update `CHANGELOG.md` under *Unreleased*.
