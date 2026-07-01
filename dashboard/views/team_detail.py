"""Team detail view: shot-mix profile for a single selected team."""
import pandas as pd
import streamlit as st

# The 7 zones that partition total FGA with no overlap. Excludes the API's
# "corner_3" column, which is the sum of left_corner_3 + right_corner_3 and
# would double-count attempts if included — see
# docs/solutions/design-patterns/flattening-nested-nba-api-headers.md
ZONES = [
    "restricted_area",
    "in_the_paint_non_ra",
    "mid_range",
    "left_corner_3",
    "right_corner_3",
    "above_the_break_3",
    "backcourt",
]

ZONE_LABELS = {
    "restricted_area": "Restricted Area",
    "in_the_paint_non_ra": "Paint (Non-RA)",
    "mid_range": "Mid-Range",
    "left_corner_3": "Left Corner 3",
    "right_corner_3": "Right Corner 3",
    "above_the_break_3": "Above Break 3",
    "backcourt": "Backcourt",
}


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
