# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Habit Focus Observatory is a local-only MVP portfolio project for personal habit/energy/focus
analytics. Streamlit logging forms write to PostgreSQL; SQL/dbt views roll the data up into
daily analytics that drive review charts and plain-English insight summaries.

## Commands

```bash
# Environment
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # Postgres connection env vars (PGHOST, PGUSER, ...)

# Database (Postgres runs in Docker)
docker compose up -d
docker exec -i habit_focus_postgres psql -U habit_user -d habit_focus_db < sql/schema.sql
docker exec -i habit_focus_postgres psql -U habit_user -d habit_focus_db < sql/views.sql

# Data
python -m src.ingest                  # load sample CSVs from data/
python scripts/load_demo_data.py      # deterministic 30-day demo window (2026-01-01..30)

# Run the app
streamlit run app/streamlit_app.py

# Tests
pytest                                # all tests
pytest tests/test_analytics.py        # one file
pytest tests/test_analytics.py::test_completeness_summary_appears   # one test

# dbt (alternative to sql/views.sql; same view names)
cp profiles.yml.example profiles.yml  # or use DBT_PROFILES_DIR=.
DBT_PROFILES_DIR=. dbt run
DBT_PROFILES_DIR=. dbt test
```

## Architecture

Data flows in one direction:

```
Streamlit forms (app/) -> src/habit_repository.py -> Postgres tables -> analytics views -> review charts + insights
```

- `app/streamlit_app.py` — single-page entrypoint; prepends the repo root to `sys.path` so
  `app.*` and `src.*` import cleanly. Renders four independent forms (today's morning check-in,
  yesterday's deep work / caffeine / exercise) plus the review section.
- `app/forms.py`, `app/review.py`, `app/charts.py` — form rendering, the Recent Trends & Review
  section, and Altair chart builders.
- `src/habit_repository.py` — all DB read/write helpers. Writes are per-section upserts; reads
  feed both form preloading and the review dashboard.
- `src/analytics.py` — pure pandas insight builders (no DB). All functions guard for missing
  columns / insufficient days and return cautious comparison strings; this is what the unit tests
  cover.
- `src/db.py` — env-driven `psycopg` connection (`load_dotenv` + `PG*` vars).
- `src/ingest.py` — sample CSV loader. `scripts/load_demo_data.py` is the deterministic demo loader.

### The logged-flags pattern (most important domain rule)

`0` is a meaningful value distinct from "never logged." The `daily_checkin` table carries
`deep_work_logged`, `caffeine_logged`, and `exercise_logged` boolean flags. The analytics views
emit `NULL` for a metric when its section was not logged, and `COALESCE(..., 0)` only when the
flag is true. When changing write paths or views, preserve this: an explicit logged `0` must not
collapse into the same state as an unsubmitted form.

### Child-table summary pattern

`caffeine_log` and `exercise_log` are child tables (FK on `checkin_date`) capable of holding
multiple events per day, but the current forms write a single daily summary row. The repository's
`replace_caffeine_summary` / `replace_exercise_summary` delete then re-insert for the date, set the
logged flag via `_ensure_daily_checkin_exists`, and skip the insert entirely when the total is `0`
(the flag still records that the section was logged). Keep the schema's per-event shape intact when
extending — it exists so the model can grow.

### Two parallel analytics layers (kept in sync)

The same two views — `daily_metrics_vw` and `daily_completeness_vw` — are defined twice:
- `sql/views.sql` (raw SQL, the current fallback path).
- dbt models under `models/` (`sources.yml` -> `staging/stg_*` -> `marts/`).

They use identical view names and column logic. **Any change to one must be mirrored in the other**
so the app behaves the same regardless of which path built the views. Postgres is the dbt source;
materialization is `view` (set in `dbt_project.yml`).

## Conventions

- App/test modules insert the repo root into `sys.path` so `src.*` imports work when run directly;
  follow that pattern in new entrypoints rather than relying on installed packages.
- `src/analytics.py` is intentionally DB-free and unit-tested — keep insight logic there, not in
  the SQL or Streamlit layers.
- Local credentials (`habit_user` / `habit_pw` / `habit_focus_db`) are hardcoded for the Docker
  Postgres across `docker-compose.yml`, `.env.example`, and `profiles.yml.example`. `profiles.yml`
  and `.env` are gitignored.

## Verifying major chart and UI changes

Visual verification is required only for changes that materially affect a rendered chart or its surrounding UI.

This includes:

* Adding, removing, or replacing a chart
* Changing chart type, layout, scale, axis behavior, aggregation, filtering, or displayed fields
* Changing labels, legends, tooltips, annotations, colors, sizing, or responsive behavior in a way that could affect readability or interpretation
* Changing Streamlit layout, containers, tabs, controls, or state behavior that could affect how a chart is displayed or used
* Fixing a visual bug whose resolution cannot be confirmed reliably through tests or schema validation alone

Visual verification is not required for:

* Refactoring with no intended visual change
* Test-only, documentation-only, or configuration-only changes
* Data-model changes that do not alter the chart’s output
* Minor copy edits
* Dependency or formatting changes that do not affect rendering
* Changes already covered by a focused visual regression test

When visual verification is required:

1. Ensure Postgres is running and start the app with `make app` on port 8501.
2. Use the Playwright MCP tools to open the affected view, wait for the chart or UI element to render, and take a screenshot.
3. Open the screenshot and verify the affected behavior against the change’s intent before committing.
4. State in the report what was visually checked and what the screenshot showed.

Limit verification to the affected view or component. Do not inspect unrelated charts or pages unless the change could reasonably affect them.

If the app cannot run because the database or another required service is unavailable, fall back to rendering the affected chart with `chart.save` and `vl-convert`, then state that limitation in the report.

## Ambiguous requests

When a request has material ambiguity:

1. Do not edit files or run expensive commands.
2. Restate the intended outcome.
3. Identify assumptions that could alter the implementation.
4. Ask concise clarifying questions.
5. Propose a bounded plan and wait for approval.

Prefer the smallest relevant file search and targeted test. Do not perform
adjacent refactoring unless explicitly requested.

## Testing and validating changes

After the change:
1. Run the smallest directly relevant test first.
2. Run the full suite only if the targeted test passes and the change could
   affect unrelated modules.
3. Do not retry a failing command more than once without explaining the failure.