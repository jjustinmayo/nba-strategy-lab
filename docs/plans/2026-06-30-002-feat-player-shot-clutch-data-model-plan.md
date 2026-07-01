---
artifact_contract: ce-unified-plan/v1
artifact_readiness: implementation-ready
execution: code
product_contract_source: ce-plan-bootstrap
date: 2026-06-30
---

# feat: Player shot-profile and clutch data model

## Summary

Extend the data model with two player-level slices — shot profiles and clutch
performance — mirroring the existing team-level ingest/transform pattern.
This is data-model-only work: no dashboard changes are included here (deferred
to a follow-up plan). Scoped down from a broader "deeper data model" request
after reviewing `nba_api`'s available endpoints (274 total) with the user;
player shot profiles and clutch were chosen as the most direct, lowest-risk
extension of work already shipped, with play-type/scheme data and lineups
explicitly deferred.

## Problem Frame

The dashboard currently only slices by team (`mart_team_stats`,
`mart_team_shot_profile`). Per `STRATEGY.md`, the goal is surfacing "what
makes each team unique" — player-level data is a natural next axis (which
players drive a team's shot profile or clutch performance). `nba_api` exposes
player-level analogs of both existing team endpoints
(`LeagueDashPlayerShotLocations`, `LeagueDashPlayerClutch`), confirmed live
against the current season: 582 player rows for shot locations, 492 for
clutch, both with `PLAYER_ID` unique per row this season (no trade-driven
duplicates observed yet).

## Key Technical Decisions

- **KTD1 — Reuse the header-flattening pattern for shot locations.**
  `LeagueDashPlayerShotLocations` returns the same nested/grouped header shape
  (`SHOT_CATEGORY` zone groups) as the team version. Apply the exact pattern
  documented in
  `docs/solutions/design-patterns/flattening-nested-nba-api-headers.md` —
  same zone list, same exclusion of the duplicate `corner_3` combined column.
- **KTD2 — Clutch ratings computed per-100-clutch-possessions, not per-48
  pace.** Clutch minutes per player per season are small (confirmed: most
  players have single-digit clutch minutes), so a per-48-minute pace figure
  isn't meaningful the way it is for full-season team totals. Compute
  `clutch_ts_pct` and a per-100-clutch-possession scoring rate instead,
  reusing the same possession estimator formula
  (`FGA - OREB + TOV + 0.4*FTA`) from `transform_team_stats.py`, applied to
  clutch-only totals.
- **KTD3 — Zero-clutch-possession players are not filtered out.** Confirmed
  via live query: at least one player has 0 clutch FGA/FTA/TOV (0 estimated
  possessions), which would divide-by-zero in the ratio formulas. Land these
  rows with `NULL` derived metrics (SQLite returns `NULL`, not an error, for
  division by zero) rather than excluding the player — raw and mart both stay
  complete; a future dashboard consumer decides how to handle low-sample
  players (e.g., a minimum-clutch-minutes filter), which is out of scope here.
- **KTD4 — Idempotency key stays `(PLAYER_ID or TEAM_ID, season)`,
  unchanged from the existing convention.** Known limitation, not solved in
  this plan: a player traded mid-season could appear on multiple teams within
  one season pull later in the year (not observed in the current early-season
  data). Documented as a deferred edge case, not blocking this work.
- **KTD5 — No dashboard changes in this plan.** Confirmed with user: this
  plan stops at validated raw/mart tables. Wiring player data into
  `dashboard/` is a separate follow-up plan.

## Requirements

- **R1**: Land `LeagueDashPlayerShotLocations` AS-IS into
  `raw_player_shot_locations`, using the flattened zone-column naming from
  KTD1.
- **R2**: Transform `raw_player_shot_locations` into
  `mart_player_shot_profile` — same shot-mix % and FG% per zone as
  `mart_team_shot_profile`, but per player.
- **R3**: Land `LeagueDashPlayerClutch` AS-IS into `raw_player_clutch`.
- **R4**: Transform `raw_player_clutch` into `mart_player_clutch` — clutch
  `ts_pct` and points-per-100-clutch-possessions per player, per KTD2/KTD3.
- **R5**: Both ingestion scripts are idempotent per season (delete-then-insert
  matching the existing team scripts).
- **R6**: Both transform scripts read only from their `raw_` tables and write
  only to their `mart_` tables — no cross-writes, preserving the raw/mart
  separation convention.

## Implementation Units

### U1. Ingest player shot locations

**Goal:** Land `LeagueDashPlayerShotLocations` into `raw_player_shot_locations`.

**Requirements:** R1, R5

**Dependencies:** None

**Files:**
- `ingest_player_shot_locations.py` (new)

**Approach:** Directly mirror `ingest_team_shot_locations.py`'s structure —
same header-flattening helper (`_snake_case`, zone-group parsing via
`columnsToSkip`), same idempotent delete-then-insert per season, same
sanity-check pattern. The only differences: call
`leaguedashplayershotlocations.LeagueDashPlayerShotLocations` instead of the
team endpoint, and the raw table carries `PLAYER_ID`/`PLAYER_NAME` (plus
`TEAM_ID`/`TEAM_ABBREVIATION`, which the player endpoint also returns)
instead of just `TEAM_ID`/`TEAM_NAME`.

**Patterns to follow:** `ingest_team_shot_locations.py` (structure, header
flattening); `docs/solutions/design-patterns/flattening-nested-nba-api-headers.md`
(the pattern's rationale and gotchas, including the corner_3 duplicate-zone
note).

**Test scenarios:**
- Happy path: running the script lands 582 rows (per the live probe) in
  `raw_player_shot_locations` for the current season, with flattened columns
  matching the same 7-zone + corner_3 naming as the team table.
- Idempotency: running the script twice for the same season replaces rows
  rather than duplicating them (row count stays the same after a second run).
- Edge case: a player with 0 attempts in a zone lands as `0`, not `NULL` or
  an error (the API returns `0` for zero attempts, not a missing value).

**Verification:** Row count matches the live API row count for the season;
spot-check a known high-volume 3-point shooter's `above_the_break_3_fga`
against the raw API response.

---

### U2. Transform player shot profile

**Goal:** Compute per-player shot-mix percentages into `mart_player_shot_profile`.

**Requirements:** R2, R6

**Dependencies:** U1

**Files:**
- `transform_player_shot_profile.py` (new)

**Approach:** Mirror `transform_team_shot_profile.py` exactly — same `ZONES`
list (excluding `corner_3`), same `pct_of_fga` calculation, same idempotent
delete-then-insert. Swap `team_id`/`team_name` for `player_id`/`player_name`
(carry `team_id`/`team_abbreviation` through as well, since a player's shot
profile is only meaningful alongside which team they played for).

**Patterns to follow:** `transform_team_shot_profile.py`.

**Test scenarios:**
- Happy path: transform produces one row per player in
  `raw_player_shot_locations` for the season, with `pct_of_fga` values across
  the 7 zones summing to ~100% per player.
- Edge case: a player with 0 total FGA across all zones (division by zero in
  the `pct_of_fga` denominator) lands with `NULL` percentage columns rather
  than crashing the script.
- Happy path: a known 3-point specialist shows a visibly higher
  `above_the_break_3_pct_of_fga` than a known low-volume-3 big man, confirming
  the transform's numbers are sane.

**Verification:** Row count matches U1's `raw_player_shot_locations` row
count; spot-check 2-3 well-known players' shot mixes against real-world
expectations.

---

### U3. Ingest player clutch stats

**Goal:** Land `LeagueDashPlayerClutch` into `raw_player_clutch`.

**Requirements:** R3, R5

**Dependencies:** None

**Files:**
- `ingest_player_clutch.py` (new)

**Approach:** Mirror `ingest_team_stats.py`'s structure (flat headers, no
flattening needed — confirmed via live probe that `LeagueDashPlayerClutch`
returns a flat header list, unlike the shot-locations endpoints). Use the
endpoint's default clutch definition (`clutch_time='Last 5 Minutes'`,
`ahead_behind='Ahead or Behind'`, `point_diff='5'` — the NBA's standard
"clutch time" definition) rather than overriding parameters.

**Patterns to follow:** `ingest_team_stats.py` (flat-header ingestion,
idempotent per-season pattern).

**Test scenarios:**
- Happy path: running the script lands 492 rows (per the live probe) in
  `raw_player_clutch` for the current season.
- Idempotency: running the script twice for the same season replaces rows
  rather than duplicating them.
- Edge case: a player with 0 clutch minutes/attempts still lands as a row
  with `0` values (API returns `0`, not omission) — needed for U4's
  divide-by-zero handling to have a real row to test against.

**Verification:** Row count matches the live API row count for the season;
spot-check a known clutch performer's `PTS`/`FG_PCT` in clutch situations
against the raw API response.

---

### U4. Transform player clutch ratings

**Goal:** Compute clutch efficiency metrics (`ts_pct`,
points-per-100-clutch-possessions) into `mart_player_clutch`.

**Requirements:** R4, R6

**Dependencies:** U3

**Files:**
- `transform_player_clutch.py` (new)

**Approach:** Reuse `transform_team_stats.py`'s possession-estimator and
`ts_pct` formulas (`poss_est = FGA - OREB + TOV + 0.4*FTA`,
`ts_pct = 100 * PTS / (2 * (FGA + 0.44*FTA))`), applied to `raw_player_clutch`
totals instead of season totals, and applied per-100-clutch-possessions
instead of per-48-minutes (KTD2). Omit a `pace` column entirely — it isn't
meaningful for clutch-only samples. Per KTD3, do not filter out
zero-possession players; let the division return `NULL` for those rows.

**Technical design (directional):**
```
clutch_poss_est = FGA - OREB + TOV + 0.4*FTA
clutch_pts_per100 = 100 * PTS / clutch_poss_est   -- NULL when clutch_poss_est = 0
clutch_ts_pct     = 100 * PTS / (2 * (FGA + 0.44*FTA))  -- NULL when denominator = 0
```

**Patterns to follow:** `transform_team_stats.py` (formula reuse, idempotent
transform structure).

**Test scenarios:**
- Happy path: transform produces one row per player in `raw_player_clutch`
  for the season, with `clutch_pts_per100` and `clutch_ts_pct` populated for
  players with nonzero clutch possessions.
- Edge case: a player with 0 clutch FGA/FTA/TOV (0 estimated possessions, per
  the live probe's confirmed example) lands with `NULL` in both derived
  columns rather than the script raising a division error.
- Happy path: a player known for strong clutch scoring efficiency shows a
  higher `clutch_ts_pct` than a low-efficiency clutch performer, confirming
  the transform's numbers are sane.

**Verification:** Row count matches U3's `raw_player_clutch` row count; the
zero-possession edge case produces `NULL` (not a crash, not a fabricated 0)
when the script runs against real data.

---

## Scope Boundaries

**Deferred to Follow-Up Work:**
- Dashboard integration for player data (player search/detail view) — KTD5
- `SynergyPlayTypes` (play-type/scheme mix) — most interesting for the "why
  does this team play this way" insight, but requires ~10 API calls per pull
  (one per play type) and percentile-based stats; scoped out to keep this
  plan cohesive
- `LeagueHustleStatsPlayer` (effort/motor metrics) and `LeagueDashPtStats`
  (tracking: drives, touches, passes) — good complements, not chosen for this
  round
- `LeagueDashLineups` (5-man combination data) — new entity type (lineup, not
  player or team), needs a minutes-played filter to be usable at 2000+ raw
  rows; higher complexity, deferred
- Minimum-clutch-minutes filtering for meaningful sample size (KTD3) — left
  to whichever consumer (dashboard) reads `mart_player_clutch`
- Handling mid-season trades producing duplicate `PLAYER_ID` rows per season
  (KTD4) — not yet observed in current data, deferred until it's a real
  problem

## Verification Contract

- `raw_player_shot_locations` row count matches the live
  `LeagueDashPlayerShotLocations` API row count for the season.
- `raw_player_clutch` row count matches the live `LeagueDashPlayerClutch` API
  row count for the season.
- `mart_player_shot_profile` and `mart_player_clutch` row counts match their
  respective raw tables.
- Re-running any of the 4 scripts for the same season does not change row
  counts (idempotent).
- No script raises an unhandled exception on the zero-possession edge case.

## Definition of Done

- U1-U4 implemented and manually verified per each unit's Verification.
- All 4 scripts follow the existing raw/mart separation and idempotent
  ingestion conventions.
- Sanity-check output (per the project's "sanity-check after each pipeline
  stage" convention) printed for each script, spot-checking at least 2-3
  known players per table.
