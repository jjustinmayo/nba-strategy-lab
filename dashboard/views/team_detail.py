"""Team detail view: shot-mix profile for a single selected team."""
import pandas as pd
import streamlit as st

from dashboard.views.zones import ZONE_LABELS, ZONES


def render(team_name: str, shot_profile: pd.DataFrame) -> None:
    """Render the selected team's shot-mix chart: zone share of FGA + FG% per zone."""
    st.header(f"Team Detail: {team_name}")

    row = shot_profile[shot_profile["team_name"] == team_name]
    if row.empty:
        st.warning(f"No shot-profile data found for {team_name}.")
        return
    row = row.iloc[0]

    mix_df = pd.DataFrame(
        {
            "Zone": [ZONE_LABELS[z] for z in ZONES],
            "% of FGA": [row[f"{z}_pct_of_fga"] for z in ZONES],
        }
    ).set_index("Zone")

    st.subheader("Shot mix (% of field goal attempts by zone)")
    st.bar_chart(mix_df)

    st.subheader("Field goal % by zone")
    fg_pct_df = pd.DataFrame(
        {
            "Zone": [ZONE_LABELS[z] for z in ZONES],
            "FG%": [round(row[f"{z}_fg_pct"] * 100, 1) for z in ZONES],
        }
    ).set_index("Zone")
    st.bar_chart(fg_pct_df)
