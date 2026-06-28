"""
Ingestion: league-wide team stats -> raw SQLite table.

One script, one job: pull season-level team stats from the NBA stats API and
land them AS-IS in a raw_ table. No transforming happens here — transforms
live in a separate SQL layer later that READS from this raw table. That
separation lets us re-run transforms without re-hitting the API, and keeps a
source of truth if a transform has a bug.

We deliberately use only the standard library's sqlite3 plus the raw dict the
API returns (no pandas), so there is no compiled dependency to be blocked by
Windows Smart App Control, and the API's exact rows/columns land untouched.

Idempotent: re-running for the same season replaces that season's rows instead
of piling up duplicates.

Run it (with the venv active) as:  python ingest_team_stats.py
"""
import sqlite3
from datetime import datetime, timezone

from nba_api.stats.endpoints import leaguedashteamstats

from config import DB_PATH, SEASON, SEASON_TYPE

# Name of the raw landing table. raw_ prefix marks it as untouched source data.
RAW_TABLE = "raw_team_stats"


def fetch_team_stats(season: str, season_type: str) -> tuple[list[str], list[list]]:
    """Call the NBA stats API and return (column_headers, rows) as plain lists.

    The API responds with JSON shaped like:
        {"resultSets": [{"headers": [...], "rowSet": [[...], [...], ...]}]}
    We take the first result set: its `headers` are the column names and its
    `rowSet` is a list of rows (each row a list of values, in header order).
    """
    print(f"Fetching team stats for {season} ({season_type})...")
    endpoint = leaguedashteamstats.LeagueDashTeamStats(
        season=season,
        season_type_all_star=season_type,
    )
    result_set = endpoint.get_dict()["resultSets"][0]
    headers = result_set["headers"]
    rows = result_set["rowSet"]
    print(f"  API returned {len(rows)} rows, {len(headers)} columns.")
    return headers, rows


def land_raw(headers: list[str], rows: list[list], season: str) -> None:
    """Write the rows to the raw SQLite table, idempotently per season."""
    # Two lineage columns: which season these rows belong to, and when we
    # pulled them. This is metadata ABOUT the ingest, not a transformation of
    # the stats — the API's own values land exactly as returned. `season` also
    # lets the idempotent re-run below target just this season.
    ingested_at = datetime.now(timezone.utc).isoformat()
    all_columns = headers + ["season", "ingested_at"]
    enriched_rows = [list(row) + [season, ingested_at] for row in rows]

    # Double-quote every column name so names the API gives us are always valid
    # SQL identifiers, and build a "?, ?, ..." placeholder list for safe,
    # parameterized inserts (never string-format values into SQL).
    col_list = ", ".join(f'"{c}"' for c in all_columns)
    placeholders = ", ".join("?" for _ in all_columns)

    conn = sqlite3.connect(DB_PATH)
    try:
        # Create the table if it doesn't exist yet. We declare columns with NO
        # type, which gives SQLite "NONE" affinity: each value is stored exactly
        # as inserted (ints stay ints, text stays text) — faithful raw landing,
        # and numeric columns still sort correctly.
        conn.execute(f"CREATE TABLE IF NOT EXISTS {RAW_TABLE} ({col_list})")

        # Idempotency: clear this season's existing rows before re-inserting, so
        # a re-run replaces rather than duplicates. (Returns 0 on a first run.)
        deleted = conn.execute(
            f"DELETE FROM {RAW_TABLE} WHERE season = ?", (season,)
        ).rowcount
        if deleted:
            print(f"  Removed {deleted} existing rows for {season} (idempotent re-run).")

        # executemany runs the same INSERT once per row — one efficient batch.
        conn.executemany(
            f"INSERT INTO {RAW_TABLE} ({col_list}) VALUES ({placeholders})",
            enriched_rows,
        )
        conn.commit()
        print(f"  Wrote {len(enriched_rows)} rows to {RAW_TABLE}.")
    finally:
        conn.close()


def sanity_check(season: str) -> None:
    """Basic post-ingest validation: row count + a spot-check of a few teams."""
    conn = sqlite3.connect(DB_PATH)
    try:
        count = conn.execute(
            f"SELECT COUNT(*) FROM {RAW_TABLE} WHERE season = ?", (season,)
        ).fetchone()[0]
        print(f"\nSanity check for {season}:")
        print(f"  Row count: {count} (expected ~30 teams)")

        # Spot-check: top teams by wins, so you can eyeball them against what you
        # know to be true for the season.
        cursor = conn.execute(
            f"""
            SELECT "TEAM_NAME", "GP", "W", "L", "PTS"
            FROM {RAW_TABLE}
            WHERE season = ?
            ORDER BY "W" DESC
            LIMIT 5
            """,
            (season,),
        )
        print("  Top 5 teams by wins:")
        print(f"    {'TEAM_NAME':<24}{'GP':>5}{'W':>5}{'L':>5}{'PTS':>9}")
        for team_name, gp, w, l, pts in cursor.fetchall():
            print(f"    {team_name:<24}{gp:>5}{w:>5}{l:>5}{pts:>9}")
    finally:
        conn.close()


def main() -> None:
    headers, rows = fetch_team_stats(SEASON, SEASON_TYPE)
    land_raw(headers, rows, SEASON)
    sanity_check(SEASON)
    print("\nDone.")


if __name__ == "__main__":
    main()
