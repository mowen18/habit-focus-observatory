"""Streamlit app for a simple morning habit and focus workflow."""

from datetime import date, time, timedelta
from pathlib import Path
import sys
from typing import Optional

import altair as alt
import pandas as pd
import streamlit as st


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.db import get_connection


TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)
MORNING_DEFAULTS = {
    "sleep_hours": 7.5,
    "sleep_quality": 7,
    "energy_rating": 7,
    "focus_rating": 7,
    "mood_rating": 7,
    "stress_rating": 4,
    "notes": "",
}
DEEP_WORK_DEFAULTS = {"deep_work_minutes": 60}
CAFFEINE_DEFAULTS = {
    "total_caffeine_mg": 0,
    "last_caffeine_time": time(14, 0),
}
EXERCISE_DEFAULTS = {
    "duration_minutes": 0,
    "intensity": "",
    "start_time": time(7, 0),
}


def _clean_text(value: str):
    """Normalize blank text inputs to None."""
    cleaned = value.strip()
    return cleaned or None


def _ensure_daily_checkin_exists(cursor, checkin_date: date) -> None:
    """Create an empty parent daily_checkin row when child rows need it."""
    cursor.execute(
        """
        INSERT INTO daily_checkin (checkin_date)
        VALUES (%s)
        ON CONFLICT (checkin_date) DO NOTHING
        """,
        (checkin_date,),
    )


def save_morning_checkin(payload: dict) -> None:
    """Upsert the morning check-in fields for one date."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO daily_checkin (
                    checkin_date,
                    sleep_hours,
                    sleep_quality,
                    energy_rating,
                    focus_rating,
                    mood_rating,
                    stress_rating,
                    notes
                )
                VALUES (
                    %(checkin_date)s,
                    %(sleep_hours)s,
                    %(sleep_quality)s,
                    %(energy_rating)s,
                    %(focus_rating)s,
                    %(mood_rating)s,
                    %(stress_rating)s,
                    %(notes)s
                )
                ON CONFLICT (checkin_date) DO UPDATE
                SET
                    sleep_hours = EXCLUDED.sleep_hours,
                    sleep_quality = EXCLUDED.sleep_quality,
                    energy_rating = EXCLUDED.energy_rating,
                    focus_rating = EXCLUDED.focus_rating,
                    mood_rating = EXCLUDED.mood_rating,
                    stress_rating = EXCLUDED.stress_rating,
                    notes = EXCLUDED.notes
                """,
                payload,
            )


def save_deep_work_minutes(checkin_date: date, deep_work_minutes: int) -> None:
    """Create or update only the deep_work_minutes field for one date."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO daily_checkin (
                    checkin_date,
                    deep_work_minutes,
                    deep_work_logged
                )
                VALUES (%s, %s, TRUE)
                ON CONFLICT (checkin_date) DO UPDATE
                SET
                    deep_work_minutes = EXCLUDED.deep_work_minutes,
                    deep_work_logged = EXCLUDED.deep_work_logged
                """,
                (checkin_date, deep_work_minutes),
            )


def replace_caffeine_summary(
    checkin_date: date,
    total_caffeine_mg: int,
    last_caffeine_time: time,
) -> None:
    """Replace the stored caffeine summary row for one date."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM caffeine_log WHERE checkin_date = %s",
                (checkin_date,),
            )

            _ensure_daily_checkin_exists(cursor, checkin_date)
            cursor.execute(
                """
                UPDATE daily_checkin
                SET caffeine_logged = TRUE
                WHERE checkin_date = %s
                """,
                (checkin_date,),
            )

            if total_caffeine_mg <= 0:
                return

            cursor.execute(
                """
                INSERT INTO caffeine_log (
                    checkin_date,
                    intake_time,
                    source,
                    caffeine_mg
                )
                VALUES (%s, %s, %s, %s)
                """,
                (checkin_date, last_caffeine_time, None, total_caffeine_mg),
            )


def replace_exercise_summary(
    checkin_date: date,
    duration_minutes: int,
    intensity: Optional[str],
    start_time: time,
) -> None:
    """Replace the stored exercise row for one date."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM exercise_log WHERE checkin_date = %s",
                (checkin_date,),
            )

            _ensure_daily_checkin_exists(cursor, checkin_date)
            cursor.execute(
                """
                UPDATE daily_checkin
                SET exercise_logged = TRUE
                WHERE checkin_date = %s
                """,
                (checkin_date,),
            )

            if duration_minutes <= 0:
                return

            cursor.execute(
                """
                INSERT INTO exercise_log (
                    checkin_date,
                    exercise_type,
                    duration_minutes,
                    intensity,
                    start_time
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (checkin_date, "Workout", duration_minutes, intensity, start_time),
            )


def _render_save_error(exc: Exception) -> None:
    """Show a friendly save error for this MVP app."""
    st.error(
        "We couldn't save this entry. "
        f"Please confirm Postgres is running and try again. Details: {exc}"
    )


def load_daily_checkin_values(checkin_date: date) -> dict:
    """Fetch one daily_checkin row for preloading form values."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    sleep_hours,
                    sleep_quality,
                    energy_rating,
                    focus_rating,
                    mood_rating,
                    stress_rating,
                    deep_work_minutes,
                    deep_work_logged,
                    caffeine_logged,
                    exercise_logged,
                    notes
                FROM daily_checkin
                WHERE checkin_date = %s
                """,
                (checkin_date,),
            )
            row = cursor.fetchone()

    if row is None:
        return {}

    deep_work_logged = bool(row[7])

    return {
        "sleep_hours": float(row[0]) if row[0] is not None else MORNING_DEFAULTS["sleep_hours"],
        "sleep_quality": row[1] if row[1] is not None else MORNING_DEFAULTS["sleep_quality"],
        "energy_rating": row[2] if row[2] is not None else MORNING_DEFAULTS["energy_rating"],
        "focus_rating": row[3] if row[3] is not None else MORNING_DEFAULTS["focus_rating"],
        "mood_rating": row[4] if row[4] is not None else MORNING_DEFAULTS["mood_rating"],
        "stress_rating": row[5] if row[5] is not None else MORNING_DEFAULTS["stress_rating"],
        "deep_work_minutes": (
            row[6]
            if deep_work_logged and row[6] is not None
            else DEEP_WORK_DEFAULTS["deep_work_minutes"]
        ),
        "deep_work_logged": deep_work_logged,
        "caffeine_logged": bool(row[8]),
        "exercise_logged": bool(row[9]),
        "notes": row[10] or "",
    }


def load_caffeine_summary_values(checkin_date: date) -> dict:
    """Fetch one caffeine summary row for preloading the caffeine form."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT caffeine_logged
                FROM daily_checkin
                WHERE checkin_date = %s
                """,
                (checkin_date,),
            )
            logged_row = cursor.fetchone()

            cursor.execute(
                """
                SELECT
                    caffeine_mg,
                    intake_time
                FROM caffeine_log
                WHERE checkin_date = %s
                ORDER BY caffeine_id DESC
                LIMIT 1
                """,
                (checkin_date,),
            )
            row = cursor.fetchone()

    caffeine_logged = bool(logged_row[0]) if logged_row is not None else False
    if not caffeine_logged:
        return {"caffeine_logged": False}

    return {
        "caffeine_logged": True,
        "total_caffeine_mg": row[0] if row is not None else 0,
        "last_caffeine_time": (
            row[1]
            if row is not None and row[1] is not None
            else CAFFEINE_DEFAULTS["last_caffeine_time"]
        ),
    }


def load_exercise_summary_values(checkin_date: date) -> dict:
    """Fetch one exercise summary row for preloading the exercise form."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT exercise_logged
                FROM daily_checkin
                WHERE checkin_date = %s
                """,
                (checkin_date,),
            )
            logged_row = cursor.fetchone()

            cursor.execute(
                """
                SELECT
                    duration_minutes,
                    intensity,
                    start_time
                FROM exercise_log
                WHERE checkin_date = %s
                ORDER BY exercise_id DESC
                LIMIT 1
                """,
                (checkin_date,),
            )
            row = cursor.fetchone()

    exercise_logged = bool(logged_row[0]) if logged_row is not None else False
    if not exercise_logged:
        return {"exercise_logged": False}

    return {
        "exercise_logged": True,
        "duration_minutes": row[0] if row is not None else 0,
        "intensity": row[1] if row is not None and row[1] is not None else "",
        "start_time": (
            row[2]
            if row is not None and row[2] is not None
            else EXERCISE_DEFAULTS["start_time"]
        ),
    }


def _sync_form_state(form_name: str, selected_date: date, values_by_key: dict) -> None:
    """Update widget state only when a section's selected date changes."""
    loaded_date_key = f"{form_name}_loaded_date"
    if st.session_state.get(loaded_date_key) == selected_date:
        return

    for key, value in values_by_key.items():
        st.session_state[key] = value
    st.session_state[loaded_date_key] = selected_date


def load_recent_daily_metrics(limit: int = 14) -> pd.DataFrame:
    """Fetch a small recent window from daily_metrics_vw for review charts and tables."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    checkin_date,
                    sleep_hours,
                    sleep_quality,
                    energy_rating,
                    focus_rating,
                    mood_rating,
                    stress_rating,
                    deep_work_minutes,
                    total_caffeine_mg,
                    caffeine_after_2pm,
                    total_exercise_minutes,
                    high_intensity_flag
                FROM daily_metrics_vw
                ORDER BY checkin_date DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            columns = [column.name for column in cursor.description]

    if not rows:
        return pd.DataFrame(columns=columns)

    metrics_df = pd.DataFrame(rows, columns=columns)
    return metrics_df.sort_values("checkin_date").reset_index(drop=True)


def load_recent_daily_completeness(limit: int = 14) -> pd.DataFrame:
    """Fetch a recent completeness window for the review section."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                WITH recent_dates AS (
                    SELECT
                        generate_series(
                            CURRENT_DATE - (%s::INTEGER - 1),
                            CURRENT_DATE,
                            INTERVAL '1 day'
                        )::DATE AS checkin_date
                )
                SELECT
                    recent_dates.checkin_date,
                    COALESCE(dc.has_checkin, FALSE) AS has_checkin,
                    COALESCE(dc.has_deep_work_entry, FALSE) AS has_deep_work_entry,
                    COALESCE(dc.has_caffeine_entry, FALSE) AS has_caffeine_entry,
                    COALESCE(dc.has_exercise_entry, FALSE) AS has_exercise_entry,
                    COALESCE(dc.completed_sections, 0) AS completed_sections,
                    COALESCE(dc.expected_sections, 4) AS expected_sections,
                    COALESCE(dc.completeness_pct, 0.0) AS completeness_pct
                FROM recent_dates
                LEFT JOIN daily_completeness_vw AS dc
                    ON recent_dates.checkin_date = dc.checkin_date
                ORDER BY recent_dates.checkin_date DESC
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            columns = [column.name for column in cursor.description]

    if not rows:
        return pd.DataFrame(columns=columns)

    completeness_df = pd.DataFrame(rows, columns=columns)
    return completeness_df.sort_values("checkin_date").reset_index(drop=True)


def load_analysis_daily_data() -> pd.DataFrame:
    """Fetch analysis-ready current-day outcomes plus prior-day behavior inputs."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    current_day.checkin_date,
                    current_day.sleep_hours,
                    current_day.sleep_quality,
                    current_day.energy_rating,
                    current_day.focus_rating,
                    current_day.mood_rating,
                    current_day.stress_rating,
                    current_completeness.has_checkin,
                    prior_day.deep_work_minutes AS prior_day_deep_work_minutes,
                    prior_day.total_caffeine_mg AS prior_day_total_caffeine_mg,
                    prior_day.total_exercise_minutes AS prior_day_total_exercise_minutes,
                    prior_completeness.has_deep_work_entry AS prior_day_has_deep_work_entry,
                    prior_completeness.has_caffeine_entry AS prior_day_has_caffeine_entry,
                    prior_completeness.has_exercise_entry AS prior_day_has_exercise_entry
                FROM daily_metrics_vw AS current_day
                LEFT JOIN daily_completeness_vw AS current_completeness
                    ON current_day.checkin_date = current_completeness.checkin_date
                LEFT JOIN daily_metrics_vw AS prior_day
                    ON prior_day.checkin_date = current_day.checkin_date - 1
                LEFT JOIN daily_completeness_vw AS prior_completeness
                    ON prior_completeness.checkin_date = current_day.checkin_date - 1
                ORDER BY current_day.checkin_date
                """
            )
            rows = cursor.fetchall()
            columns = [column.name for column in cursor.description]

    if not rows:
        return pd.DataFrame(columns=columns)

    return pd.DataFrame(rows, columns=columns)


def _format_average(series: pd.Series, decimals: int = 1) -> str:
    """Format an average metric while handling missing values cleanly."""
    average_value = series.mean()
    if pd.isna(average_value):
        return "N/A"
    return f"{average_value:.{decimals}f}"


def _format_logged_status(value: bool) -> str:
    """Display completeness flags with simple human-friendly labels."""
    return "Logged" if bool(value) else "Not logged"


def prepare_completeness_display_data(recent_completeness_df: pd.DataFrame) -> pd.DataFrame:
    """Return a small recent completeness table ready for display."""
    display_df = recent_completeness_df.copy()
    status_columns = [
        "has_checkin",
        "has_deep_work_entry",
        "has_caffeine_entry",
        "has_exercise_entry",
    ]
    for column in status_columns:
        display_df[column] = display_df[column].map(_format_logged_status)

    display_df["completeness_pct"] = display_df["completeness_pct"].map(
        lambda value: f"{float(value):.1f}%"
    )

    return display_df.rename(
        columns={
            "checkin_date": "Date",
            "has_checkin": "Morning check-in",
            "has_deep_work_entry": "Deep work",
            "has_caffeine_entry": "Caffeine",
            "has_exercise_entry": "Exercise",
            "completed_sections": "Completed sections",
            "expected_sections": "Expected sections",
            "completeness_pct": "Completeness",
        }
    )


def prepare_sleep_chart_data(recent_metrics_df: pd.DataFrame) -> pd.DataFrame:
    """Return clean numeric sleep-hour data ready for st.line_chart."""
    sleep_chart_df = recent_metrics_df[["checkin_date", "sleep_hours"]].copy()
    sleep_chart_df["sleep_hours"] = pd.to_numeric(
        sleep_chart_df["sleep_hours"],
        errors="coerce",
    )
    sleep_chart_df = sleep_chart_df.dropna(subset=["sleep_hours"])
    return sleep_chart_df.set_index("checkin_date")[["sleep_hours"]]


def prepare_sleep_focus_analysis_data(analysis_df: pd.DataFrame) -> pd.DataFrame:
    """Return same-day morning rows with usable sleep and focus values."""
    sleep_focus_df = analysis_df[
        analysis_df["has_checkin"]
        & analysis_df["sleep_hours"].notna()
        & analysis_df["focus_rating"].notna()
    ][["checkin_date", "sleep_hours", "focus_rating"]].copy()
    return sleep_focus_df.sort_values("checkin_date").reset_index(drop=True)


def prepare_caffeine_sleep_quality_data(analysis_df: pd.DataFrame) -> pd.DataFrame:
    """Return prior-day caffeine inputs aligned to current-day sleep quality."""
    caffeine_sleep_df = analysis_df[
        analysis_df["prior_day_has_caffeine_entry"]
        & analysis_df["prior_day_total_caffeine_mg"].notna()
        & analysis_df["sleep_quality"].notna()
    ][["checkin_date", "prior_day_total_caffeine_mg", "sleep_quality"]].copy()
    return caffeine_sleep_df.sort_values("checkin_date").reset_index(drop=True)


def prepare_exercise_energy_data(analysis_df: pd.DataFrame) -> pd.DataFrame:
    """Return prior-day exercise inputs aligned to current-day energy ratings."""
    exercise_energy_df = analysis_df[
        analysis_df["prior_day_has_exercise_entry"]
        & analysis_df["prior_day_total_exercise_minutes"].notna()
        & analysis_df["energy_rating"].notna()
    ][["checkin_date", "prior_day_total_exercise_minutes", "energy_rating"]].copy()
    return exercise_energy_df.sort_values("checkin_date").reset_index(drop=True)


def build_scatter_chart(
    chart_df: pd.DataFrame,
    x_column: str,
    y_column: str,
    x_title: str,
    y_title: str,
) -> alt.Chart:
    """Build a simple Altair scatter plot for a filtered daily relationship."""
    chart_df = chart_df.copy()
    if "checkin_date" in chart_df.columns:
        chart_df["checkin_date"] = pd.to_datetime(chart_df["checkin_date"])
    chart_df[x_column] = pd.to_numeric(chart_df[x_column], errors="coerce")
    chart_df[y_column] = pd.to_numeric(chart_df[y_column], errors="coerce")

    return (
        alt.Chart(chart_df)
        .mark_circle(size=90, color="#2E6F95")
        .encode(
            x=alt.X(f"{x_column}:Q", title=x_title),
            y=alt.Y(f"{y_column}:Q", title=y_title),
            tooltip=[
                alt.Tooltip("checkin_date:T", title="Date"),
                alt.Tooltip(f"{x_column}:Q", title=x_title),
                alt.Tooltip(f"{y_column}:Q", title=y_title),
            ],
        )
        .properties(height=280)
    )


st.set_page_config(page_title="Habit Focus Observatory", layout="centered")
st.title("Habit Focus Observatory")
st.caption("Simple morning workflow for the MVP.")
st.write(
    "Use the forms below to record today's check-in and yesterday's supporting summaries."
)

st.subheader("1. Today Morning Check-in")
morning_checkin_date = st.date_input(
    "Check-in date",
    value=TODAY,
    key="morning_checkin_date",
)
try:
    morning_saved_values = load_daily_checkin_values(morning_checkin_date)
except Exception as exc:
    st.error(
        "We couldn't load the saved morning check-in values. "
        f"Please confirm Postgres is running and try again. Details: {exc}"
    )
    morning_saved_values = {}

_sync_form_state(
    "morning_form",
    morning_checkin_date,
    {
        "morning_sleep_hours": morning_saved_values.get(
            "sleep_hours",
            MORNING_DEFAULTS["sleep_hours"],
        ),
        "morning_sleep_quality": morning_saved_values.get(
            "sleep_quality",
            MORNING_DEFAULTS["sleep_quality"],
        ),
        "morning_energy_rating": morning_saved_values.get(
            "energy_rating",
            MORNING_DEFAULTS["energy_rating"],
        ),
        "morning_focus_rating": morning_saved_values.get(
            "focus_rating",
            MORNING_DEFAULTS["focus_rating"],
        ),
        "morning_mood_rating": morning_saved_values.get(
            "mood_rating",
            MORNING_DEFAULTS["mood_rating"],
        ),
        "morning_stress_rating": morning_saved_values.get(
            "stress_rating",
            MORNING_DEFAULTS["stress_rating"],
        ),
        "morning_notes": morning_saved_values.get("notes", MORNING_DEFAULTS["notes"]),
    },
)

with st.form("today_morning_checkin_form"):
    morning_sleep_hours = st.number_input(
        "Sleep hours",
        min_value=0.0,
        max_value=24.0,
        step=0.25,
        key="morning_sleep_hours",
    )

    morning_rating_col_1, morning_rating_col_2, morning_rating_col_3 = st.columns(3)
    morning_sleep_quality = morning_rating_col_1.number_input(
        "Sleep quality (1-10)",
        min_value=1,
        max_value=10,
        step=1,
        key="morning_sleep_quality",
    )
    morning_energy_rating = morning_rating_col_2.number_input(
        "Energy rating (1-10)",
        min_value=1,
        max_value=10,
        step=1,
        key="morning_energy_rating",
    )
    morning_focus_rating = morning_rating_col_3.number_input(
        "Focus rating (1-10)",
        min_value=1,
        max_value=10,
        step=1,
        key="morning_focus_rating",
    )

    morning_rating_col_4, morning_rating_col_5 = st.columns(2)
    morning_mood_rating = morning_rating_col_4.number_input(
        "Mood rating (1-10)",
        min_value=1,
        max_value=10,
        step=1,
        key="morning_mood_rating",
    )
    morning_stress_rating = morning_rating_col_5.number_input(
        "Stress rating (1-10)",
        min_value=1,
        max_value=10,
        step=1,
        key="morning_stress_rating",
    )
    morning_notes = st.text_area("Notes", key="morning_notes")

    morning_submitted = st.form_submit_button("Save today's morning check-in")

if morning_submitted:
    morning_payload = {
        "checkin_date": morning_checkin_date,
        "sleep_hours": round(float(morning_sleep_hours), 2),
        "sleep_quality": int(morning_sleep_quality),
        "energy_rating": int(morning_energy_rating),
        "focus_rating": int(morning_focus_rating),
        "mood_rating": int(morning_mood_rating),
        "stress_rating": int(morning_stress_rating),
        "notes": _clean_text(morning_notes),
    }
    try:
        save_morning_checkin(morning_payload)
        st.success(f"Saved today's morning check-in for {morning_checkin_date.isoformat()}.")
    except Exception as exc:
        _render_save_error(exc)

st.subheader("2. Yesterday Deep Work")
deep_work_date = st.date_input(
    "Check-in date",
    value=YESTERDAY,
    key="deep_work_date",
)
try:
    deep_work_saved_values = load_daily_checkin_values(deep_work_date)
except Exception as exc:
    st.error(
        "We couldn't load the saved deep work values. "
        f"Please confirm Postgres is running and try again. Details: {exc}"
    )
    deep_work_saved_values = {}

_sync_form_state(
    "deep_work_form",
    deep_work_date,
    {
        "deep_work_minutes": deep_work_saved_values.get(
            "deep_work_minutes",
            DEEP_WORK_DEFAULTS["deep_work_minutes"],
        )
    },
)

with st.form("yesterday_deep_work_form"):
    deep_work_minutes = st.number_input(
        "Deep work minutes",
        min_value=0,
        step=15,
        key="deep_work_minutes",
    )

    deep_work_submitted = st.form_submit_button("Save yesterday's deep work")

if deep_work_submitted:
    try:
        save_deep_work_minutes(deep_work_date, int(deep_work_minutes))
        st.success(f"Saved deep work for {deep_work_date.isoformat()}.")
    except Exception as exc:
        _render_save_error(exc)

st.subheader("3. Yesterday Caffeine Summary")
caffeine_checkin_date = st.date_input(
    "Check-in date",
    value=YESTERDAY,
    key="caffeine_checkin_date",
)
try:
    caffeine_saved_values = load_caffeine_summary_values(caffeine_checkin_date)
except Exception as exc:
    st.error(
        "We couldn't load the saved caffeine values. "
        f"Please confirm Postgres is running and try again. Details: {exc}"
    )
    caffeine_saved_values = {}

_sync_form_state(
    "caffeine_form",
    caffeine_checkin_date,
    {
        "total_caffeine_mg": caffeine_saved_values.get(
            "total_caffeine_mg",
            CAFFEINE_DEFAULTS["total_caffeine_mg"],
        ),
        "last_caffeine_time": caffeine_saved_values.get(
            "last_caffeine_time",
            CAFFEINE_DEFAULTS["last_caffeine_time"],
        ),
    },
)

with st.form("yesterday_caffeine_form"):
    total_caffeine_mg = st.number_input(
        "Total caffeine mg",
        min_value=0,
        step=5,
        key="total_caffeine_mg",
    )
    last_caffeine_time = st.time_input(
        "Last caffeine time",
        key="last_caffeine_time",
    )

    caffeine_submitted = st.form_submit_button("Save yesterday's caffeine summary")

if caffeine_submitted:
    try:
        replace_caffeine_summary(
            caffeine_checkin_date,
            int(total_caffeine_mg),
            last_caffeine_time,
        )
        st.success(f"Saved caffeine summary for {caffeine_checkin_date.isoformat()}.")
    except Exception as exc:
        _render_save_error(exc)

st.subheader("4. Yesterday Exercise")
exercise_checkin_date = st.date_input(
    "Check-in date",
    value=YESTERDAY,
    key="exercise_checkin_date",
)
try:
    exercise_saved_values = load_exercise_summary_values(exercise_checkin_date)
except Exception as exc:
    st.error(
        "We couldn't load the saved exercise values. "
        f"Please confirm Postgres is running and try again. Details: {exc}"
    )
    exercise_saved_values = {}

_sync_form_state(
    "exercise_form",
    exercise_checkin_date,
    {
        "exercise_duration_minutes": exercise_saved_values.get(
            "duration_minutes",
            EXERCISE_DEFAULTS["duration_minutes"],
        ),
        "exercise_intensity": exercise_saved_values.get(
            "intensity",
            EXERCISE_DEFAULTS["intensity"],
        ),
        "exercise_start_time": exercise_saved_values.get(
            "start_time",
            EXERCISE_DEFAULTS["start_time"],
        ),
    },
)

with st.form("yesterday_exercise_form"):
    exercise_duration_minutes = st.number_input(
        "Duration minutes",
        min_value=0,
        step=5,
        key="exercise_duration_minutes",
    )

    exercise_intensity_col, exercise_time_col = st.columns(2)
    exercise_intensity = exercise_intensity_col.selectbox(
        "Intensity",
        options=["", "low", "moderate", "high"],
        key="exercise_intensity",
    )
    exercise_start_time = exercise_time_col.time_input(
        "Start time",
        key="exercise_start_time",
    )

    exercise_submitted = st.form_submit_button("Save yesterday's exercise")

if exercise_submitted:
    try:
        replace_exercise_summary(
            exercise_checkin_date,
            int(exercise_duration_minutes),
            exercise_intensity or None,
            exercise_start_time,
        )
        st.success(f"Saved exercise for {exercise_checkin_date.isoformat()}.")
    except Exception as exc:
        _render_save_error(exc)

st.divider()
st.subheader("Recent Trends & Review")

try:
    recent_metrics_df = load_recent_daily_metrics(limit=14)
    recent_completeness_df = load_recent_daily_completeness(limit=14)
    analysis_df = load_analysis_daily_data()
except Exception as exc:
    st.error(
        "We couldn't load the recent trends section. "
        f"Please confirm Postgres is running and try again. Details: {exc}"
    )
else:
    if recent_metrics_df.empty:
        st.info("No data yet. Save a check-in above to populate the recent review section.")
    else:
        recent_7d_df = recent_metrics_df.tail(7)

        metric_col_1, metric_col_2, metric_col_3, metric_col_4 = st.columns(4)
        metric_col_1.metric(
            "Avg sleep hours",
            _format_average(recent_7d_df["sleep_hours"], decimals=2),
        )
        metric_col_2.metric(
            "Avg focus rating",
            _format_average(recent_7d_df["focus_rating"]),
        )
        metric_col_3.metric(
            "Avg energy rating",
            _format_average(recent_7d_df["energy_rating"]),
        )
        metric_col_4.metric(
            "Avg deep work minutes",
            _format_average(recent_7d_df["deep_work_minutes"]),
        )

        st.write("Sleep hours over time")
        sleep_chart_df = prepare_sleep_chart_data(recent_metrics_df)
        if sleep_chart_df.empty:
            st.info("No sleep-hour data available for the recent chart yet.")
        else:
            st.line_chart(
                sleep_chart_df,
                use_container_width=True,
            )

        st.write("Focus rating over time")
        st.line_chart(
            recent_metrics_df.set_index("checkin_date")[["focus_rating"]],
            use_container_width=True,
        )

        st.write("Deep work minutes over time")
        st.line_chart(
            recent_metrics_df.set_index("checkin_date")[["deep_work_minutes"]],
            use_container_width=True,
        )

        st.write("Relationship spot checks")

        sleep_focus_df = prepare_sleep_focus_analysis_data(analysis_df)
        st.write("Sleep hours vs same-day focus rating")
        if len(sleep_focus_df) < 2:
            st.info("Add at least two morning check-ins with sleep hours and focus ratings to see this chart.")
        else:
            st.caption(f"Using {len(sleep_focus_df)} day(s) with a real morning check-in.")
            st.altair_chart(
                build_scatter_chart(
                    sleep_focus_df,
                    x_column="sleep_hours",
                    y_column="focus_rating",
                    x_title="Sleep hours",
                    y_title="Same-day focus rating",
                ),
                use_container_width=True,
            )

        caffeine_sleep_df = prepare_caffeine_sleep_quality_data(analysis_df)
        st.write("Yesterday total caffeine mg vs today sleep quality")
        if len(caffeine_sleep_df) < 2:
            st.info("Add at least two rows with yesterday's explicitly logged caffeine and today's sleep quality to see this chart.")
        else:
            st.caption(
                f"Using {len(caffeine_sleep_df)} day(s) where yesterday's caffeine was explicitly logged and today's sleep quality is present."
            )
            st.altair_chart(
                build_scatter_chart(
                    caffeine_sleep_df,
                    x_column="prior_day_total_caffeine_mg",
                    y_column="sleep_quality",
                    x_title="Yesterday total caffeine mg",
                    y_title="Today sleep quality",
                ),
                use_container_width=True,
            )

        exercise_energy_df = prepare_exercise_energy_data(analysis_df)
        st.write("Yesterday total exercise minutes vs today energy rating")
        if len(exercise_energy_df) < 2:
            st.info("Add at least two rows with yesterday's explicitly logged exercise and today's energy rating to see this chart.")
        else:
            st.caption(
                f"Using {len(exercise_energy_df)} day(s) where yesterday's exercise was explicitly logged and today's energy rating is present."
            )
            st.altair_chart(
                build_scatter_chart(
                    exercise_energy_df,
                    x_column="prior_day_total_exercise_minutes",
                    y_column="energy_rating",
                    x_title="Yesterday total exercise minutes",
                    y_title="Today energy rating",
                ),
                use_container_width=True,
            )

        st.write("Data completeness")
        full_data_days = int(
            (
                recent_completeness_df["completed_sections"]
                == recent_completeness_df["expected_sections"]
            ).sum()
        )
        completeness_metric_col_1, completeness_metric_col_2 = st.columns(2)
        completeness_metric_col_3, completeness_metric_col_4 = st.columns(2)
        completeness_metric_col_1.metric(
            "Full data days",
            f"{full_data_days}/{len(recent_completeness_df)}",
        )
        completeness_metric_col_2.metric(
            "Missing deep work",
            int((~recent_completeness_df["has_deep_work_entry"]).sum()),
        )
        completeness_metric_col_3.metric(
            "Missing caffeine",
            int((~recent_completeness_df["has_caffeine_entry"]).sum()),
        )
        completeness_metric_col_4.metric(
            "Missing exercise",
            int((~recent_completeness_df["has_exercise_entry"]).sum()),
        )

        completeness_display_df = prepare_completeness_display_data(
            recent_completeness_df.sort_values("checkin_date", ascending=False)
        )
        st.dataframe(
            completeness_display_df,
            use_container_width=True,
            hide_index=True,
        )

        st.write("Recent daily logs")
        st.dataframe(
            recent_metrics_df.sort_values("checkin_date", ascending=False),
            use_container_width=True,
            hide_index=True,
        )
