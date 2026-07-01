"""Player overview: sortable, volume-filtered table of shot mix + clutch summary."""
import pandas as pd
import streamlit as st


def render(player_overview: pd.DataFrame) -> None:
    """Render a sortable table of players, filtered by a minimum-FGA slider."""
    st.header("Player Overview")

    min_fga = st.slider("Minimum FGA", min_value=0, max_value=1000, value=50, step=10)
    filtered = player_overview[player_overview["total_fga"] >= min_fga]

    display_df = filtered[
        [
            "player_name",
            "team_abbreviation",
            "total_fga",
            "above_the_break_3_pct_of_fga",
            "restricted_area_pct_of_fga",
            "mid_range_pct_of_fga",
            "clutch_min",
            "clutch_ts_pct",
            "clutch_pts_per100",
        ]
    ].rename(
        columns={
            "player_name": "Player",
            "team_abbreviation": "Team",
            "total_fga": "FGA",
            "above_the_break_3_pct_of_fga": "Above-Break-3 %",
            "restricted_area_pct_of_fga": "Rim %",
            "mid_range_pct_of_fga": "Mid-Range %",
            "clutch_min": "Clutch Min",
            "clutch_ts_pct": "Clutch TS%",
            "clutch_pts_per100": "Clutch Pts/100",
        }
    )
    for col in ["Clutch Min", "Clutch TS%", "Clutch Pts/100"]:
        display_df[col] = display_df[col].round(1)

    st.caption(f"Showing {len(display_df)} of {len(player_overview)} players")
    st.dataframe(
        display_df.sort_values("FGA", ascending=False),
        hide_index=True,
        use_container_width=True,
    )
