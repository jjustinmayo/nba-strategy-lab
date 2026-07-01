"""League-wide comparison view: all 30 teams' pace/ratings, sortable."""
import pandas as pd
import streamlit as st


def render(team_stats: pd.DataFrame) -> None:
    """Render a sortable table of every team's pace and ratings."""
    st.header("League Overview")

    display_df = team_stats[
        ["team_name", "pace", "off_rtg", "def_rtg", "net_rtg", "ts_pct"]
    ].rename(
        columns={
            "team_name": "Team",
            "pace": "Pace",
            "off_rtg": "Off Rtg",
            "def_rtg": "Def Rtg",
            "net_rtg": "Net Rtg",
            "ts_pct": "TS%",
        }
    )
    display_df["TS%"] = display_df["TS%"].round(1)
    for col in ["Pace", "Off Rtg", "Def Rtg", "Net Rtg"]:
        display_df[col] = display_df[col].round(1)

    st.dataframe(
        display_df.sort_values("Net Rtg", ascending=False),
        hide_index=True,
        use_container_width=True,
    )
