# habit-focus-observatory

Minimal MVP scaffold for a SQL + Python + Streamlit habit and focus analysis project.

## Local Setup

1. Activate the project environment: `source .venv/bin/activate`
2. Install dependencies: `pip install -r requirements.txt`
3. Copy environment variables: `cp .env.example .env`
4. Start Postgres: `docker compose up -d`

## Structure

- `app/` contains the Streamlit entrypoint.
- `sql/` contains schema, views, and starter analytical queries for the MVP.
- `src/` contains lightweight Python modules for DB access, ingestion, analytics, and utilities.
- `data/` contains sample input data.
- `notebooks/` contains an exploration notebook stub.

## Getting Started

1. Activate the project environment: `source .venv/bin/activate`
2. Install dependencies: `pip install -r requirements.txt`
3. Run the app from the repo root: `streamlit run app/streamlit_app.py`

## Streamlit Workflow

The MVP Streamlit app keeps everything on one page and breaks the morning routine
into four separate forms:

1. Today morning check-in
   - saves today’s `daily_checkin` fields for sleep, ratings, and notes
2. Yesterday deep work
   - updates only `deep_work_minutes` on `daily_checkin` for the selected date
   - deep work stays null / unknown until this form is submitted, and submitting `0` records an explicit zero
3. Yesterday caffeine summary
   - replaces that date’s stored caffeine summary using a single `caffeine_log` row
   - caffeine stays null / unknown until this form is submitted, and submitting `0` records an explicit zero
4. Yesterday exercise
   - replaces that date’s stored exercise summary using a single `exercise_log` row
   - exercise stays null / unknown until this form is submitted, and submitting `0` records an explicit zero

Each section has its own submit button, so you can save one part of the workflow
without resubmitting the others.

The app also includes a read-only "Recent Trends & Review" section that uses
`daily_metrics_vw` to show recent summary metrics, charts, and a recent log table.

When you pick a date in one of the forms, the app now preloads any saved values
for that date when they exist, making it easier to review and edit earlier entries.

For caffeine, exercise, and deep work, the app now distinguishes three states:
not logged yet (`NULL` / unknown), logged as `0`, and logged as a nonzero value.

## Sample Ingestion

Sample files:

- `data/sample_logs.csv` for `daily_checkin` fields: `check_in_date`, `sleep_hours`, `sleep_quality`, `energy_score`, `focus_score`, `mood_score`, `stress_score`, `deep_work_minutes`, `notes`
- `data/sample_caffeine_log.csv` for `caffeine_log`
- `data/sample_exercise_log.csv` for `exercise_log`

Run the sample CSV loaders from the repo root:

`python -m src.ingest`
