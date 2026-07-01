---
name: NBA Strategy Lab
last_updated: 2026-06-30
---

# NBA Strategy Lab Strategy

## Target problem

I don't know how to code or follow best practices for shipping a high-quality, valuable software project — I've never built or shipped one before. I want a real project to learn what it takes to direct an AI agent to build something well, without myself having to become the one who writes or deeply understands the code.

## Our approach

The agent implements essentially all of the code; I direct scope and judge everything by whether the result works and is genuinely useful and interesting, not by whether I understand how it was built. This is a deliberate shift from treating this as a coding-education project to treating it as a "non-technical founder directing a build" project — I invest my time in deciding what to build and evaluating outcomes, not in learning to code.

## Who it's for

**Primary:** Me, as an engaged NBA fan interested in the analytics/strategy side of the game — hiring this dashboard to surface what makes each team unique (schemes, gameplan, roster strengths/weaknesses) in ways mainstream stat sites don't show.

## Key metrics

- **Weekly self-usage** - do I open the dashboard unprompted at least once in a given week
- **Data accuracy** - spot-checks of dashboard numbers against official NBA stats match
- **Insight density** - number of "didn't know that, that's cool" moments per session
- **Load/refresh speed** - dashboard loads and updates quickly when parameters change

## Tracks

### Data pipeline

Ingesting and transforming NBA data reliably and accurately (raw → analytics layers).

_Why it serves the approach:_ Everything downstream is worthless if the underlying data isn't trustworthy — this is the foundation the agent has to get right without my ability to catch subtle bugs myself.

### Analytics / insights

Defining the strategy metrics and findings (pace, efficiency, shot profiles, clutch performance, etc.) that actually reveal what makes a team unique.

_Why it serves the approach:_ This is where the "wow, didn't know that" moments come from — the actual value the persona is hiring the product for.

### Dashboard / UX

Fast, visually appealing, easy-to-interpret presentation of the analytics.

_Why it serves the approach:_ I judge success by outcome and usefulness, not implementation — the UX is the surface I'll actually be judging the project by.

### AI features

NL-to-SQL and future agentic capabilities layered on top of the data/analytics foundation.

_Why it serves the approach:_ Matches the project's original phase plan (Phase 2+) and is the natural extension of directing an agent rather than hand-coding.
