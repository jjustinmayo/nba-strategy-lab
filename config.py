"""
Configuration for the NBA Strategy Lab pipeline.

Centralizes settings (database location, which season to pull) in ONE place
instead of hardcoding them across scripts. This is the "config over
hardcoding" principle: to change the season or move the database, you edit
here once, not hunt through every script.
"""
from pathlib import Path

# Project root = the folder THIS file lives in. Building paths relative to the
# file (rather than the current working directory) means the scripts work no
# matter which folder you run them from, and on any machine (your other
# desktop included).
PROJECT_ROOT = Path(__file__).resolve().parent

# Local SQLite database file. Matched by *.db in .gitignore, so it is never
# committed. Created automatically on the first ingest run.
DB_PATH = PROJECT_ROOT / "nba_strategy.db"

# Which season to pull. The NBA stats API expects the "YYYY-YY" string format.
SEASON = "2025-26"

# Season type. Valid values the API accepts: "Regular Season", "Playoffs",
# "Pre Season", "All Star".
SEASON_TYPE = "Regular Season"
