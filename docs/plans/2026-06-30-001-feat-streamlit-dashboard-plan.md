---
artifact_contract: ce-unified-plan/v1
artifact_readiness: implementation-ready
execution: code
product_contract_source: ce-plan-bootstrap
date: 2026-06-30
---

# feat: Streamlit dashboard for team stats and shot profiles

## Summary

Build the first version of the NBA Strategy Lab dashboard: a Streamlit app with a
league-wide comparison table (all 30 teams' pace/ratings) and a per-team detail
view showing shot-mix profile, so the user can spot what makes each team unique.
This is the first deliverable on the Dashboard/UX track in `STRATEGY.md`.

## Problem Frame

The pipeline has landed and transformed two mart tables (`mart_team_stats`,
`mart_team_shot_profile`) in `nba_strategy.db`, but there is no way to view them
except querying SQL directly. Per `STRATEGY.md`, the user judges this project by
outcome — a fast, accurate, visually clear surface that produces "didn't know
that" insight moments — not by understanding the code. There is currently no
dashboard framework in the project's dependencies.

## Requirements

- **R1**: League-wide table showing all 30 teams with pace, off_rtg, def_rtg,
  net_rtg, ts_pct — sortable by any column.
- **R2**: Clicking/selecting a team opens a detail view for that team.
- **R3**: Team detail view shows the team's shot-mix profile (7 zones: % of FGA
  and FG% per zone) in a way that's easy to interpret at a glance (chart, not
  raw numbers only).
- **R4**: Dashboard loads and updates quickly (ties to the "load/refresh speed"
  metric in `STRATEGY.md`).
- **R5**: Reads only from the mart layer (`mart_team_stats`,
  `mart_team_shot_profile`) — never queries `raw_` tables directly, preserving
  the raw/mart separation convention.

## Key Technical Decisions

- **KTD1 — Framework: Streamlit.** Chosen over Dash/Flask because it needs no
  separate frontend code, renders tables and charts with minimal boilerplate,
  and matches the project's beginner-Python constraint. Confirmed with user.
- **KTD2 — Single-file app with a page-selection pattern**, not `st.navigation`
  multi-file pages yet. `app.py` reads a `st.selectbox` (or sidebar radio) for
  "League" vs a specific team, and renders the corresponding view function.
  Simpler to reason about with one file at this scale (2 views); revisit
  multi-page structure only if the app grows past ~3-4 views.
- **KTD3 — Read via pandas `read_sql_query` against the existing SQLite file**,
  not a new data-access layer. `config.DB_PATH` is already the single source of
  truth for the DB location; the dashboard imports it directly, matching the
  ingestion/transform scripts' pattern.
- **KTD4 — No caching layer for v1.** `st.cache_data` is deferred — SQLite reads
  of two ~30-row tables are fast enough that caching would add complexity before
  there's a real performance problem to solve.

## Implementation Units

### U1. Data access module

**Goal:** One small module that loads the two mart tables as pandas DataFrames,
so the app code never writes raw SQL inline.

**Requirements:** R1, R5

**Dependencies:** None

**Files:**
- `dashboard/data.py` (new)
- `dashboard/data_test.py` (new, if a test runner is added — see Test scenarios)

**Approach:** Two functions, `load_team_stats(season)` and
`load_shot_profile(season)`, each running a parameterized
`SELECT * FROM mart_... WHERE season = ?` via `pandas.read_sql_query` against
`sqlite3.connect(config.DB_PATH)`, returning a DataFrame. Import `SEASON` from
`config.py` as the default season argument so the dashboard doesn't hardcode
`"2025-26"` a second time.

**Patterns to follow:** `config.py`'s existing `DB_PATH`/`SEASON` constants;
the parameterized-query style already used in `transform_team_stats.py`.

**Test scenarios:**
- Happy path: `load_team_stats(SEASON)` returns a DataFrame with 30 rows and
  the expected columns (`team_name`, `pace`, `off_rtg`, `def_rtg`, `net_rtg`,
  `ts_pct`).
- Happy path: `load_shot_profile(SEASON)` returns a DataFrame with 30 rows and
  the 7 zone `_pct_of_fga` columns.
- Edge case: calling with a season not present in the DB returns an empty
  DataFrame (not an error) — confirms the WHERE clause behaves as filtering,
  not an implicit join/crash.

**Verification:** Both functions run against the real `nba_strategy.db` and
return non-empty, correctly-shaped DataFrames for the current season.

---

### U2. League-wide comparison table view

**Goal:** Render the sortable, all-30-teams ratings table.

**Requirements:** R1, R4

**Dependencies:** U1

**Files:**
- `dashboard/views/league.py` (new)

**Approach:** Use `st.dataframe` (not `st.table`) so the built-in column-sort
UI satisfies R1 without custom sort-state code. Round displayed values to 1
decimal for pace/ratings and format `ts_pct` as a percentage for readability.

**Patterns to follow:** N/A (first UI code in the project) — follow Streamlit's
own `st.dataframe` conventions rather than inventing a custom table.

**Test scenarios:**
- Happy path: given the U1 DataFrame, the rendered table includes all 30 team
  names and the 5 ratings columns.
- Test expectation: no additional edge-case tests — this is a thin rendering
  wrapper over an already-tested data function; visual correctness is
  confirmed manually per Verification below.

**Verification:** Running the app and viewing the league page shows 30 rows,
sortable by clicking any column header, with the Thunder/Spurs/Pistons-type
top-net-rating ordering matching the known sanity-check output from
`transform_team_stats.py`.

---

### U3. Team detail view with shot-profile chart

**Goal:** Given a selected team, show that team's shot-mix profile as a chart
(not just a numbers table) so zone tendencies are visually obvious.

**Requirements:** R2, R3

**Dependencies:** U1

**Files:**
- `dashboard/views/team_detail.py` (new)

**Approach:** A horizontal bar chart (`st.bar_chart`, or a simple layout using
`st.columns`) with the 7 zones on one axis and `_pct_of_fga` on the other,
so a team's mix is scannable at a glance. Show `_fg_pct` per zone alongside
(e.g., as a second bar or as text labels) so both volume and efficiency are
visible together — this is the "what makes each team unique" signal from
`STRATEGY.md`. Exclude the redundant `corner_3` combined column (already
excluded in `mart_team_shot_profile` — see
`docs/solutions/design-patterns/flattening-nested-nba-api-headers.md`).

**Technical design (directional):**
```
zones = [restricted_area, in_the_paint_non_ra, mid_range,
         left_corner_3, right_corner_3, above_the_break_3, backcourt]
for each zone: bar height = <zone>_pct_of_fga, label/tooltip = <zone>_fg_pct
```

**Patterns to follow:** U1's `load_shot_profile`.

**Test scenarios:**
- Happy path: selecting a team known to be 3-heavy (e.g., Celtics per the
  transform's sanity check) shows a visibly higher above_the_break_3 bar than
  a team known to be rim-heavy.
- Edge case: selecting a team with no attempts in a zone (if any exist) renders
  a zero-height bar, not an error.

**Verification:** Selecting several different teams produces visibly different
shot-mix shapes, matching what's expected from real-world knowledge of those
teams' offenses.

---

### U4. App entry point and navigation

**Goal:** Wire U2 and U3 together into one runnable app with a way to switch
between the league table and a specific team's detail view.

**Requirements:** R1, R2

**Dependencies:** U1, U2, U3

**Files:**
- `dashboard/app.py` (new)

**Approach:** Sidebar with a mode selector ("League Overview" vs "Team Detail").
In Team Detail mode, a second sidebar selectbox (populated from
`load_team_stats()["team_name"]`) picks the team, satisfying R2's
"select a team" requirement without needing `st.dataframe` row-click events
(which Streamlit doesn't support natively without extra components).

**Patterns to follow:** KTD2 (single-file view-selection pattern).

**Test scenarios:**
- Test expectation: none — this unit is wiring/composition of already-tested
  U2/U3 view functions; correctness is verified by running the app (see
  Verification), not unit tests.

**Verification:** `streamlit run dashboard/app.py` starts without error;
switching between League Overview and Team Detail (for at least 3 different
teams) works without a page reload delay noticeable to the user.

---

## Scope Boundaries

**Deferred to Follow-Up Work:**
- Multi-page `st.navigation` structure (only worth it if the app grows past
  the two views built here)
- `st.cache_data` / performance tuning (KTD4 — no evidence yet that it's needed)
- Any AI/NL-to-SQL feature (explicitly Phase 2+ per `STRATEGY.md`)
- Historical/season-over-season comparison (only current season is in the DB)

**Out of scope:**
- Deployment/hosting — this plan covers running the dashboard locally only

## Dependencies / Prerequisites

- Add `streamlit` to `requirements.txt` and install it in the project's venv
  before U4 can be verified.

## Verification Contract

- `python -c "import streamlit"` succeeds after the dependency is installed.
- `streamlit run dashboard/app.py` launches without exceptions.
- League Overview page renders all 30 teams; Team Detail page renders a
  shot-mix chart that visibly differs across at least 3 selected teams.

## Definition of Done

- U1-U4 implemented and manually verified per each unit's Verification.
- `requirements.txt` updated with `streamlit`.
- Dashboard runs end-to-end via `streamlit run dashboard/app.py` against the
  real `nba_strategy.db`.
