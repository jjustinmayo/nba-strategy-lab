"""
Transform: raw team stats -> mart_team_stats (derived strategy metrics).

One script, one job: read the AS-IS box-score totals already landed in
raw_team_stats and compute strategy metrics (pace, ratings, efficiency) into
a separate mart_ table. This script never touches the API and never writes
back to raw_team_stats — it only reads raw and writes mart, so re-running it
(or fixing a formula bug here) never requires re-pulling data.

Metric formulas, all derived from team-season TOTALS (not per-game):
  - poss_est: estimated team possessions, using the standard estimator
    FGA - OREB + TOV + 0.4*FTA (approximates true possessions without
    play-by-play data).
  - pace: estimated possessions per 48 minutes of game time.
  - off_rtg: points scored per 100 estimated possessions.
  - net_rtg: PLUS_MINUS (season point differential) per 100 estimated
    possessions, i.e. point differential put on the same per-100-poss scale
    as off_rtg/def_rtg so the three are comparable.
  - def_rtg: off_rtg - net_rtg. This backs into defensive rating without
    needing opponent box-score data, which this endpoint doesn't provide
    per-team anyway.
  - ts_pct: true shooting percentage, PTS / (2 * (FGA + 0.44*FTA)) — a
    standard efficiency metric that accounts for free throws and threes.

Idempotent: re-running for the same season replaces that season's rows in
mart_team_stats instead of piling up duplicates, matching the ingestion
script's pattern.

Run it (with the venv active, after running ingest_team_stats.py) as:
    python transform_team_stats.py
"""
import sqlite3

from config import DB_PATH, SEASON

RAW_TABLE = "raw_team_stats"
MART_TABLE = "mart_team_stats"

# The transform itself: one SELECT against the raw table, computing every
# derived metric from raw columns. Keeping this as a single readable query
# (rather than separate Python math) keeps the "T" in raw->mart literally
# in SQL, per the project's transform-with-SQL convention.
TRANSFORM_SQL = f"""
    SELECT
        "TEAM_ID"   AS team_id,
        "TEAM_NAME" AS team_name,
        "GP"        AS gp,
        "W"         AS w,
        "L"         AS l,
        ("FGA" - "OREB" + "TOV" + 0.4 * "FTA")                       AS poss_est,
        48.0 * ("FGA" - "OREB" + "TOV" + 0.4 * "FTA") / "MIN"        AS pace,
        100.0 * "PTS" / ("FGA" - "OREB" + "TOV" + 0.4 * "FTA")       AS off_rtg,
        100.0 * "PLUS_MINUS" / ("FGA" - "OREB" + "TOV" + 0.4 * "FTA") AS net_rtg,
        (100.0 * "PTS" / ("FGA" - "OREB" + "TOV" + 0.4 * "FTA"))
            - (100.0 * "PLUS_MINUS" / ("FGA" - "OREB" + "TOV" + 0.4 * "FTA")) AS def_rtg,
        100.0 * "PTS" / (2.0 * ("FGA" + 0.44 * "FTA"))               AS ts_pct,
        ? AS season
    FROM {RAW_TABLE}
    WHERE season = ?
"""


def run_transform(season: str) -> None:
    """Compute derived metrics from raw_team_stats and write them to mart_team_stats."""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {MART_TABLE} (
                team_id INTEGER,
                team_name TEXT,
                gp INTEGER,
                w INTEGER,
                l INTEGER,
                poss_est REAL,
                pace REAL,
                off_rtg REAL,
                net_rtg REAL,
                def_rtg REAL,
                ts_pct REAL,
                season TEXT
            )
            """
        )

        # Idempotency: clear this season's existing rows before re-inserting,
        # same pattern as the raw ingestion script.
        deleted = conn.execute(
            f"DELETE FROM {MART_TABLE} WHERE season = ?", (season,)
        ).rowcount
        if deleted:
            print(f"  Removed {deleted} existing rows for {season} (idempotent re-run).")

        rows = conn.execute(TRANSFORM_SQL, (season, season)).fetchall()
        conn.executemany(
            f"""
            INSERT INTO {MART_TABLE}
                (team_id, team_name, gp, w, l, poss_est, pace, off_rtg, net_rtg, def_rtg, ts_pct, season)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
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
            SELECT team_name, ROUND(pace, 1), ROUND(off_rtg, 1), ROUND(def_rtg, 1), ROUND(net_rtg, 1)
            FROM {MART_TABLE}
            WHERE season = ?
            ORDER BY net_rtg DESC
            LIMIT 5
            """,
            (season,),
        )
        print("  Top 5 teams by net rating:")
        print(f"    {'TEAM_NAME':<24}{'PACE':>7}{'OFF_RTG':>9}{'DEF_RTG':>9}{'NET_RTG':>9}")
        for team_name, pace, off_rtg, def_rtg, net_rtg in cursor.fetchall():
            print(f"    {team_name:<24}{pace:>7}{off_rtg:>9}{def_rtg:>9}{net_rtg:>9}")
    finally:
        conn.close()


def main() -> None:
    run_transform(SEASON)
    sanity_check(SEASON)
    print("\nDone.")


if __name__ == "__main__":
    main()
