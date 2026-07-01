"""
Ingestion: league-wide player clutch stats -> raw SQLite table.

One script, one job: pull season-level player box-score totals for clutch
situations from the NBA stats API and land them AS-IS in a raw_ table. No
transforming happens here — transforms live in a separate SQL layer later
that READS from this raw table.

Mirrors ingest_team_stats.py's flat-header ingestion pattern exactly —
LeagueDashPlayerClutch returns a flat header list (confirmed against the
live API), unlike the shot-locations endpoints' nested/grouped headers.

Uses the endpoint's default clutch definition — last 5 minutes of a game,
team ahead or behind by 5 points or fewer — which is the NBA's standard
"clutch time" definition, rather than overriding any of the clutch-scoping
parameters.

Idempotent: re-running for the same season replaces that season's rows
instead of piling up duplicates.

Run it (with the venv active) as:  python ingest_player_clutch.py
"""
import sqlite3
from datetime import datetime, timezone

from nba_api.stats.endpoints import leaguedashplayerclutch

from config import DB_PATH, SEASON, SEASON_TYPE

RAW_TABLE = "raw_player_clutch"


def fetch_player_clutch(season: str, season_type: str) -> tuple[list[str], list[list]]:
    """Call the NBA stats API and return (column_headers, rows) as plain lists."""
    print(f"Fetching player clutch stats for {season} ({season_type})...")
    endpoint = leaguedashplayerclutch.LeagueDashPlayerClutch(
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
    ingested_at = datetime.now(timezone.utc).isoformat()
    all_columns = headers + ["season", "ingested_at"]
    enriched_rows = [list(row) + [season, ingested_at] for row in rows]

    col_list = ", ".join(f'"{c}"' for c in all_columns)
    placeholders = ", ".join("?" for _ in all_columns)

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(f"CREATE TABLE IF NOT EXISTS {RAW_TABLE} ({col_list})")

        deleted = conn.execute(
            f"DELETE FROM {RAW_TABLE} WHERE season = ?", (season,)
        ).rowcount
        if deleted:
            print(f"  Removed {deleted} existing rows for {season} (idempotent re-run).")

        conn.executemany(
            f"INSERT INTO {RAW_TABLE} ({col_list}) VALUES ({placeholders})",
            enriched_rows,
        )
        conn.commit()
        print(f"  Wrote {len(enriched_rows)} rows to {RAW_TABLE}.")
    finally:
        conn.close()


def sanity_check(season: str) -> None:
    """Basic post-ingest validation: row count + a spot-check of a few players."""
    conn = sqlite3.connect(DB_PATH)
    try:
        count = conn.execute(
            f"SELECT COUNT(*) FROM {RAW_TABLE} WHERE season = ?", (season,)
        ).fetchone()[0]
        print(f"\nSanity check for {season}:")
        print(f"  Row count: {count}")

        cursor = conn.execute(
            f"""
            SELECT "PLAYER_NAME", "MIN", "PTS", "FG_PCT"
            FROM {RAW_TABLE}
            WHERE season = ?
            ORDER BY "PTS" DESC
            LIMIT 5
            """,
            (season,),
        )
        print("  Top 5 players by clutch points:")
        print(f"    {'PLAYER_NAME':<24}{'CLUTCH_MIN':>11}{'CLUTCH_PTS':>11}{'FG_PCT':>8}")
        for player_name, minutes, pts, fg_pct in cursor.fetchall():
            print(f"    {player_name:<24}{minutes:>11}{pts:>11}{fg_pct:>8}")
    finally:
        conn.close()


def main() -> None:
    headers, rows = fetch_player_clutch(SEASON, SEASON_TYPE)
    land_raw(headers, rows, SEASON)
    sanity_check(SEASON)
    print("\nDone.")


if __name__ == "__main__":
    main()
