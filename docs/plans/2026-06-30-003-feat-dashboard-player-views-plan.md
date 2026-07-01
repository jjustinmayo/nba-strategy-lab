---
artifact_contract: ce-unified-plan/v1
artifact_readiness: implementation-ready
execution: code
product_contract_source: ce-plan-bootstrap
date: 2026-06-30
---

# feat: Player views for the dashboard

## Summary

Extend the Streamlit dashboard with player-level views, wiring in
`mart_player_shot_profile` and `mart_player_clutch` (built in
`docs/plans/2026-06-30-002-feat-player-shot-clutch-data-model-plan.md`, which
explicitly deferred dashboard integration — KTD5). Adds two new sidebar modes,
mirroring the existing team-side pattern: a league-wide "Player Overview"
table and a "Player Detail" drill-down, plus the minimum-volume filter that
plan explicitly deferred to whoever consumes the data (KTD3) — this dashboard
is that consumer.

## Problem Frame

The dashboard currently only shows team-level data (`League Overview`,
`Team Detail`). The player data model exists in the database but has no UI.
Unlike teams (30 rows, no filtering needed), players are 582 rows for shot
profile and 492 for clutch — showing all of them unfiltered by default would
bury the interesting names under end-of-bench noise.

## Key Technical Decisions

- **KTD1 — Full symmetry with the team-side UX.** Two new modes: "Player
  Overview" (sortable table, mirrors `League Overview`) and "Player Detail"
  (shot-mix chart, mirrors `Team Detail`). Confirmed with user over embedding
  players inside `Team Detail` — keeps the two axes (team-first vs.
  player-first browsing) independent and consistent with the existing pattern.
- **KTD2 — Player Overview joins shot profile and clutch data on
  `player_id` + `season`.** The two mart tables have different row counts
  (582 vs. 492) because not every player who took a shot this season has
  logged clutch minutes. Use a `LEFT JOIN` from `mart_player_shot_profile`
  (the larger set) so every player with shot data appears, with `NULL`
  clutch columns for players with no clutch minutes yet.
- **KTD3 — Default minimum-volume filter, user-adjustable.** Confirmed with
  user: Player Overview defaults to players with ≥50 total FGA (roughly a
  couple of games of real rotation minutes) rather than showing all 582.
  Implemented as a Streamlit slider defaulting to 50, not a hardcoded cutoff —
  the user can lower it to see everyone or raise it to narrow further. This
  resolves the sample-size question the data-model plan (KTD3 there)
  deliberately left to "whichever consumer reads this data."
- **KTD4 — Player Detail shows shot-mix chart + clutch summary, not raw
  ranks.** Mirrors `team_detail.py`'s bar-chart pattern for the 7 shot zones.
  Clutch is shown as a small summary (clutch minutes, TS%, pts/100) rather
  than a chart — clutch samples are small enough that a chart of 1-2 numbers
  would be visual noise; a labeled stat block is clearer.
- **KTD5 — No changes to the data model in this plan.** This plan only reads
  from `mart_player_shot_profile`/`mart_player_clutch` — both already built
  and validated in the prior plan.

## Requirements

- **R1**: A "Player Overview" mode showing a sortable table of players
  (shot-mix % + clutch summary), joined per KTD2.
- **R2**: Player Overview defaults to a minimum-FGA filter (KTD3), adjustable
  via a slider, not a fixed cutoff with no escape hatch.
- **R3**: A "Player Detail" mode: select a player, see their shot-mix chart
  (same style as `Team Detail`'s) plus a clutch summary (KTD4).
- **R4**: Players with no clutch minutes (`NULL` clutch columns from the
  `LEFT JOIN`) display cleanly — e.g., "no clutch data yet" — not a crash or
  a blank/confusing cell.
- **R5**: New view code reads only from the two mart tables via `dashboard/data.py`
  (extended, not bypassed) — consistent with the existing dashboard's
  mart-only read boundary.

## Implementation Units

### U1. Player data access functions

**Goal:** Load player shot profile and clutch data as DataFrames, including
the joined overview query.

**Requirements:** R1, R2, R5

**Dependencies:** None

**Files:**
- `dashboard/data.py` (modify — add functions alongside existing
  `load_team_stats`/`load_shot_profile`)

**Approach:** Add `load_player_shot_profile(season)` and
`load_player_clutch(season)` (same `pandas.read_sql_query` pattern as the
existing team functions). Add `load_player_overview(season)` that performs
the KTD2 `LEFT JOIN` in SQL (not a pandas merge) — join
`mart_player_shot_profile` to `mart_player_clutch` on `player_id` and
`season`, selecting the shot-mix `_pct_of_fga` columns plus
`clutch_ts_pct`/`clutch_pts_per100`/`clutch_min` from the clutch side.

**Patterns to follow:** `dashboard/data.py`'s existing `load_team_stats`/
`load_shot_profile` (connection handling, parameterized query, `sys.path`
repo-root fix already in place at the top of the file).

**Test scenarios:**
- Happy path: `load_player_overview(SEASON)` returns 582 rows (matching
  `mart_player_shot_profile`'s row count) with both shot-mix and clutch
  columns present.
- Edge case: a player present in `mart_player_shot_profile` but absent from
  `mart_player_clutch` (there are ~90 such players this season) appears in
  the result with `NULL`/`NaN` clutch columns, not dropped by the join.
- Happy path: `load_player_shot_profile(SEASON)` and `load_player_clutch(SEASON)`
  each return their respective mart table's full row count.

**Verification:** Row counts and join behavior confirmed against the real
`nba_strategy.db`; spot-check one known player with clutch data and one
without.

---

### U2. Player Overview view

**Goal:** Render the sortable, volume-filtered player table.

**Requirements:** R1, R2, R4

**Dependencies:** U1

**Files:**
- `dashboard/views/player_overview.py` (new)

**Approach:** Mirror `league.py`'s `st.dataframe` structure. Add an
`st.slider("Minimum FGA", ...)` defaulting to 50 (KTD3) above the table;
filter the DataFrame on `total_fga >= slider_value` before rendering. Format
`NULL` clutch columns as a readable placeholder (e.g., via
`.fillna` to a display string, or leaving them blank in `st.dataframe` —
Streamlit already renders `NaN` as empty, which satisfies R4's "not
confusing" bar without extra code).

**Patterns to follow:** `dashboard/views/league.py` (table rendering,
column rename/rounding style).

**Test scenarios:**
- Happy path: default slider (50 FGA) shows fewer than 582 rows, sorted
  table includes column headers for shot-mix % and clutch stats.
- Edge case: moving the slider to 0 shows all 582 players including
  zero-attempt players (if any exist this season).
- Edge case: a player with `NULL` clutch columns renders without an error or
  a raw "NaN" string in a way that looks broken (Streamlit's default NaN
  rendering as blank satisfies this — confirm visually).

**Verification:** Running the app and viewing Player Overview shows a
filterable table where raising/lowering the FGA slider changes the visible
row count live.

---

### U3. Player Detail view

**Goal:** Given a selected player, show their shot-mix chart plus a clutch
summary.

**Requirements:** R3, R4

**Dependencies:** U1

**Files:**
- `dashboard/views/player_detail.py` (new)

**Approach:** Reuse `team_detail.py`'s `ZONES`/`ZONE_LABELS` constants and
bar-chart structure for the shot-mix chart (same 7 zones, same
`st.bar_chart` calls for `% of FGA` and `FG%`). Below the chart, render a
clutch summary using `st.metric` (or similar) for `clutch_min`,
`clutch_ts_pct`, `clutch_pts_per100`. When the player has no row in
`mart_player_clutch` (R4), show "No clutch data yet this season" instead of
blank/`NaN` metrics.

**Technical design (directional):**
```
shot_row = shot_profile[player_name]
render bar charts exactly as team_detail.py does, keyed on shot_row

clutch_row = clutch_data[player_name]  (may not exist)
if clutch_row exists: st.metric(...) x3
else: st.info("No clutch data yet this season")
```

**Patterns to follow:** `dashboard/views/team_detail.py` (zones, chart
structure, the `if row.empty` no-data guard pattern).

**Test scenarios:**
- Happy path: selecting a high-volume player known for a distinct shot
  profile shows the same kind of visibly distinct bar-chart shape as the
  team version already demonstrates.
- Edge case: selecting a player with no clutch minutes shows the
  "No clutch data yet" message instead of blank metrics or an exception.
- Edge case: selecting a player with 0 total FGA (if any exist) shows the
  existing `team_detail.py`-style "no data found" warning rather than a
  divide-by-zero display artifact (the mart layer already stores `NULL` for
  these — the view must handle `NULL` gracefully, not just empty-DataFrame).

**Verification:** Running the app, selecting several different players
(including at least one with no clutch data) renders correctly with no
exceptions or visibly broken metrics.

---

### U4. Wire player modes into the app

**Goal:** Add "Player Overview" and "Player Detail" to the sidebar navigation.

**Requirements:** R1, R3

**Dependencies:** U1, U2, U3

**Files:**
- `dashboard/app.py` (modify)

**Approach:** Extend the existing `st.sidebar.radio("View", [...])` options
list with the two new modes, following the same
`if mode == ... elif ... else` branching already used for
`League Overview`/`Team Detail`. Player Detail's player selector mirrors
Team Detail's team selector (`st.sidebar.selectbox` populated from the
loaded player data).

**Patterns to follow:** `dashboard/app.py`'s existing mode-branching
structure (KTD2 from the original dashboard plan: single-file
view-selection pattern).

**Test scenarios:**
- Test expectation: none — this unit is wiring/composition of already-tested
  U2/U3 view functions; correctness is verified by running the app (see
  Verification), not unit tests.

**Verification:** `streamlit run dashboard/app.py` starts without error; all
four modes (League Overview, Team Detail, Player Overview, Player Detail)
are reachable from the sidebar and each renders without exceptions.

---

## Scope Boundaries

**Deferred to Follow-Up Work:**
- Cross-linking (e.g., clicking a team in Team Detail jumps to that team's
  players in Player Overview) — nice-to-have navigation polish, not core to
  this round
- Caching (`st.cache_data`) for the new queries — same KTD4 rationale as the
  original dashboard plan: not worth the complexity until there's a real
  performance problem
- Any further data model work (play types, hustle stats, lineups) — already
  deferred in the prior plan

## Verification Contract

- `load_player_overview` returns the correct joined row count and column set
  against the real `nba_strategy.db`.
- All four dashboard modes render without exceptions when run via
  `streamlit run dashboard/app.py`.
- The FGA slider visibly changes Player Overview's row count.
- A player with no clutch data displays a clear "no data" message in Player
  Detail rather than blank/broken metrics.

## Definition of Done

- U1-U4 implemented and manually verified per each unit's Verification.
- Dashboard runs end-to-end with all 4 modes against the real
  `nba_strategy.db`.
