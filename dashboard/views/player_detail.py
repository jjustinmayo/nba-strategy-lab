"""Player detail view: shot-mix profile plus clutch summary for a single selected player."""
import pandas as pd
import streamlit as st

from dashboard.views.zones import ZONE_LABELS, ZONES


def render(player_name: str, shot_profile: pd.DataFrame, clutch: pd.DataFrame) -> None:
    """Render the selected player's shot-mix chart plus a clutch summary."""
    st.header(f"Player Detail: {player_name}")

    row = shot_profile[shot_profile["player_name"] == player_name]
    if row.empty:
        st.warning(f"No shot-profile data found for {player_name}.")
        return
    row = row.iloc[0]

    if pd.isna(row["total_fga"]):
        st.info(
            f"Shot-zone data for {player_name} is incomplete this season "
            "(a zone attempt count is missing upstream)."
        )
    elif row["total_fga"] == 0:
        st.info(f"{player_name} has 0 total field goal attempts this season.")
    else:
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

    st.subheader("Clutch performance")
    clutch_row = clutch[clutch["player_name"] == player_name]
    if clutch_row.empty:
        st.info("No clutch data yet this season.")
        return

    clutch_row = clutch_row.iloc[0]
    if pd.isna(clutch_row["clutch_pts_per100"]):
        st.info(
            f"{player_name} has {clutch_row['clutch_min']:.1f} clutch minutes logged, "
            "but not enough estimated clutch possessions for a reliable efficiency rate."
        )
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Clutch Minutes", f"{clutch_row['clutch_min']:.1f}")
    col2.metric("Clutch TS%", f"{clutch_row['clutch_ts_pct']:.1f}")
    col3.metric("Clutch Pts/100", f"{clutch_row['clutch_pts_per100']:.1f}")
