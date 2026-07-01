"""
Transform: raw team shot locations -> mart_team_shot_profile (shot-mix %s).

One script, one job: read the AS-IS zone-level shot counts already landed in
raw_team_shot_locations and compute each zone's share of total field-goal
attempts (shot mix) plus its FG% (already provided by the API, carried
through). This script never touches the API and never writes back to
raw_team_shot_locations — it only reads raw and writes mart.

Shot mix is the strategy signal here: two teams can have similar overall FG%
while getting there completely differently (e.g. rim + corner-3-heavy vs.
mid-range-heavy), which is exactly the "what makes each team unique" question
this project is after.

Zones used (the API's Corner 3 zone is dropped from the mix calc since it's
already the sum of Left Corner 3 + Right Corner 3 — including it would
double-count attempts):
  restricted_area, in_the_paint_non_ra, mid_range,
  left_corner_3, right_corner_3, above_the_break_3, backcourt

Idempotent: re-running for the same season replaces that season's rows in
mart_team_shot_profile instead of piling up duplicates, matching the other
transform script's pattern.

Run it (with the venv active, after running ingest_team_shot_locations.py) as:
    python transform_team_shot_profile.py
"""
import sqlite3

from config import DB_PATH, SEASON

RAW_TABLE = "raw_team_shot_locations"
MART_TABLE = "mart_team_shot_profile"

# Zones that partition total FGA with no overlap. "corner_3" is excluded
# because it duplicates left_corner_3 + right_corner_3.
ZONES = [
    "restricted_area",
    "in_the_paint_non_ra",
    "mid_range",
    "left_corner_3",
    "right_corner_3",
    "above_the_break_3",
    "backcourt",
]

_total_fga_expr = " + ".join(f'"{zone}_fga"' for zone in ZONES)

_zone_columns = []
for zone in ZONES:
    _zone_columns.append(f'"{zone}_fga" AS {zone}_fga')
    _zone_columns.append(f'ROUND(100.0 * "{zone}_fga" / ({_total_fga_expr}), 1) AS {zone}_pct_of_fga')
    _zone_columns.append(f'"{zone}_fg_pct" AS {zone}_fg_pct')

TRANSFORM_SQL = f"""
    SELECT
        "TEAM_ID"   AS team_id,
        "TEAM_NAME" AS team_name,
        ({_total_fga_expr}) AS total_fga,
        {", ".join(_zone_columns)},
        ? AS season
    FROM {RAW_TABLE}
    WHERE season = ?
"""

_mart_columns = ["team_id", "team_name", "total_fga"]
for zone in ZONES:
    _mart_columns += [f"{zone}_fga", f"{zone}_pct_of_fga", f"{zone}_fg_pct"]
_mart_columns.append("season")

_column_defs = ["team_id INTEGER", "team_name TEXT", "total_fga INTEGER"]
for zone in ZONES:
    _column_defs += [
        f"{zone}_fga INTEGER",
        f"{zone}_pct_of_fga REAL",
        f"{zone}_fg_pct REAL",
    ]
_column_defs.append("season TEXT")


def run_transform(season: str) -> None:
    """Compute shot-mix percentages from raw_team_shot_locations and write them to mart_team_shot_profile."""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            f"CREATE TABLE IF NOT EXISTS {MART_TABLE} ({', '.join(_column_defs)})"
        )

        # Idempotency: clear this season's existing rows before re-inserting,
        # same pattern as the other transform script.
        deleted = conn.execute(
            f"DELETE FROM {MART_TABLE} WHERE season = ?", (season,)
        ).rowcount
        if deleted:
            print(f"  Removed {deleted} existing rows for {season} (idempotent re-run).")

        rows = conn.execute(TRANSFORM_SQL, (season, season)).fetchall()
        placeholders = ", ".join("?" for _ in _mart_columns)
        conn.executemany(
            f"INSERT INTO {MART_TABLE} ({', '.join(_mart_columns)}) VALUES ({placeholders})",
            rows,
        )
        conn.commit()
        print(f"  Wrote {len(rows)} rows to {MART_TABLE}.")
    finally:
        conn.close()


def sanity_check(season: str) -> None:
    """Basic post-transform validation: row count + a spot-check of a few teams."""
    conn = sqlite3.connect(DB_PATH)
    try:
        count = conn.execute(
            f"SELECT COUNT(*) FROM {MART_TABLE} WHERE season = ?", (season,)
        ).fetchone()[0]
        print(f"\nSanity check for {season}:")
        print(f"  Row count: {count} (expected ~30 teams)")

        cursor = conn.execute(
            f"""
            SELECT team_name, above_the_break_3_pct_of_fga, restricted_area_pct_of_fga, mid_range_pct_of_fga
            FROM {MART_TABLE}
            WHERE season = ?
            ORDER BY above_the_break_3_pct_of_fga DESC
            LIMIT 5
            """,
            (season,),
        )
        print("  Top 5 teams by above-the-break-3 share of FGA:")
        print(f"    {'TEAM_NAME':<24}{'ABOVE_BREAK_3_%':>17}{'RIM_%':>9}{'MID_RANGE_%':>13}")
        for team_name, above_break_pct, rim_pct, mid_pct in cursor.fetchall():
            print(f"    {team_name:<24}{above_break_pct:>17}{rim_pct:>9}{mid_pct:>13}")
    finally:
        conn.close()


def main() -> None:
    run_transform(SEASON)
    sanity_check(SEASON)
    print("\nDone.")


if __name__ == "__main__":
    main()
