"""
Ingestion: league-wide team shot locations -> raw SQLite table.

One script, one job: pull season-level team shooting broken out by court zone
from the NBA stats API and land it AS-IS in a raw_ table. No transforming
happens here — transforms live in a separate SQL layer later that READS from
this raw table.

The API returns shot zones as a nested/grouped header (one FGM/FGA/FG_PCT
triplet per zone: Restricted Area, In The Paint (Non-RA), Mid-Range, Left
Corner 3, Right Corner 3, Above the Break 3, Backcourt, and a combined
Corner 3) rather than one flat header per column. SQL columns can't be
nested, so we flatten each (zone, stat) pair into one column name, e.g.
"restricted_area_fgm" — this is just naming, not a transformation of any
value; every number still lands exactly as the API returned it.

Idempotent: re-running for the same season replaces that season's rows
instead of piling up duplicates, matching ingest_team_stats.py's pattern.

Run it (with the venv active) as:  python ingest_team_shot_locations.py
"""
import re
import sqlite3
from datetime import datetime, timezone

from nba_api.stats.endpoints import leaguedashteamshotlocations

from config import DB_PATH, SEASON, SEASON_TYPE

RAW_TABLE = "raw_team_shot_locations"


def _snake_case(name: str) -> str:
    """Turn an API zone label like 'Above the Break 3' into 'above_the_break_3'."""
    name = re.sub(r"[^0-9a-zA-Z]+", "_", name)
    return name.strip("_").lower()


def fetch_team_shot_locations(season: str, season_type: str) -> tuple[list[str], list[list]]:
    """Call the NBA stats API and return (flattened_column_names, rows).

    The API responds with a nested header shape:
        {"resultSets": {"headers": [
            {"name": "SHOT_CATEGORY", "columnsToSkip": 2, "columnNames": [<zone>, ...]},
            {"name": "columns", "columnNames": ["TEAM_ID", "TEAM_NAME", "FGM", "FGA", "FG_PCT", ...]},
        ], "rowSet": [[...], ...]}}
    The first header group names one zone per (FGM, FGA, FG_PCT) triplet in
    the second group, after the leading TEAM_ID/TEAM_NAME columns
    (`columnsToSkip`). We flatten that into one header per column, in row order.
    """
    print(f"Fetching team shot locations for {season} ({season_type})...")
    endpoint = leaguedashteamshotlocations.LeagueDashTeamShotLocations(
        season=season,
        season_type_all_star=season_type,
    )
    result_set = endpoint.get_dict()["resultSets"]
    zone_group, columns_group = result_set["headers"]

    skip = zone_group["columnsToSkip"]
    stat_names = columns_group["columnNames"][skip:]

    headers = columns_group["columnNames"][:skip]
    for zone in zone_group["columnNames"]:
        zone_slug = _snake_case(zone)
        for i in range(3):
            headers.append(f"{zone_slug}_{stat_names[i].lower()}")

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
    """Basic post-ingest validation: row count + a spot-check of a few teams."""
    conn = sqlite3.connect(DB_PATH)
    try:
        count = conn.execute(
            f"SELECT COUNT(*) FROM {RAW_TABLE} WHERE season = ?", (season,)
        ).fetchone()[0]
        print(f"\nSanity check for {season}:")
        print(f"  Row count: {count} (expected ~30 teams)")

        # Spot-check: teams with the highest above-the-break-3 attempt share,
        # eyeballed against teams known to shoot a lot of threes.
        cursor = conn.execute(
            f"""
            SELECT "TEAM_NAME", "above_the_break_3_fga", "restricted_area_fga"
            FROM {RAW_TABLE}
            WHERE season = ?
            ORDER BY "above_the_break_3_fga" DESC
            LIMIT 5
            """,
            (season,),
        )
        print("  Top 5 teams by above-the-break-3 attempts:")
        print(f"    {'TEAM_NAME':<24}{'ABOVE_BREAK_3_FGA':>19}{'RESTRICTED_AREA_FGA':>21}")
        for team_name, above_break_3_fga, restricted_area_fga in cursor.fetchall():
            print(f"    {team_name:<24}{above_break_3_fga:>19}{restricted_area_fga:>21}")
    finally:
        conn.close()


def main() -> None:
    headers, rows = fetch_team_shot_locations(SEASON, SEASON_TYPE)
    land_raw(headers, rows, SEASON)
    sanity_check(SEASON)
    print("\nDone.")


if __name__ == "__main__":
    main()
