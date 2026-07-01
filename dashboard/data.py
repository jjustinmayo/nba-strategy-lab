"""
Data access for the Streamlit dashboard.

One module, one job: load the mart_ tables as pandas DataFrames. The
dashboard's view code should never write raw SQL inline — it calls these
functions instead, keeping the mart-layer read boundary in one place.
"""
import sqlite3
import sys
from pathlib import Path

import pandas as pd

# `streamlit run dashboard/app.py` puts dashboard/ (not the repo root) on
# sys.path, so `import config` would otherwise fail. Add the repo root
# (this file's parent's parent) explicitly, matching config.py's own
# path-relative-to-__file__ approach.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DB_PATH, SEASON  # noqa: E402


def load_team_stats(season: str = SEASON) -> pd.DataFrame:
    """Load mart_team_stats (pace/ratings per team) for the given season."""
    conn = sqlite3.connect(DB_PATH)
    try:
        return pd.read_sql_query(
            "SELECT * FROM mart_team_stats WHERE season = ?", conn, params=(season,)
        )
    finally:
        conn.close()


def load_shot_profile(season: str = SEASON) -> pd.DataFrame:
    """Load mart_team_shot_profile (shot-mix % by zone per team) for the given season."""
    conn = sqlite3.connect(DB_PATH)
    try:
        return pd.read_sql_query(
            "SELECT * FROM mart_team_shot_profile WHERE season = ?", conn, params=(season,)
        )
    finally:
        conn.close()


def load_player_shot_profile(season: str = SEASON) -> pd.DataFrame:
    """Load mart_player_shot_profile (shot-mix % by zone per player) for the given season."""
    conn = sqlite3.connect(DB_PATH)
    try:
        return pd.read_sql_query(
            "SELECT * FROM mart_player_shot_profile WHERE season = ?", conn, params=(season,)
        )
    finally:
        conn.close()


def load_player_clutch(season: str = SEASON) -> pd.DataFrame:
    """Load mart_player_clutch (clutch efficiency metrics per player) for the given season."""
    conn = sqlite3.connect(DB_PATH)
    try:
        return pd.read_sql_query(
            "SELECT * FROM mart_player_clutch WHERE season = ?", conn, params=(season,)
        )
    finally:
        conn.close()


def load_player_overview(season: str = SEASON) -> pd.DataFrame:
    """Load a joined player overview: shot-mix % plus clutch summary per player.

    LEFT JOINs mart_player_clutch onto mart_player_shot_profile (the larger
    set — not every player with shot data has logged clutch minutes yet), so
    every player with shot data appears, with NULL clutch columns for players
    with no clutch data this season.
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        return pd.read_sql_query(
            """
            SELECT
                sp.player_id,
                sp.player_name,
                sp.team_abbreviation,
                sp.total_fga,
                sp.restricted_area_pct_of_fga,
                sp.in_the_paint_non_ra_pct_of_fga,
                sp.mid_range_pct_of_fga,
                sp.left_corner_3_pct_of_fga,
                sp.right_corner_3_pct_of_fga,
                sp.above_the_break_3_pct_of_fga,
                sp.backcourt_pct_of_fga,
                c.clutch_min,
                c.clutch_ts_pct,
                c.clutch_pts_per100
            FROM mart_player_shot_profile sp
            LEFT JOIN mart_player_clutch c
                ON sp.player_id = c.player_id AND sp.season = c.season
            WHERE sp.season = ?
            """,
            conn,
            params=(season,),
        )
    finally:
        conn.close()
