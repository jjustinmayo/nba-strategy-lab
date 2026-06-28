# Python Notes (for review)

Personal learning notes on the Python written for this project. Anchored to the
real scripts (`config.py`, `ingest_team_stats.py`) so the concepts stay concrete.

---

## 0. The meta-skill: how to read any Python script

Read **outside-in**, not line 1 → line N:

1. **Top docstring** (`"""..."""`) — what is this file's job? (one file = one job)
2. **Imports** — what does it depend on? This is the file's "vocabulary."
3. **`main()` first** — it's the table of contents (the flow: `fetch → land → check`).
4. **Then each function top-down** — now read bodies for the *how*.

> Habit: docstring → imports → `main` → details. You'll grasp ~80% before reading any hard line.

---

## 1. `config.py` concepts

```python
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent
DB_PATH = PROJECT_ROOT / "nba_strategy.db"
```

- **`pathlib.Path`** — modern path handling. Don't glue strings with `\` (breaks across OSes); use `Path` objects.
- **`/` operator is overloaded** on Paths to mean "join path parts": `PROJECT_ROOT / "nba_strategy.db"`.
- **`__file__`** — built-in: this script's own path. `.resolve()` = absolute, `.parent` = its folder.
  - Net effect: paths anchored to the file, not to the current working directory. The #1 fix for "works on my machine" path bugs.
- The whole file is just **constants, no logic** — that's "config over hardcoding" made concrete.

---

## 2. `ingest_team_stats.py` concepts

### Imports & dependency story
```python
import sqlite3                              # stdlib, no install, talks to SQLite
from datetime import datetime, timezone
from nba_api.stats.endpoints import leaguedashteamstats
from config import DB_PATH, SEASON, SEASON_TYPE
```
- `import X` → whole module, call `X.thing()`.
- `from X import Y` → pull one name out, call `Y()` directly (use for things you call a lot).

### Functions & type hints
```python
def fetch_team_stats(season: str, season_type: str) -> tuple[list[str], list[list]]:
```
- **`def`** defines a function.
- **Type hints** (`season: str`, `-> tuple[...]`) don't enforce anything at runtime — they're free *documentation* of the data's shape, and your editor uses them to catch mistakes.

### The core data structure (the heart of it)
```python
result_set = endpoint.get_dict()["resultSets"][0]
headers = result_set["headers"]   # ['TEAM_ID', 'TEAM_NAME', ...]
rows    = result_set["rowSet"]    # [[1610612760, 'OKC', 82, 64, ...], [...], ...]
```
- API returns a **dict** (key→value). `["resultSets"]` looks up a key; `[0]` grabs first list item.
- `headers` = list of column names. `rows` = **list of lists** (each inner list = one team's row, same order as headers).
- **Mental model:** "list of rows + a parallel list of column names" = what a DB table, a CSV, and a pandas DataFrame all are underneath.

### List comprehension
```python
enriched_rows = [list(row) + [season, ingested_at] for row in rows]
```
- Read it as: "for each `row` in `rows`, build `list(row) + [season, ingested_at]`, collect into a new list."
- Longhand equivalent:
  ```python
  enriched_rows = []
  for row in rows:
      enriched_rows.append(list(row) + [season, ingested_at])
  ```
- We tack the two lineage values onto the end of every row. Comprehensions are everywhere in data work.

### SQLite pattern: parameterized queries + idempotency
```python
placeholders = ", ".join("?" for _ in all_columns)
conn.executemany(
    f"INSERT INTO {RAW_TABLE} ({col_list}) VALUES ({placeholders})",
    enriched_rows,
)
```
- **`?` placeholders**: NEVER paste data values into SQL strings. Pass `?` and hand values separately — prevents SQL injection and quoting bugs. (Column *names* are f-string'd in because identifiers can't be parameterized; *values* always go through `?`.)
- **`executemany`** runs the same INSERT once per row in one efficient batch.
- **Idempotency** = `DELETE FROM ... WHERE season = ?` before inserting → re-running is safe (clears this season's old rows first, so counts never double).

### try / finally
```python
conn = sqlite3.connect(DB_PATH)
try:
    ...
finally:
    conn.close()
```
- **`finally` runs no matter what** (even on a crash) → always closes the DB connection, never leaks one.
- Slicker version uses `with` (a "context manager") — left out for now to keep the mechanics visible. (Future refactor lesson.)

### The `__main__` guard
```python
if __name__ == "__main__":
    main()
```
- "Run `main()` only if this file is executed directly (`python ingest_team_stats.py`), not if it's *imported*."
- Lets a file be both a runnable script and an importable module. You'll see it in nearly every Python script.

---

## 3. Syntax cheat-sheet

| Syntax | Means |
|---|---|
| `from x import y` | pull name `y` out of module `x` |
| `def f(a: str) -> int:` | function `f`, takes a string, returns an int (hints) |
| `f"...{var}..."` | f-string: embed `var`'s value into text |
| `d["key"]`, `lst[0]` | look up a dict key / list index |
| `[expr for x in items]` | list comprehension (loop that builds a list) |
| `try: ... finally: ...` | run cleanup no matter what happens |
| `if __name__ == "__main__":` | "run only when executed directly" |

---

## 4. Habits for learning Python *for data engineering*

1. **Always know the "shape" of your data at each step.** Ask: dict? list of rows? single value?
   Printing shapes/counts between stages (`print(f"{len(rows)} rows, {len(headers)} cols")`) is the #1 debugging habit.
2. **Trace one row end-to-end.** Follow OKC: list in `rowSet` → +season/ingested_at → row in `raw_team_stats` → back out in the sanity check.
3. **Use the Python REPL.** With the venv active: run `python`, import things, poke at `.get_dict()` live.
4. **Read stdlib docs for the few modules you actually use** (`sqlite3`, `pathlib`, `datetime`) over broad tutorials.

---

## 5. Project-specific gotcha: Smart App Control blocks pandas

- This machine has Windows **Smart App Control enforced**, which blocked pandas' compiled DLL
  (`ImportError: ... An Application Control policy has blocked this file`).
- `numpy` imported fine; only pandas' binary was flagged.
- **Fix:** ingestion uses the stdlib `sqlite3` + the API's raw `get_dict()` — **no pandas**. Also a better
  fit for "land raw as-is" (no DataFrame layer reinterpreting values). Revisit pandas if/when the
  dashboard phase truly needs it.
