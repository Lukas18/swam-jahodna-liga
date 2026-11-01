"""Read uDisc per-round exports without changing league data."""
from collections import Counter
from io import BytesIO
import json
from pathlib import Path
import re

from openpyxl import load_workbook


ROUND_SHEET = re.compile(r"round\s*(\d+)", re.IGNORECASE)
HOLES = tuple(range(1, 19))


def _integer(value, label, *, optional=False):
    if value is None or str(value).strip() == "":
        if optional:
            return None
        raise ValueError(f"{label} is missing")
    try:
        number = int(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{label} must be a whole number: {value!r}") from exc
    if str(value).strip() not in (str(number), f"{number}.0") and not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a whole number: {value!r}")
    return number


def parse_workbook(content):
    """Return complete or partial scorecards from sheets named Round N."""
    workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    sheets = []
    for sheet in workbook.worksheets:
        match = ROUND_SHEET.fullmatch(sheet.title.strip())
        if match:
            sheets.append((int(match.group(1)), sheet))
    if not sheets:
        raise ValueError("No 'Round 1' / 'Round 2' worksheets were found")
    sheets.sort(key=lambda item: item[0])
    numbers = [number for number, _ in sheets]
    if len(set(numbers)) != len(numbers) or numbers != list(range(1, len(numbers) + 1)):
        raise ValueError("Round worksheet numbers must be unique and consecutive, starting at 1")

    rounds = []
    for number, sheet in sheets:
        rows = sheet.iter_rows(values_only=True)
        headers = [str(value).strip().lower() if value is not None else "" for value in next(rows, ())]
        required = {"name", "division", "starting_hole", *[f"hole_{hole}" for hole in HOLES]}
        missing = sorted(required - set(headers))
        if missing:
            raise ValueError(f"{sheet.title}: missing columns: {', '.join(missing)}")
        index = {header: position for position, header in enumerate(headers) if header}
        players = []
        seen = set()
        par_totals = Counter()
        for row_number, values in enumerate(rows, 2):
            if not any(value is not None and str(value).strip() for value in values):
                continue
            def cell(header):
                position = index.get(header)
                return values[position] if position is not None and position < len(values) else None
            name = str(cell("name") or "").strip()
            division = str(cell("division") or "").strip()
            if not name:
                raise ValueError(f"{sheet.title}, row {row_number}: player name is missing")
            identity = str(cell("username") or cell("pdga_number") or f"{division}:{name}").strip().casefold()
            if identity in seen:
                raise ValueError(f"{sheet.title}, row {row_number}: duplicate player {name}")
            seen.add(identity)
            start = _integer(cell("starting_hole"), f"{sheet.title}, row {row_number} starting hole")
            if start not in HOLES:
                raise ValueError(f"{sheet.title}, row {row_number}: starting hole must be 1–18")
            scores = [_integer(cell(f"hole_{hole}"), f"{sheet.title}, row {row_number} hole {hole}", optional=True)
                      for hole in HOLES]
            if any(score is not None and score < 1 for score in scores):
                raise ValueError(f"{sheet.title}, row {row_number}: hole throws must be positive")
            total = _integer(cell("round_total_score"), "round total", optional=True)
            relative = _integer(cell("round_relative_score"), "round relative score", optional=True)
            if all(score is not None for score in scores) and total is not None and sum(scores) != total:
                raise ValueError(f"{sheet.title}, row {row_number}: hole throws do not sum to round total")
            if total is not None and relative is not None:
                par_totals[total - relative] += 1
            players.append({"id": identity, "name": name, "division": division, "start": start,
                            "scores": scores, "total": total, "relative": relative})
        rounds.append({"number": number, "sheet": sheet.title, "players": players,
                       "reported_par_totals": dict(par_totals)})
    return {"rounds": rounds, "divisions": sorted({p["division"] for r in rounds for p in r["players"]}),
            "player_count": len({p["id"] for r in rounds for p in r["players"]})}


def load_layouts(path):
    """Read optional league layout profiles as per-hole par choices."""
    path = Path(path)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    courses = {course["id"]: course["name"] for course in data.get("courses", [])}
    result = []
    for layout in data.get("layouts", []):
        profiles = {}
        for category, holes in layout.get("profiles", {}).items():
            by_number = {int(h["number"]): int(h["par"]) for h in holes}
            if set(by_number) == set(HOLES):
                profiles[category] = [by_number[hole] for hole in HOLES]
        if profiles:
            result.append({"id": layout["id"], "name": f"{courses.get(layout['course_id'], '')} / {layout['name']}",
                           "profiles": profiles})
    return result
