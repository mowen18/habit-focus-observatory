# habit-focus-observatory

Minimal MVP scaffold for a SQL + Python + Streamlit habit and focus analysis project.

## Local Setup

1. Activate the project environment: `source .venv/bin/activate`
2. Install dependencies: `pip install -r requirements.txt`
3. Copy environment variables: `cp .env.example .env`
4. Start Postgres: `docker compose up -d`

## Structure

- `app/` contains the Streamlit entrypoint.
- `sql/` contains schema, views, and analysis query placeholders.
- `src/` contains lightweight Python modules for DB access, ingestion, analytics, and utilities.
- `data/` contains sample input data.
- `notebooks/` contains an exploration notebook stub.

## Getting Started

1. Activate the project environment: `source .venv/bin/activate`
2. Install dependencies: `pip install -r requirements.txt`
3. Run the app: `streamlit run app/streamlit_app.py`
