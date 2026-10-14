#!/usr/bin/env python3
"""
Iterate through ~/Downloads/Liga, and for every Excel file:
  1. In column "division": "0 18" -> "0-18", "19 54" -> "19-54"
  2. Collect (username, name) pairs from columns "username" and "name"
Then print (and save) the unique username + name pairs.

Requires: pip install openpyxl
Note: .xls (old format) is not supported by openpyxl - convert to .xlsx first.
"""

import csv
import re
import shutil
from pathlib import Path

from openpyxl import load_workbook

FOLDER = Path.home() / "Downloads" / "Jahodna DG Liga"
BACKUP = True  # keep a copy of each original in Liga/backup before editing

# Map of values to replace (spaces of any kind, incl. non-breaking, are normalised)
REPLACEMENTS = {
    "HCP18": "0-18",
    "HCP54": "19-54",
}


def norm(value) -> str:
    """Collapse any whitespace (incl. non-breaking spaces) to a single space."""
    return re.sub(r"\s+", " ", str(value)).strip()


def find_columns(ws, wanted):
    """Find wanted header names (case-insensitive) in the first row."""
    found = {}
    for cell in ws[1]:
        if cell.value is None:
            continue
        key = norm(cell.value).lower()
        if key in wanted:
            found[key] = cell.column
    return found


def main():
    if not FOLDER.is_dir():
        raise SystemExit(f"Folder not found: {FOLDER}")

    files = sorted(
        p for p in FOLDER.iterdir()
        if p.suffix.lower() in (".xlsx", ".xlsm") and not p.name.startswith("~$")
    )
    if not files:
        raise SystemExit(f"No Excel files found in {FOLDER}")

    if BACKUP:
        (FOLDER / "backup").mkdir(exist_ok=True)

    pairs = set()  # unique (username, name) combinations
    total_changes = 0

    for path in files:
        if BACKUP:
            shutil.copy2(path, FOLDER / "backup" / path.name)

        wb = load_workbook(path, keep_vba=path.suffix.lower() == ".xlsm")
        file_changes = 0

        for ws in wb.worksheets:
            cols = find_columns(ws, {"division", "username", "name"})

            # 1) Fix division values
            if "division" in cols:
                for row in range(2, ws.max_row + 1):
                    cell = ws.cell(row=row, column=cols["division"])
                    if cell.value is None:
                        continue
                    new = REPLACEMENTS.get(norm(cell.value))
                    if new is not None:
                        cell.value = new
                        file_changes += 1

            # # 2) Collect (username, name) pairs, row by row
            # if "username" in cols and "name" in cols:
            #     for row in range(2, ws.max_row + 1):
            #         u = ws.cell(row=row, column=cols["username"]).value
            #         n = ws.cell(row=row, column=cols["name"]).value
            #         u = norm(u) if u is not None else ""
            #         n = norm(n) if n is not None else ""
            #         if u or n:
            #             pairs.add((u, n))

        if file_changes:
            wb.save(path)
        wb.close()
        total_changes += file_changes
        print(f"{path.name}: {file_changes} division value(s) changed")

    print(f"\nTotal changes: {total_changes}")

    sorted_pairs = sorted(pairs, key=lambda p: (p[0].casefold(), p[1].casefold()))

    print(f"=== Unique username + name pairs ({len(sorted_pairs)}) ===")
    for u, n in sorted_pairs:
        print(f"{u}\t{n}")

    out = FOLDER / "unique_pairs.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig opens cleanly in Excel
        writer = csv.writer(f)
        writer.writerow(["username", "name"])
        writer.writerows(sorted_pairs)
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()