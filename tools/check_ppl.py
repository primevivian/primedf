#!/usr/bin/env python3
"""Lightweight static checks for HP PPL source files.

There is no PPL compiler outside the calculator/Connectivity Kit, so CI
catches the mistakes that are easy to make when editing on a PC:

* unbalanced blocks (BEGIN/IF/WHILE/FOR/CASE/IFERR ... END, REPEAT ... UNTIL)
* forward declarations without a matching definition (and vice versa)
* a missing entry point (START() or Symb()) for an app program
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

OPENERS = {"BEGIN", "IF", "WHILE", "FOR", "CASE", "IFERR"}
TOKEN = re.compile(r'"(?:[^"\\]|\\.)*"|//[^\n]*|[A-Za-z_][A-Za-z0-9_]*|\n')
FUNC_HEAD = re.compile(r"^(?:EXPORT\s+)?([A-Za-z_][A-Za-z0-9_]*)\(([^)]*)\)\s*(;)?\s*$")


def check(path: Path) -> list[str]:
    src = path.read_text(encoding="utf-8")
    errors: list[str] = []

    stack: list[tuple[str, int]] = []
    line = 1
    for m in TOKEN.finditer(src):
        tok = m.group(0)
        if tok == "\n":
            line += 1
            continue
        if tok.startswith(('"', "//")):
            continue
        if tok in OPENERS or tok == "REPEAT":
            stack.append((tok, line))
        elif tok == "END":
            if not stack or stack[-1][0] == "REPEAT":
                errors.append(f"{path}:{line}: END without an open block")
            else:
                stack.pop()
        elif tok == "UNTIL":
            if not stack or stack[-1][0] != "REPEAT":
                errors.append(f"{path}:{line}: UNTIL without REPEAT")
            else:
                stack.pop()
    for tok, ln in stack:
        errors.append(f"{path}:{ln}: {tok} is never closed")

    declared: dict[str, int] = {}
    defined: dict[str, int] = {}
    lines = src.splitlines()
    for i, raw in enumerate(lines, start=1):
        if raw[:1].isspace():  # declarations/definitions start at column 0
            continue
        text = raw.split("//", 1)[0].strip()
        m = FUNC_HEAD.match(text)
        if not m or m.group(1).upper() in OPENERS | {"END", "RETURN"}:
            continue
        name, is_decl = m.group(1), bool(m.group(3))
        if is_decl:
            declared[name] = i
        else:
            nxt = next((ln.strip() for ln in lines[i:] if ln.strip()), "")
            if nxt.split("//", 1)[0].strip() == "BEGIN":
                if name in defined:
                    errors.append(f"{path}:{i}: {name}() defined twice")
                defined[name] = i
    for name, ln in declared.items():
        if name not in defined:
            errors.append(f"{path}:{ln}: {name}() declared but never defined")
    if not {"START", "Symb"} & defined.keys():
        errors.append(f"{path}: app program has no entry point (START() or Symb())")
    return errors


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: check_ppl.py FILE.hpppl [...]", file=sys.stderr)
        return 2
    errors = [e for f in argv[1:] for e in check(Path(f))]
    for e in errors:
        print(e)
    if not errors:
        print("PPL checks passed")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
