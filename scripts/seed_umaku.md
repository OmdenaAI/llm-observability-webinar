# Seeding the Umaku Workspace

This is a manual, one-time setup step (not automated) — Umaku is a hosted
platform, not something we stand up locally, so seeding means populating a
real project via Umaku's own UI or API before the demo.

## Required state before any dry run

1. **An organization + project** created in Umaku, dedicated to this demo
   (do not reuse a real work project — read-only calls are safe, but keep
   this isolated in case scope ever expands to writes later).
2. **An active sprint** with a name and date range — required for
   `sprints_get_active` to return something non-empty.
3. **A populated kanban board** for that sprint — at least 8-10 tasks
   across a few columns (To Do / In Progress / Done), so
   `kanban_get_board` produces a visually interesting board on screen.
   Remember: `kanban_get_board` requires an explicit `sprint_ids` argument —
   it will not default to the active sprint.
4. **Enough historical sprint data** (at least 1-2 prior completed sprints)
   so `projects_get_dashboard` shows a trend, not just a single data point.
5. **Enough activity/history** for `performance_assessments_by_project` to
   generate a meaningful assessment — check Umaku's docs for the minimum
   data needed to trigger this (may require some completed tasks with
   logged hours, comments, or commits).

## Getting the MCP token

1. Generate a personal access token from Umaku's account settings.
2. Add it to `.env` as `UMAKU_MCP_TOKEN`.
3. Confirm the connection with the `health_check` MCP tool before the first
   dry run — see docs/preflight_checklist.md.

## Open question
Confirm with Umaku (or their docs) what data/activity is actually required
to trigger a performance assessment — if it needs to be manually generated
per sprint rather than computed automatically, that becomes a required seed
step here too, not just historical data.
