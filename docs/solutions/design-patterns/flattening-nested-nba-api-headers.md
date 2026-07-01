---
title: Flattening nba_api's nested/grouped headers for raw SQL landing
date: 2026-06-30
category: design-patterns
module: ingestion
problem_type: design_pattern
component: tooling
severity: low
applies_when:
  - "Landing an nba_api endpoint whose resultSets.headers is a list of grouped header objects (e.g. one FGM/FGA/FG_PCT triplet per shot zone) instead of a flat list of column name strings"
tags: [nba-api, ingestion, sqlite, raw-layer, header-flattening]
---

# Flattening nba_api's nested/grouped headers for raw SQL landing

## Context

`ingest_team_stats.py` (using `leaguedashteamstats`) gets a flat `headers` list
back from `get_dict()["resultSets"][0]`, so each header string maps directly
to one SQL column. Building `ingest_team_shot_locations.py` against
`leaguedashteamshotlocations` hit a different shape: `resultSets` is a dict
(not a list) whose `headers` is two grouped objects — one naming the 8 shot
zones (`SHOT_CATEGORY`, with a `columnsToSkip` count and a `columnNames` list
of zone labels), and one naming the repeating per-zone stat triplet
(`FGM`, `FGA`, `FG_PCT`). Nested headers like this aren't valid SQL column
names, and several other nba_api endpoints likely to matter later in this
project (lineups, clutch splits, potentially shot-chart detail) use the same
grouped-header convention.

## Guidance

Flatten each `(zone, stat)` pair into one column name at ingestion time —
e.g. `above_the_break_3_fga` — rather than trying to preserve the nested
shape in SQL. This is naming only, not a transformation of any value: every
number still lands exactly as the API returned it, so it doesn't violate the
project's raw-layer-stays-AS-IS convention.

```python
skip = zone_group["columnsToSkip"]
stat_names = columns_group["columnNames"][skip:]  # e.g. ["FGM", "FGA", "FG_PCT"]

headers = columns_group["columnNames"][:skip]  # leading TEAM_ID, TEAM_NAME
for zone in zone_group["columnNames"]:
    zone_slug = _snake_case(zone)  # "Above the Break 3" -> "above_the_break_3"
    for i in range(3):
        headers.append(f"{zone_slug}_{stat_names[i].lower()}")
```

The rest of the ingestion script (idempotent per-season delete-then-insert,
`CREATE TABLE IF NOT EXISTS` with no declared types, parameterized insert)
is unchanged from the flat-header case in `ingest_team_stats.py`.

## Why This Matters

Without flattening, the API's grouped-header response can't be inserted into
SQLite at all (SQL has no concept of a nested/grouped column), and hand-typing
zone-specific column lists would be brittle if the API adds or reorders
zones. Deriving the flat names from `columnNames` at runtime means the script
adapts automatically if the API's zone set changes.

Also watch for **duplicate/derived groups** in a grouped header: this
endpoint's zone list includes a `Corner 3` group that is the sum of
`Left Corner 3` + `Right Corner 3`. Landing it in raw is fine (it's still an
AS-IS API value), but any transform computing a shot-mix percentage must
exclude it from the mix denominator or attempts get double-counted — see
`transform_team_shot_profile.py`'s `ZONES` list, which deliberately omits
`corner_3`.

## When to Apply

- Before writing a new `ingest_*.py` script against an nba_api endpoint,
  inspect `get_dict()["resultSets"]` interactively first — if `headers` is a
  list of dicts (each with a `columnNames` list) instead of a flat list of
  strings, this pattern applies.
- Also applies to any transform reading a raw table built this way: check
  whether the raw zones/groups overlap (like `corner_3` above) before summing
  or computing percentages across them.

## Examples

Flat-header endpoint (`leaguedashteamstats`) — no flattening needed:
```python
result_set = endpoint.get_dict()["resultSets"][0]
headers = result_set["headers"]  # already a flat list of strings
```

Grouped-header endpoint (`leaguedashteamshotlocations`) — flattening required,
as shown in Guidance above.

## Related

- `ingest_team_stats.py` — flat-header ingestion pattern (idempotent per-season landing)
- `transform_team_stats.py` — raw-to-mart transform pattern this project follows
- `ingest_team_shot_locations.py`, `transform_team_shot_profile.py` — this pattern in use
