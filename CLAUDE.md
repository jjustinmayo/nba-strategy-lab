# NBA Strategy Lab

Learning project: building an NBA on-court performance/strategy pipeline + dashboard
end-to-end, as if working as a data/AI engineer for an NBA team. User is intermediate
in SQL, beginner in Python, has never built a full end-to-end data pipeline before.
Goal is to learn data engineering and AI engineering principles through a real,
iteratively-built project (not just tutorials).

## Phase plan
- **Phase 1 (current): MVP dashboard.** Pull league-wide stats via an NBA stats API,
  land in a local database, transform with SQL, show in a simple dashboard. No AI yet.
- **Phase 2:** deeper data model (lineups, clutch, shot profiles), dbt for transforms,
  basic scheduling/orchestration, first AI feature (NL-to-SQL agent).
- **Phase 3:** cloud warehouse, CI/CD, monitoring, agent evaluation/guardrails.

## Working style
- User is learning DE/AI engineering for the job market, not just trying to ship fast.
  Explain new concepts briefly when introducing them, especially Python and DE tooling.
- Plan before building: for non-trivial steps, lay out the approach and get explicit
  sign-off before writing code, rather than building straight from a one-line prompt.
- User wants to review diffs/code during early phases as part of learning — don't skip
  explanation in favor of speed.
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
- **Don't rubber-stamp diffs at scale** is the long-term direction (lean on tests/
  validation instead of manually reviewing every line) — but deliberately NOT
  followed yet in this project's early phases, since the user wants to read and
  understand the code as a learning mechanism. Revisit this once the user is more
  comfortable with the stack.

**Where we left off:** project folder and git repo created, this memory file
written, Phase 1 not yet started. Next decision point is picking the concrete data
source (leaning toward `nba_api`, a free Python wrapper around stats.nba.com) and
standing up the first ingestion script.
