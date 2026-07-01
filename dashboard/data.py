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
