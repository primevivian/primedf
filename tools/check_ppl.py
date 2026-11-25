#!/usr/bin/env python3
"""Static checks for HP PPL source files.

There is no PPL compiler outside the calculator/Connectivity Kit, so CI
catches the mistakes that are easy to make when editing on a PC:

Structure
* unbalanced blocks (BEGIN/IF/WHILE/FOR/CASE/IFERR ... END, REPEAT ... UNTIL)
* a missing app entry point (START() or Symb())
* a function defined twice

Proven on hardware (docs/HARDWARE_NOTES.md):
* a function parameter named "i" is a syntax error: i is the imaginary unit
  (test 8, editor Check pointed at it). "e" is treated the same as a precaution.
* more than 8 names in one LOCAL statement: the 9th was a syntax error
  (step 2d, Check pointed at it; test 4 used "ok" as a 4th name and booted).
* "a!=b" is NOT a not-equal test in PPL. It parses as a! = b (factorial),
  compiles, passes the editor's Check, and crashes at run time on strings,
  silently and past IFERR. For not-equal use "<>", "≠" or NOT(a==b)
  (all verified, test 7).

Precautions (not proven either way yet):
* no forward declarations: define every function before it is called
* no "ELSE IF" on one line: write ELSE, then a nested IF ... END
* no LOCAL variables named like app variables F0-F9 (apps are based on Function)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

OPENERS = {"BEGIN", "IF", "WHILE", "FOR", "CASE", "IFERR"}
TOKEN = re.compile(r'"(?:[^"\\]|\\.)*"|//[^\n]*|[A-Za-z_][A-Za-z0-9_]*|\n')
FUNC_HEAD = re.compile(r"^(?:EXPORT\s+)?([A-Za-z_][A-Za-z0-9_]*)\(([^)]*)\)\s*(;)?\s*$")
CALL = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")
APP_VARS = re.compile(r"^[Ff][0-9]$")


def _code(line: str) -> str:
    """The line without its // comment and with string contents blanked."""
    out, in_str = [], False
    i = 0
    while i < len(line):
        ch = line[i]
        if not in_str and line.startswith("//", i):
            break
        if ch == '"':
            in_str = not in_str
            out.append(ch)
        else:
            out.append(" " if in_str else ch)
        i += 1
    return "".join(out)


def check(path: Path) -> list[str]:
    src = path.read_text(encoding="utf-8")
    lines = src.splitlines()
    errors: list[str] = []

    # ---- block balance (token based, strings/comments skipped)
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

    # ---- functions: definitions, forward declarations
    defined: dict[str, int] = {}
    for i, raw in enumerate(lines, start=1):
        if raw[:1].isspace():  # declarations/definitions start at column 0
            continue
        text = _code(raw).strip()
        m = FUNC_HEAD.match(text)
        if not m or m.group(1).upper() in OPENERS | {"END", "RETURN", "LOCAL"}:
            continue
        name, is_decl = m.group(1), bool(m.group(3))
        for param in (p.strip() for p in m.group(2).split(",")):
            if param in ("i", "e"):
                errors.append(f"{path}:{i}: parameter named '{param}' is a syntax error "
                              "(i is the imaginary unit; e is likely the same); rename it")
        if is_decl:
            errors.append(f"{path}:{i}: forward declaration of {name}(); "
                          "define functions before use instead")
            continue
        nxt = next((ln.strip() for ln in lines[i:] if ln.strip()), "")
        if _code(nxt).strip() == "BEGIN":
            if name in defined:
                errors.append(f"{path}:{i}: {name}() defined twice")
            defined[name] = i
    if not {"START", "Symb"} & defined.keys():
        errors.append(f"{path}: app program has no entry point (START() or Symb())")

    # ---- per-line rules
    for i, raw in enumerate(lines, start=1):
        code = _code(raw)
        stripped = code.strip()
        if not stripped or "check_ppl: ignore" in raw:  # hardware tests probe bad code on purpose
            continue
        if "!=" in code:
            errors.append(f"{path}:{i}: != is not not-equal in PPL (it reads as a! = b); "
                          "use <> instead")
        if re.search(r"\bELSE\s+IF\b", code):
            errors.append(f"{path}:{i}: ELSE IF on one line; use ELSE + nested IF ... END")
        lm = re.match(r"\s*LOCAL\s+(.*?);?\s*$", code)
        if lm:
            names = lm.group(1).split(",")
            if len(names) > 8:
                errors.append(f"{path}:{i}: {len(names)} names in one LOCAL; a 9th name was a "
                              "syntax error on hardware, keep it to 8")
            for decl in names:
                var = decl.split(":=")[0].strip()
                if APP_VARS.match(var):
                    errors.append(f"{path}:{i}: LOCAL {var} clashes with app variable "
                                  f"{var.upper()}")
        if raw[:1].isspace():  # inside a function body: calls must be defined above
            for cm in CALL.finditer(code):
                callee = cm.group(1)
                if callee in defined and defined[callee] > i:
                    errors.append(f"{path}:{i}: {callee}() is used before it is defined "
                                  f"(line {defined[callee]})")
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
