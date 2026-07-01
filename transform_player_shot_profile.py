"""
Transform: raw player shot locations -> mart_player_shot_profile (shot-mix %s).

One script, one job: read the AS-IS zone-level shot counts already landed in
raw_player_shot_locations and compute each zone's share of total field-goal
attempts (shot mix) plus its FG% (already provided by the API, carried
through). This script never touches the API and never writes back to
raw_player_shot_locations — it only reads raw and writes mart.

Mirrors transform_team_shot_profile.py exactly (same ZONES list, same
corner_3 exclusion — see that file's docstring for the full rationale) but
keyed on player_id/player_name instead of team_id/team_name. team_id/
team_abbreviation are carried through too, since a player's shot profile is
only meaningful alongside which team they played for.

A player with 0 total field goal attempts across all zones divides by zero
in the pct_of_fga calculation — SQLite returns NULL for division by zero
rather than raising an error, so these rows land with NULL percentages
instead of the script crashing.

Idempotent: re-running for the same season replaces that season's rows in
mart_player_shot_profile instead of piling up duplicates.

Run it (with the venv active, after running ingest_player_shot_locations.py) as:
    python transform_player_shot_profile.py
"""
import sqlite3

from config import DB_PATH, SEASON

RAW_TABLE = "raw_player_shot_locations"
MART_TABLE = "mart_player_shot_profile"

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
        "PLAYER_ID"          AS player_id,
        "PLAYER_NAME"        AS player_name,
        "TEAM_ID"            AS team_id,
        "TEAM_ABBREVIATION"  AS team_abbreviation,
        ({_total_fga_expr}) AS total_fga,
        {", ".join(_zone_columns)},
        ? AS season
    FROM {RAW_TABLE}
    WHERE season = ?
"""

_mart_columns = ["player_id", "player_name", "team_id", "team_abbreviation", "total_fga"]
for zone in ZONES:
    _mart_columns += [f"{zone}_fga", f"{zone}_pct_of_fga", f"{zone}_fg_pct"]
_mart_columns.append("season")

_column_defs = [
    "player_id INTEGER",
    "player_name TEXT",
    "team_id INTEGER",
    "team_abbreviation TEXT",
    "total_fga INTEGER",
]
for zone in ZONES:
    _column_defs += [
        f"{zone}_fga INTEGER",
        f"{zone}_pct_of_fga REAL",
        f"{zone}_fg_pct REAL",
    ]
_column_defs.append("season TEXT")


def run_transform(season: str) -> None:
    """Compute shot-mix percentages from raw_player_shot_locations and write them to mart_player_shot_profile."""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            f"CREATE TABLE IF NOT EXISTS {MART_TABLE} ({', '.join(_column_defs)})"
        )

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
    """Basic post-transform validation: row count + a spot-check of a few players."""
    conn = sqlite3.connect(DB_PATH)
    try:
        count = conn.execute(
            f"SELECT COUNT(*) FROM {MART_TABLE} WHERE season = ?", (season,)
        ).fetchone()[0]
        print(f"\nSanity check for {season}:")
        print(f"  Row count: {count}")

        cursor = conn.execute(
            f"""
            SELECT player_name, above_the_break_3_pct_of_fga, restricted_area_pct_of_fga, mid_range_pct_of_fga
            FROM {MART_TABLE}
            WHERE season = ? AND total_fga > 0
            ORDER BY above_the_break_3_pct_of_fga DESC
            LIMIT 5
            """,
            (season,),
        )
        print("  Top 5 players by above-the-break-3 share of FGA:")
        print(f"    {'PLAYER_NAME':<24}{'ABOVE_BREAK_3_%':>17}{'RIM_%':>9}{'MID_RANGE_%':>13}")
        for player_name, above_break_pct, rim_pct, mid_pct in cursor.fetchall():
            print(f"    {player_name:<24}{above_break_pct:>17}{rim_pct:>9}{mid_pct:>13}")

        zero_fga = conn.execute(
            f"SELECT COUNT(*) FROM {MART_TABLE} WHERE season = ? AND total_fga = 0", (season,)
        ).fetchone()[0]
        print(f"  Players with 0 total FGA (NULL pct_of_fga expected): {zero_fga}")
    finally:
        conn.close()


def main() -> None:
    run_transform(SEASON)
    sanity_check(SEASON)
    print("\nDone.")


if __name__ == "__main__":
    main()
