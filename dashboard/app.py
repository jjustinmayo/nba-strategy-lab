"""
NBA Strategy Lab dashboard entry point.

Run with (venv active, from the repo root):  streamlit run dashboard/app.py
"""
import sys
from pathlib import Path

import streamlit as st

# `streamlit run dashboard/app.py` puts dashboard/ (not the repo root) on
# sys.path, so `import dashboard.*` would otherwise fail. Add the repo root
# explicitly before importing sibling package modules.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dashboard.data import (  # noqa: E402
    load_player_clutch,
    load_player_overview,
    load_player_shot_profile,
    load_shot_profile,
    load_team_stats,
)
from dashboard.views import league, player_detail, player_overview, team_detail  # noqa: E402

st.set_page_config(page_title="NBA Strategy Lab", layout="wide")

team_stats = load_team_stats()
shot_profile = load_shot_profile()
player_overview_data = load_player_overview()
player_shot_profile = load_player_shot_profile()
player_clutch = load_player_clutch()

st.sidebar.title("NBA Strategy Lab")
mode = st.sidebar.radio(
    "View", ["League Overview", "Team Detail", "Player Overview", "Player Detail"]
)

if mode == "League Overview":
    league.render(team_stats)
elif mode == "Team Detail":
    team_name = st.sidebar.selectbox("Team", sorted(team_stats["team_name"]))
    team_detail.render(team_name, shot_profile)
elif mode == "Player Overview":
    player_overview.render(player_overview_data)
else:
    player_name = st.sidebar.selectbox(
        "Player", sorted(player_shot_profile["player_name"])
    )
    player_detail.render(player_name, player_shot_profile, player_clutch)
