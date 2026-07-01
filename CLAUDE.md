# NBA Strategy Lab

Building an NBA on-court performance/strategy pipeline + dashboard end-to-end.
User directs scope and judges the project by outcome (is it accurate, fast,
useful, interesting) — not by understanding or reviewing the implementation.
User is intermediate in SQL, beginner in Python, and has deliberately chosen
to spend their time learning how to direct an AI agent to build a real project
well (a "non-technical founder" posture) rather than learning to code or the
DE/AI concepts themselves. See STRATEGY.md for the full problem/approach/tracks.

## Phase plan
- **Phase 1 (current): MVP dashboard.** Pull league-wide stats via an NBA stats API,
  land in a local database, transform with SQL, show in a simple dashboard. No AI yet.
- **Phase 2:** deeper data model (lineups, clutch, shot profiles), dbt for transforms,
  basic scheduling/orchestration, first AI feature (NL-to-SQL agent).
- **Phase 3:** cloud warehouse, CI/CD, monitoring, agent evaluation/guardrails.

## Working style
- User judges this project by outcome (accuracy, speed, usefulness, "that's cool"
  insight moments), not by understanding the code. Do not default to explaining
  Python/DE concepts or walking through diffs line-by-line unless asked — implement,
  then report results in outcome terms (what it does, what it shows, whether it
  works), not implementation terms.
- Plan before building: for non-trivial steps, lay out the approach and get explicit
  sign-off before writing code, rather than building straight from a one-line prompt.
  Sign-off is about scope/direction, not code review.
- **Standing CE workflow for non-trivial work:** `/ce-plan` to produce a structured
  plan doc before code is written, `/ce-work` to execute against that plan (diffs
  still reviewable if asked), `/ce-compound` after the session to capture durable
  learnings in `docs/solutions/` (organized by category, e.g. `design-patterns/`,
  with YAML frontmatter — search it before implementing or debugging in an area
  it might already cover). Small/obvious changes don't need the full loop — use
  judgment on what counts as "non-trivial."
- Still apply DE/software best practices under the hood (see Conventions below) even
  though the user won't review them — quality here is enforced by the agent, not by
  user inspection.
- **Git/GitHub actions: user runs these themselves, not the agent.** User is
  deliberately building muscle memory for `git status`/`add`/`commit`/`pull`/`push`,
  branching, and conflict resolution. Default to telling the user the exact command(s)
  to run and what to expect, rather than running git commands for them. Exceptions:
  the agent may run read-only git commands (`status`, `log`, `diff`, `branch`) to gather
  context for an explanation, and may still run git commands itself if the user
  explicitly asks the agent to handle a specific git action.
- Default to the simplest file/process structure that works; don't pre-build
  structure (extra .md files, automation, tooling) before there's a real,
  repeated pain point. When a manual step starts being done every session, or
  a file (e.g. CLAUDE.md) starts mixing stable rules with frequently-changing
  state, proactively flag it and recommend a concrete fix (e.g. splitting into
  a new file, scripting a manual step) rather than waiting to be asked.

## Conventions

### Data engineering principles (applies from Phase 1 onward)
- **Raw vs. transformed separation**: land data from the API as-is in a
  `raw`/staging area first; never transform in place. SQL transforms read
  from raw and write to a separate `analytics`/`marts` layer. This keeps
  you able to re-run transforms without re-pulling the API, and keeps a
  source of truth if a transform has a bug.
- **Idempotent ingestion**: re-running the same ingestion script for the
  same date/data range should not create duplicates or fail. Prefer
  upsert/replace logic over blind inserts.
- **Config over hardcoding**: API keys, file paths, DB connection strings
  go in a config/env file (not committed to git), not hardcoded in scripts.
- **Naming convention**: tables/columns use `snake_case`; raw tables
  prefixed `raw_`, transformed tables prefixed by their layer (e.g.
  `stg_`, `mart_`) once Phase 2 introduces dbt-style layering.
- **One script, one responsibility**: ingestion, transform, and
  dashboard-serving logic live in separate scripts/modules, not one
  monolithic file — makes it easier to test and debug each stage alone.
- **Sanity-check after each pipeline stage**: after ingesting or
  transforming, do a basic row-count/spot-check before moving to the next
  stage, rather than assuming success.

### Cross-device & git workflow
- **Cross-device continuity:** user works on this repo from multiple desktops.
  Claude Code session/chat history is stored locally per machine and does not
  sync between devices — only what's committed to this repo carries over. So:
  keep this file current with decisions/progress as they happen, commit often,
  and treat git history + this file (not chat history) as the source of truth
  for "where things stand" at the start of any new session on any machine.
- **Git workflow:** practicing real-world habits intentionally, not just
  shipping fast, since that's part of the learning goal:
  - Branch per feature/task (e.g. `feat/ingest-script`), merge into `main` via
    PR even though working solo — gives a review checkpoint and a PR
    description documenting *why*, not just *what*. Delete branches after merge.
  - `git pull` on `main` at the start of every session on either desktop before
    branching, to avoid branching off stale history.
  - Never commit secrets (API keys, tokens, DB connection strings) — always
    via `.env`, which is gitignored. Don't hardcode credentials in scripts.
  - Don't commit data artifacts (raw pulls, exports, local DB files) — they're
    regenerable from the pipeline, not source of truth. `.gitignore` already
    covers `*.db`/`*.sqlite`; extend it as new artifact types show up (CSV
    exports, parquet, etc.).
  - Small, focused commits with messages explaining why — easier to review
    and revert independently.

## Context recap (from prior planning session)

This project was scoped in a separate chat before this folder existed. Recap of
how we got here, for any new session picking this up cold:

**Why this project:** user wants to learn data engineering and AI engineering
principles realistically, as if employed by an NBA team — not just follow a
tutorial. Plan → build → test → validate, with the user directing scope/decisions
and the agent doing most of the implementation, explaining concepts along the way
(user is intermediate at SQL, beginner at Python, has never shipped an end-to-end
data pipeline).

**How we landed on the project:** considered several NBA analytics concepts
(game-recap generation, NL-to-SQL front-office agent, injury/load-management risk
scoring, scouting-report RAG). User is most interested in on-court
performance/strategy, league-wide (not one team), and wants the AI layer decided
by whichever fits the data work best. Settled on "Strategy Lab": a league-wide
pipeline + dashboard on lineup/clutch/shot-profile analytics, with a natural-language-
to-SQL agent as the AI engineering centerpiece (chosen over recap-generation or
pure ML because it's closest to a real "AI engineer embedded with an analytics
team" deliverable, and teaches schema-grounding, tool-calling, and guardrails).

**Why 3 phases:** iterative build-up so each stage teaches a bounded set of new
concepts instead of everything at once. See Phase plan above — Phase 1 is
deliberately minimal/local with no AI; Phase 2 adds production-style rigor (dbt,
orchestration) plus the first AI feature; Phase 3 adds cloud/CI-CD/observability
and hardens the AI agent with evaluation and guardrails.

**Agentic-engineering framework adopted from a video (Kun, ex-Meta/Microsoft/
Atlassian principal engineer) on how to work with coding agents effectively.**
Core ideas being applied here, in plain terms:
- **Agent** = an active session of an AI assistant that can read/write files and
  run commands in a project folder, not just talk. Each chat session is its own
  independent "worker" with no memory of other sessions unless context is shared
  via files.
- **Memory files** (this `CLAUDE.md`) are how a brand-new agent session gets
  onboarded without the user re-explaining everything. Global preferences should
  stay short (loaded into every prompt); project-specific knowledge can be more
  verbose and should grow incrementally — every time the agent makes a mistake,
  the fix/lesson gets written down here so it isn't repeated.
- **Skills** are for conditionally-relevant instructions (only loaded when
  actually needed) — not used yet in this project, but the mechanism to reach for
  once this file gets bloated with instructions that only apply in specific
  situations.
- **Plan before building**: for non-trivial work, agree on the approach explicitly
  before code gets written, rather than letting the agent build straight from a
  one-line prompt.
- **Don't rubber-stamp diffs at scale**: as of 2026-06-30 the user shifted from a
  code-review-as-learning posture to judging by outcome only (see STRATEGY.md) —
  so the agent leans on tests/validation/sanity-checks to catch bugs itself,
  rather than expecting the user to catch them via code review.

**Where we left off (Phase 1 — first ingestion done):**
- **Data source chosen:** `nba_api` (free, no API key, wraps stats.nba.com; already
  exposes the lineup/clutch/shot endpoints we grow into later, so no source switch
  between phases).
- **First ingestion built + validated:** `ingest_team_stats.py` pulls
  `LeagueDashTeamStats` for the current season (`2025-26`) and lands it AS-IS in a
  `raw_team_stats` table in a local SQLite DB (`nba_strategy.db`). Idempotent per
  season (delete-then-insert). 30 teams; 54 API columns + 2 lineage columns
  (`season`, `ingested_at`); sanity-checked against known standings.
- **Pandas-free on purpose:** ingestion uses only the stdlib `sqlite3` + the API's raw
  `get_dict()` (no DataFrame layer) — see Environment note for why.
- **Files added:** `config.py` (settings), `ingest_team_stats.py` (ingestion),
  `requirements.txt` (pinned deps), `PYTHON_NOTES.md` (Python learning notes).
- **DB for Phase 1:** SQLite (local file, zero-setup; graduate to Postgres/warehouse later).
- **Next:** the transform ("T") layer — prototype strategy metrics (pace, offensive/
  defensive efficiency, shot profiles) in a notebook with pandas, then formalize the
  chosen transforms into a transform script writing a separate `analytics`/`mart` table
  (preserving raw->analytics separation).

## Environment & setup

- **Develop inside WSL/Ubuntu (Linux), not native Windows.** Windows **Smart App
  Control** (enforced on the primary dev machine) blocks pandas' compiled binaries
  (`ImportError: ... An Application Control policy has blocked this file`); numpy was
  fine, only pandas was flagged. Rather than disable a security feature or adopt a
  niche pandas-free workaround as the long-term path, the project moved to WSL — which
  also makes local dev mirror the Linux servers/containers everything eventually runs
  on. Any other Windows desktop will likely hit the same wall, so use WSL there too.
- **Per-machine setup (inside WSL):**
  ```bash
  cd ~ && git clone <repo-url> && cd nba-strategy-lab
  git checkout <feature-branch>
  python3 -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt
  ```
  Keep the project in the Linux filesystem (`~/...`), NOT under `/mnt/c` (slow). Open in
  VS Code via `code .` from the project dir (Remote-WSL; look for the `WSL: Ubuntu` badge).
- **venv activation differs by OS:** `source .venv/bin/activate` (Linux) vs
  `.venv\Scripts\Activate.ps1` (Windows PowerShell).
