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

from dashboard.data import load_shot_profile, load_team_stats  # noqa: E402
from dashboard.views import league, team_detail  # noqa: E402

st.set_page_config(page_title="NBA Strategy Lab", layout="wide")

team_stats = load_team_stats()
shot_profile = load_shot_profile()

st.sidebar.title("NBA Strategy Lab")
mode = st.sidebar.radio("View", ["League Overview", "Team Detail"])

if mode == "League Overview":
    league.render(team_stats)
else:
    team_name = st.sidebar.selectbox("Team", sorted(team_stats["team_name"]))
    team_detail.render(team_name, shot_profile)
