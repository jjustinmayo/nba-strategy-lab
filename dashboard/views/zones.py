"""Shared shot-zone constants for team_detail.py and player_detail.py.

The 7 zones that partition total FGA with no overlap. Excludes the API's
combined "corner_3" column (sum of left_corner_3 + right_corner_3) — see
docs/solutions/design-patterns/flattening-nested-nba-api-headers.md.
"""

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
