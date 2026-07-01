"""
Transform: raw player clutch stats -> mart_player_clutch (clutch efficiency).

One script, one job: read the AS-IS clutch-situation box-score totals already
landed in raw_player_clutch and compute clutch efficiency metrics into a
separate mart_ table. This script never touches the API and never writes
back to raw_player_clutch — it only reads raw and writes mart.

Reuses transform_team_stats.py's possession-estimator and true-shooting
formulas, applied to clutch-only totals instead of season totals:
  - clutch_poss_est: estimated clutch possessions, using the standard
    estimator FGA - OREB + TOV + 0.4*FTA.
  - clutch_pts_per100: points scored per 100 estimated clutch possessions —
    the clutch-time analog of off_rtg.
  - clutch_ts_pct: true shooting percentage during clutch situations.

Unlike transform_team_stats.py, there is no pace/per-48 metric here: clutch
minutes per player per season are small (often single digits), so a
per-48-minute pace figure isn't a meaningful figure the way it is for
full-season team totals.

A player with 0 clutch FGA/FTA/TOV (0 estimated clutch possessions) divides
by zero in the pts-per-100 formula — SQLite returns NULL for division by
zero rather than raising an error, so these rows land with NULL derived
metrics instead of the script crashing. A player can also have a *negative*
estimated clutch possession count on a small sample (e.g. a clutch offensive
rebound with few/no clutch field-goal attempts) — confirmed on real data (7
of 492 players this season). Dividing PTS by a negative possession count
produces a meaningless negative rate rather than a genuine efficiency
number, so clutch_pts_per100 is NULL whenever clutch_poss_est is not
strictly positive, not just when it's exactly zero. clutch_poss_est itself
is still stored uncapped so the underlying number stays visible. These
players are not filtered out entirely; a future consumer (e.g., a
minimum-clutch-minutes threshold) decides how to handle low-sample players.

Idempotent: re-running for the same season replaces that season's rows in
mart_player_clutch instead of piling up duplicates.

Run it (with the venv active, after running ingest_player_clutch.py) as:
    python transform_player_clutch.py
"""
import sqlite3

from config import DB_PATH, SEASON

RAW_TABLE = "raw_player_clutch"
MART_TABLE = "mart_player_clutch"

TRANSFORM_SQL = f"""
    SELECT
        "PLAYER_ID"          AS player_id,
        "PLAYER_NAME"        AS player_name,
        "TEAM_ID"            AS team_id,
        "TEAM_ABBREVIATION"  AS team_abbreviation,
        "GP"                 AS gp,
        "MIN"                AS clutch_min,
        ("FGA" - "OREB" + "TOV" + 0.4 * "FTA")                             AS clutch_poss_est,
        CASE
            WHEN ("FGA" - "OREB" + "TOV" + 0.4 * "FTA") > 0
                THEN 100.0 * "PTS" / ("FGA" - "OREB" + "TOV" + 0.4 * "FTA")
            ELSE NULL
        END                                                                 AS clutch_pts_per100,
        100.0 * "PTS" / (2.0 * ("FGA" + 0.44 * "FTA"))                     AS clutch_ts_pct,
        ? AS season
    FROM {RAW_TABLE}
    WHERE season = ?
"""


def run_transform(season: str) -> None:
    """Compute clutch efficiency metrics from raw_player_clutch and write them to mart_player_clutch."""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {MART_TABLE} (
                player_id INTEGER,
                player_name TEXT,
                team_id INTEGER,
                team_abbreviation TEXT,
                gp INTEGER,
                clutch_min REAL,
                clutch_poss_est REAL,
                clutch_pts_per100 REAL,
                clutch_ts_pct REAL,
                season TEXT
            )
            """
        )

        deleted = conn.execute(
            f"DELETE FROM {MART_TABLE} WHERE season = ?", (season,)
        ).rowcount
        if deleted:
            print(f"  Removed {deleted} existing rows for {season} (idempotent re-run).")

        rows = conn.execute(TRANSFORM_SQL, (season, season)).fetchall()
        conn.executemany(
            f"""
            INSERT INTO {MART_TABLE}
                (player_id, player_name, team_id, team_abbreviation, gp, clutch_min,
                 clutch_poss_est, clutch_pts_per100, clutch_ts_pct, season)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
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
            SELECT player_name, ROUND(clutch_min, 1), ROUND(clutch_ts_pct, 1), ROUND(clutch_pts_per100, 1)
            FROM {MART_TABLE}
            WHERE season = ? AND clutch_poss_est > 0
            ORDER BY clutch_ts_pct DESC
            LIMIT 5
            """,
            (season,),
        )
        print("  Top 5 players by clutch TS% (min 1 clutch possession):")
        print(f"    {'PLAYER_NAME':<24}{'CLUTCH_MIN':>11}{'CLUTCH_TS%':>11}{'PTS/100':>9}")
        for player_name, clutch_min, ts_pct, pts_per100 in cursor.fetchall():
            print(f"    {player_name:<24}{clutch_min:>11}{ts_pct:>11}{pts_per100:>9}")

        zero_poss = conn.execute(
            f"SELECT COUNT(*) FROM {MART_TABLE} WHERE season = ? AND clutch_poss_est = 0", (season,)
        ).fetchone()[0]
        print(f"  Players with 0 clutch possessions (NULL derived metrics expected): {zero_poss}")
    finally:
        conn.close()


def main() -> None:
    run_transform(SEASON)
    sanity_check(SEASON)
    print("\nDone.")


if __name__ == "__main__":
    main()
